"""
Hey! This is my first Python project! I'm really learning as I go along, and a GPT really helps
explain a bunch of concepts--don't worry, it's not writing it for me!
I'm going to try to train a deep learning agent play a game inspired by "Proximity" of Brian Cable. (i think it's brian cable, at least)
Proximity is a turn-based strategy game where players compete to control hexagonal tiles on a 10x8 grid. 
If you place a tile (each are d20) of a higher value adjacent to an opponent's tile of a lower value, you absorb it.
Next to an ally, the ally's tile(s) increases by one.

When all tiles are filled, the highest score wins.

The deep learning agent's name is Jef (with one f), thanks to a suggestion from a classmate.

I'll try to pit it against a random bot, some greedy bots, some long-term bots (maybe MCTS, minmax, or even genetic), and
finally, it'll self-learn

I may take two training approaches, a binary training approach (all wins/losses are rewarded equally, no matter the margin), 
and a margin-based approach (a landslide win is super to a thin one), and I want to see which plays better. 
I'm guessing the binary one will, but here's for trying!

If there's any suggestions you have, let me know!
Best,
-Gaymer <3
"""
# endregion

# region Initialize
import numpy as np 
from ordered_set import OrderedSet
import random
import sys
import math 
import time
import copy

# These control the player types:
IsAdjacentUsed = True # The adjacency checks add a decent amount of overhead, but are critical for all bots, barring the RL-algorithm
p1movetype = 7  # e.g., 1: random, 2: human, 3: RandomAdjacentTileBot, 4 is easy, 5 is medium, 6 is hard (greediest move), 7 is MCTS
p2movetype = 1
p3movetype = 6
HoleRandomnessType = 1  # 0 for none, 1 for pure randomness, 2 for perlin (not yet implemented)
PlayerCount = 2
RandomHoleOccurancePercentage = 10
global GlobalMoveNum

if p1movetype == 2 or p2movetype == 2 or p3movetype == 2:
    import re  # regex

# Define player “colors” using bit masks
none, red, green, blue = 0b00, 0b01, 0b10, 0b11

# Grid dimensions and roll settings
xMax = 10  # columns
yMax = 8   # rows
xMin = 0
yMin = 0
RollMax = 20

owner_symbols = {
    0: "·",  # represents no owner
    1: "R",  # red
    2: "G",  # green
    3: "B"   # blue
}


# Number banks (shuffled)
NumBank1 = NumBank2 = NumBank3 = list(range(1, RollMax+1)) * 2
random.shuffle(NumBank1)
random.shuffle(NumBank2)
random.shuffle(NumBank3)

# Hexagonal neighbour offsets (depending on row parity)
EvenRowOffsets = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
OddRowOffsets  = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]

# Sets to track valid and adjacent tiles (using (x, y) tuples)
adjacent_tiles = OrderedSet()

# 15: IsValid, 14-13: Owner, 13-8 = value, 7 IsAdjacent, 6-3 x, 2-0 y (nice and snug)
# ADD AN X, Y BIT !! very useful for AI
def get_owner(tile):
    mask = 0b0110000000000000
    return (tile & mask) >> 13

def set_owner(tile, owner):
    mask = 0b0110000000000000  # Bits 13 and 14
    cleared = tile & (~mask & 0xFFFF)     # Zero out owner bits
    result = cleared | (owner << 13)
    return np.uint16(result)

def get_value(tile):
    mask = 0b0001111100000000
    return (tile & mask) >> 8

def set_value(tile, value):
    mask = 0b0001111100000000
    cleared = tile & (~mask & 0xFFFF)
    return np.uint16(cleared | (value << 8))

def set_valid(tile, YN):
    mask = 0b1000000000000000
    cleared = tile & (~mask & 0xFFFF)
    bit = (0b1000000000000000 if YN else 0)
    return np.uint16(cleared | bit)

def is_valid(tile):
  mask =  0b1000000000000000
  return tile & mask

def is_adjacent(tile):
  mask =  0b0000000010000000
  return (tile & mask) >> 9

def set_adjacent(tile, YN):
    mask = 0b0000000010000000
    cleared = tile & (~mask & 0xFFFF)
    bit = (0b0000000010000000 if YN else 0)
    return np.uint16(cleared | bit)


adj_mask = np.zeros((8,10), dtype=bool)



if not RandomHoleOccurancePercentage >= 0 and not RandomHoleOccurancePercentage <= 1:
  RandomHoleOccurancePercentage = 10
  
if HoleRandomnessType == 0:
    # This sets bit 15 (0b1000000000000000) indicating a valid tile.
    grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
elif HoleRandomnessType == 1:
    grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
    hole_mask = np.random.rand(8, 10) < RandomHoleOccurancePercentage/100
    # Remove the valid bit from holes (bitwise AND with complement)
    grid[hole_mask] = grid[hole_mask] & 0b0111111111111111  
else:
    print("Warning, HoleRandomnessType is poorly defined. Proceeding with no holes.")
    grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)

GlobalMoveNum = 0
try: 
  holemasksum = hole_mask.sum()
  MoveMax = (xMax * yMax) - holemasksum
except:
  MoveMax = xMax * yMax

# endregion
# region MainFunctions

class Player:
    def __init__(self, name):
        self.name = name  # this holds the bit mask value for the player (red, green, or blue)
        self.score = int(0)
        self.NumBank = list(range(1, RollMax+1)) * 2
        self.FirstTime = True
        self.MoveType = int(0)
        self.MoveNumber = int(0)
        self.SumOfRolls = int(0)
        self.id = int(0)

class FakePlayer:
    def __init__(self, name):
        self.name = name  # this holds the bit mask value for the player (red, green, or blue)
        self.score = int(0)
        self.NumBank = list(range(1, RollMax+1)) * 2
        self.FirstTime = True
        self.MoveType = int(0)
        self.MoveNumber = int(0)
        self.SumOfRolls = int(0)

class Winner:
    def __init__(self, name):
        self.name = []
        self.player = []
        self.score = 0


def PlayerAssignment():
    # Randomly assign player colors for visualization.
    PossiblePlayers = [red, green, blue]
    temp = random.sample(PossiblePlayers, 3)
    global Player1, Player2, Player3
    Player1, Player2, Player3 = Player(temp[0]), Player(temp[1]), Player(temp[2])
    Player1.MoveType, Player1.id = p1movetype, 1 
    Player2.MoveType, Player2.id = p2movetype, 2
    Player3.MoveType, Player3.id = p3movetype, 3
    # might also create a mapping from owner value to Player for later use.
    owner_to_player = {Player1.name: Player1, Player2.name: Player2, Player3.name: Player3}

PlayerAssignment()

def ApplyMechanics(player, x, y, num, g=grid, adjmask = adj_mask, NumBank=None):
    if type(NumBank) == list:
        if len(NumBank) > 0:
            del NumBank[0]
    IsAdjacentToSomethingCheck(x, y, g)
    g[y][x] = set_adjacent(g[y][x], False)
    adjmask[y][x] = False   
    if (x, y) in adjacent_tiles:
        adjacent_tiles.remove((int(x),int(y)))
    
    if is_valid(g[y][x]):
        g[y][x] = set_valid(g[y][x], False)
    else:
        print("Critical Error! Chose an invalid tile!!!!!")
    if "grid" == str(g):
        global GlobalMoveNum
        GlobalMoveNum += 1
    if GlobalMoveNum > MoveMax:
      print("GlobalMoveNumber is equal to or greater than MoveMax")
      GetWinner()
      exit()
    offsets = np.array(EvenRowOffsets if y % 2 == 0 else OddRowOffsets)  
    
    neighbor_coords = np.array([x, y]) + offsets
    ys, xs = neighbor_coords[:, 1], neighbor_coords[:, 0]
    in_bounds = (xs >= 0) & (xs < xMax) & (ys >= 0) & (ys < yMax)
    ys, xs = ys[in_bounds], xs[in_bounds]
    
    values = get_value(g[ys, xs])
    x, y, num = int(x), int(y), int(num)
    
    if adjmask[y][x]:
      adjmask[y][x] = False;
      if (x, y) in adjacent_tiles:
        adjacent_tiles.remove((x, y))
      else:
        print("Warning! Tile in adjmask, but not adjacent tiles.")
    
    owners = get_owner(g[ys, xs])
    is_ally = (player.name == owners)
    is_enemy = ((player.name != owners) & (player.name != none))
    is_weaker_tile = (values < num) & (values != 0) 
    is_weaker_enemy = is_enemy & is_weaker_tile
    g[y][x] = set_owner(g[y][x], player.name)
    g[y][x] = set_value(g[y][x], num)
    player.score += num

    player.SumOfRolls += num
    if values[is_ally].size > 0: 
      values[is_ally] += 1
      player.score += np.count_nonzero(is_ally)
      tiles = g[ys, xs].copy()
      tiles[is_ally] = set_value(tiles[is_ally], values[is_ally])
      g[ys[is_ally], xs[is_ally]] = tiles[is_ally]

    if values[is_weaker_enemy].size > 0:
      player.score += int(np.sum(values[is_weaker_enemy]))
      tiles = g[ys, xs].copy()
      tiles[is_weaker_enemy] = set_owner(tiles[is_weaker_enemy], player.name)
      g[ys[is_weaker_enemy], xs[is_weaker_enemy]] = tiles[is_weaker_enemy]
      absorbed_owners = owners[is_weaker_enemy]
      absorbed_values = values[is_weaker_enemy]
      for p in [Player1, Player2, Player3]:
        player_mask = (absorbed_owners == p.name)
        if np.any(player_mask):
          penalty = int(np.sum(absorbed_values[player_mask]).item())
          p.score -= penalty
    if type(NumBank) == list:
        if len(NumBank) > 0:
            del NumBank[0]
        else:
            print("Error! NumBank's length is below 1.", "("+str(len(NumBank))+")")

# def ucb1_tuned(average, NumOfVisitsForI, NumOfVisitsForParent, variance):
#     exploration_term = math.sqrt((math.log(NumOfVisitsForParent) / NumOfVisitsForI) * min(0.25, variance + math.sqrt((2 * math.log(NumOfVisitsForParent)) / NumOfVisitsForI)))
#     # this is a complex formula (UCB1-Tuned)! for an explanation, see https://en.wikipedia.org/wiki/Monte_Carlo_tree_search#Exploration_and_exploitation for something similar--the only difference is that this is tuned for how "risky" a move is
#     return average + exploration_term


def EvalFromMoveList(move_list, player): # this is a basic formula ! try to upgrade it to something fancier (like an upper bound of confidence)
    winningnum = 0
    for move in move_list:
        if move == player:
            winningnum += 1
    MoveGoodness = winningnum / len(move_list)
    return MoveGoodness


def GameTest(player, player1, player2, stochastity=0.1, g=None, simnum=10, adjmask=adj_mask, player3=None): 
    winners = []
    players = [player1, player2]
    if player3 is not None:
      players.append(player3)
    players = [player1, player2] + ([player3] if player3 else [])
    RelativeP1, RelativeP2, RelativeP3 = players[0], players[1], players[2] if len(players) > 2 else None
    LocalMoveNum = GlobalMoveNum - 1
    for _ in range(int(1)): # SHOULD BE SIMNUM
        root = np.copy(g)
        tempP1 = copy.deepcopy(RelativeP1)
        tempP2 = copy.deepcopy(RelativeP2)
        p1tempnumbank = RelativeP1.NumBank.copy()
        p2tempnumbank = RelativeP2.NumBank.copy()
        random.shuffle(p1tempnumbank)
        random.shuffle(p2tempnumbank)
        if player3 != None:
            p3tempnumbank = RelativeP3.NumBank.copy()
            random.shuffle(p3tempnumbank)
            tempP3 = copy.deepcopy(RelativeP3)
        for num in p1tempnumbank:
            LocalMoveNum += 1
            p1num, p2num, p3num = p1tempnumbank[0], p2tempnumbank[0], p3tempnumbank[0] if player3 else None
            if LocalMoveNum >= MoveMax:
                break
            GreedyBot(tempP1, 1, stochastity, root, p1tempnumbank[0]) # This starts the loop at player 1, but with simulations, this isn't always necessarily the case. Fix pls :3
            LocalMoveNum += 1 
            if GameIsOver(False, LocalMoveNum):
                break
            GreedyBot(tempP2, 1, stochastity, root)
            if GameIsOver(False, LocalMoveNum):
                break
            if PlayerCount == 3:
                LocalMoveNum += 1
                if GameIsOver(False, LocalMoveNum):
                    break   
                GreedyBot(TempP3, 1, stochastity, root)
        winner = GetWinner(tempP1, tempP2, None)
        winners.append(winner)
    MoveGoodness = EvalFromMoveList(winners, player)
    return MoveGoodness

def MonteCarlosSearch(player, player1, player2, stochastity=0.1, fakegrid=grid, adjmask=adj_mask, simnum=50, num=None):
    if num == None:
        num = player.NumBank[0]
    move_list = [] 
    neighbors = np.argwhere(adjmask)  # Each element is [y, x]
    if len(neighbors) == 0:
        neighbors = np.argwhere(is_valid(fakegrid))
        
    for coord in neighbors:
        grid_copy = np.copy(fakegrid)
        y, x = coord
        move(player, num, x, y, grid_copy)
        MoveGoodness = GameTest(player, player1, player2, stochastity, fakegrid, simnum,adjmask)
        print("The added was", x, y, MoveGoodness)
        move_list.append((x, y, MoveGoodness))
    print("before i error out, here's the adjmask", np.argwhere(adjmask)) #debug
    best_move = max(move_list, key=lambda move: move[2])
    print("I, the humble MCTS bot, playing as", str(player.name)+",", "with number", str(num)+",", "chose my move to be", "("+str(best_move[0])+", "+str(best_move[1])+")", "out of", len(move_list), "options.") # debug
    return best_move
            
def MCTSbot(player, player1, player2, stochastity=0.1, simnum=50):
    root = copy.deepcopy(grid)
    adjmaskcopy = copy.deepcopy(adj_mask)
    best_move = MonteCarlosSearch(player, player1, player2, stochastity, root, adjmaskcopy, simnum)
    move(player, player.NumBank[0], best_move[0], best_move[1], root)
    

"""
YOU CAN VECTORISE GREEDY BOT! especially stochastity, you can probably make a really long list of random numbers using np and count through it
"""
def GreedyBot(player, greediness, stochastity=0, g=grid, num=None): 
    if num == None:
        num = player.NumBank[0]
    if stochastity != 0 and stochastity > random.randint(1, 100):
        RandomMove(player, num, g)
    else:
      scores = OrderedSet()
      try:
        greediness = int(greediness)
      except ValueError:
        print("Warning, GreedyBot played a random move! Greediness not defined properly.")
        RandomMove(player, num)
        return
      if greediness > len(adjacent_tiles):
        greediness = len(adjacent_tiles)
      if len(adjacent_tiles) != 0:
          for x, y in adjacent_tiles:
              PossibleScore = ScoreFromAbsorption(player, x, y)
              scores.append(((x, y), PossibleScore))
          top_moves = sorted(scores, key=lambda item: item[1], reverse=True)[:greediness]
          best_move = random.choice(top_moves)
          (x, y), _ = best_move
          ApplyMechanics(player, x, y, num, g)
      else:
          RandomMove(player, num, g)
          if GlobalMoveNum > 1:
            print("Warning, GreedyBot played a random move!")

def RandomMove(player, num, g=grid):
    yx = np.argwhere(is_valid(grid)) 
    if len(yx) != 0:
        y, x = yx[np.random.randint(len(yx))]
        ApplyMechanics(player, x, y, num, g)
        return x, y
    
def RandomAdjacentTileBot(player, num, g=grid):
    if adjacent_tiles:
        print("Adjacent tile move made (move number", player.MoveNumber, ")")
        x, y = adjacent_tiles.pop()
        ApplyMechanics(player, x, y, num, g)
        return True, x, y
    else:
        return RandomMove(player, num, g)

def GetWinner(p1=Player1, p2=Player2, p3=None):
    print(p1.name, p1.score, p2.name, p2.score, Player3.name, Player3.score)
    winner = Winner("")
    winner.score = max(p1.score, p2.score, p3.score if p3 != None else 0)
    if p1.score == winner.score:
        winner.name.append(p1.name)
        winner.player.append("Player1")
    if p2.score == winner.score:
        winner.name.append(p2.name)
        winner.player.append("Player2")
    if p3.score == winner.score:
        winner.name.append(p3.name)
        winner.player.append("Player3")
    
    if len(winner.name) == 1:
        print("The winner of the game is", str(winner.player[0]), "("+str(winner.name[0])+")")
        return winner.name
    elif len(winner.name) == 2:
        print("Two-way tie! The winners are", str(winner.player), "and their colors are", str(winner.name))
        return 00
    elif len(winner.name) == 3:
        print("Three-way tie!! The winners are", str(winner.player), "and their colors are", str(winner.name))
        return 00

def display_grid():
  owners = (grid & 0b0110000000000000) >> 13
  values = (grid & 0b0001111100000000) >> 8
  valids = (grid & 0b1000000000000000) > 0

  print("The scores are as follows:",
    str(Player1.name).capitalize() + ":", Player1.score,
    str(Player2.name).capitalize() + ":", Player2.score,
    str(Player3.name).capitalize() + ":", Player3.score)

  print("The current sum of rolls is",
    str(Player1.name).capitalize() + ":", Player1.SumOfRolls,
    str(Player2.name).capitalize() + ":", Player2.SumOfRolls,
    str(Player3.name).capitalize() + ":", Player3.SumOfRolls)

  print("   0   1   2   3   4   5   6   7   8   9")

  for y in range(yMax):
    row_str = ""
    for x in range(xMax):
      owner = owners[y][x]
      value = values[y][x]
      valid = valids[y][x]

      if not valid and value == 0:
        row_str += " X  "
      elif owner == none and value == 0:
        row_str += " ·  "
      elif owner == none and value != 0:
        print(f"Warning: tile at ({x},{y}) has value {value} but no owner? Owner: {owner}")
        row_str += " ? "
      else:
        symbol = owner_symbols[owner] + f"{value:02d}"
        row_str += symbol + " "

    if y % 2 == 1:
      print(y, "  " + row_str)
    else:
      print(y, row_str)

  print("     0   1   2   3   4   5   6   7   8   9")


def HumanMoveInput(player):
  while True:
    display_grid()
    print("Your number is", player.NumBank[0], "and your color is", str(player.name)+".")
    move_input = input("What is your move? Structure it as X,Y : ")
    match = re.match(r"(\d+),\s*(\d+)", move_input)
    if match:
        x, y = map(int, match.groups())
        print(f"X: {x}, Y: {y}")
        inbounds = (xMin <= x < xMax and yMin <= y < yMax)
        if inbounds:
            if get_owner(grid[y][x]) == none and is_valid(grid[y][x]):
              return x, y
            else:
                print("Invalid input.")
        else:
            print("Out of bounds.")


def IsAdjacentToSomethingCheck(x, y, g=grid):
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (xMin <= nx < xMax and yMin <= ny < yMax):
            continue
        if get_owner(g[ny][nx]) == none and is_valid(g[ny][nx]):
            if (nx, ny) not in adjacent_tiles:
                adjacent_tiles.add((nx, ny))
                adj_mask[y][x] = True

def ScoreFromAbsorption(player, x, y, g=grid):
    PossibleScore = 0
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (xMin <= nx < xMax and yMin <= ny < yMax):
            continue
        GridYxValue = get_value(g[ny][nx])
        ChosenSpot = g[ny][nx]
        if int(get_owner(ChosenSpot)) == int(player.name):
            PossibleScore += 1
        elif get_owner(ChosenSpot) !=none and get_owner(ChosenSpot) != player.name and player.NumBank[0] > GridYxValue:
            PossibleScore += GridYxValue
    return PossibleScore

def move(player, num, x, y, g=grid):
    if player is None or num is None or x is None or y is None:
        print("Warning: Parameter unset!")
    if GlobalMoveNum >= MoveMax:
        print("MoveNum > MoveMax! Critical Error!")
    if not (0 <= x < xMax and 0 <= y < yMax):
        print("Out of bounds! Critical Error!")
    if get_owner(g[y][x]) != none:
        print("Tile already occupied! Critical Error!")
    ApplyMechanics(player, x, y, num, g)

def Play(player, g=grid): # FIX THESE TO UTILISE THE GRID
    """AAAA"""
    if player.FirstTime:
        random.shuffle(player.NumBank)
        player.FirstTime = False 
    if len(player.NumBank) == 0:
        display_grid()
        print("Whoops,", str(player.name)+"'s", "number bank ran out.")
        exit()
    if player.MoveType == 1:
        RandomMove(player, player.NumBank[0], g)
    elif player.MoveType == 2:
        x, y = HumanMoveInput(player)
        move(player, player.NumBank[0], x, y, g)
    elif player.MoveType == 3:
        MoveMade = RandomAdjacentTileBot(player, player.NumBank[0], g)
    elif player.MoveType == 4:
        GreedyBot(player, 5)
    elif player.MoveType == 5:
        GreedyBot(player, 3)
    elif player.MoveType == 6:
        GreedyBot(player, 1)
    elif player.MoveType == 7:
        MCTSbot(player, Player1, Player2)
    else:
        print("FATAL ERROR. Movetype is poorly defined.")
        exit()
    del player.NumBank[0]

def GameIsOver(gridshown=True, movenum=GlobalMoveNum):
    if movenum >= MoveMax:
        if gridshown == True:
            display_grid()
        return True
    return False

# def ResetStates():
#     player
# endregion

# region MainLoop
while True:
    if GlobalMoveNum >= MoveMax:
        display_grid()
        break
    Play(Player1)
    if GameIsOver():
        break
    Play(Player2)
    if GameIsOver():
        break
    if PlayerCount == 3:
        if GameIsOver():
            break
        Play(Player3)
  
GetWinner()
# endregion
# region Checklist 

"""
Checklist
1) get a grid of tiles [✓]
2) manually place some hexagons [✓]
3) get turns working [✓] 
4) determine which tiles touch which [✓]
5) get a representation of the grid (text-based) [✓]
6) implement logic (absorbing adjacent enemies, reinforcing allies) [✓] 
7) determine score on-the-go, without relying on checking every score in the loop [✓]
8) determine winner at the end [✓]
9) get "holes" working [✓]
10) get some basic rules-based bots to play against [✓] 
11) optimise, esp. state values and excessive loops [✓] # a lot harder than i thought; note one can probably do more, but i didn't do the 80/20
12) implement MCTS bots to encourage deeper thinking [-] # try greedy rollouts and random rollouts
13) get a reinforcement learning agent to learn this game, with the help of MCTS at later stages [X]
14) graphical implementation [X]
15) elo system? [X]
"""
# endregion
# region misc
"""
other important things!
save every 10th game or so 

maybe for some rules based ones

random) duh
reallyeasy) play a random adjacent move
easy) play a random move out of the greediest 5
medium) play a random move of the greediest 3
hard) play the greediest move
MCTS easy) use weak MCTS 
MCTS hard) use strong MCTS
maybe add a minmax + MCTS

maybe get a win/loss record for the agent for the past 1000 moves every 1000 games, and for every percent above 75 the RL beats the previous bot, make 5% of their opponents the harder one

for holes, maybe do perlin noise, add a bias to the sides 4,4, normalize so only 
10, 15, 20, and 30 tiles meet a threshold respectively (e.g. 0.3), and then
any tile above the threshold becomes a hole. batch generate like 50k of these and choose
them at random, and utilise them around 20-40% of the time. don't calculate 
on-the-fly, it would be really expensive

or maybe just follow rod pierce, with just the random tenth of tiles being holes
"""
#endregion
