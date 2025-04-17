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
p1movetype = 4  # e.g., 1: random, 2: human, 3: RandomAdjacentTileBot, 4 is easy, 5 is medium, 6 is hard (greediest move), 7 is MCTS
p2movetype = 1
p3movetype = 6
HoleRandomnessType = 1  # 0 for none, 1 for pure randomness, 2 for perlin (not yet implemented)
MCTSStochasticity = 0.1
MCTSSimnum = 50
PlayerCount = 2
RandomHoleOccurancePercentage = 10

if p1movetype == 2 or p2movetype == 2 or p3movetype == 2:
    import re  # regex

# Define player “colors” using bit masks
none, red, green, blue = 0b00, 0b01, 0b10, 0b11

# Grid dimensions and roll settings
x_max = 10  # columns
y_max = 8   # rows
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
    MainGrid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
elif HoleRandomnessType == 1:
    MainGrid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
    hole_mask = np.random.rand(8, 10) < RandomHoleOccurancePercentage/100
    # Remove the valid bit from holes (bitwise AND with complement)
    MainGrid[hole_mask] = MainGrid[hole_mask] & 0b0111111111111111  
else:
    print("Warning, HoleRandomnessType is poorly defined. Proceeding with no holes.")
    MainGrid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)

# endregion
def HumanMoveInput(player):
  while True:
    display_grid()
    print("Your number is", player.NumBank[0], "and your color is", str(player.name)+".")
    move_input = input("What is your move? Structure it as X,Y : ")
    match = re.match(r"(\d+),\s*(\d+)", move_input)
    if match:
        x, y = map(int, match.groups())
        print(f"X: {x}, Y: {y}")
        inbounds = (xMin <= x < x_max and yMin <= y < y_max)
        if inbounds:
            if get_owner(MainGrid[y][x]) == none and is_valid(MainGrid[y][x]):
              return x, y
            else:
                print("Invalid input.")
        else:
            print("Out of bounds.")
# region PrimaryCode

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
    
    def MakeRandomMove(self, owner, g):
        yx = np.argwhere(is_valid(g)) 
        if len(yx) != 0:
            print("Critical error! MakeRandomMove called, while no valid options are avaliable.")
            y, x = yx[np.random.randint(len(yx))]
            Grid.add_tile(self, x, y, self.name, self.NumBank[0], g)
        del self.NumBank[0]
    
    def MakeRandomAdjacentMove(self, owner, g):
        yx = np.argwhere(adj_mask)
        if len(yx) != 0:
            y, x = yx[np.random.randint(len(yx))]
            Grid.add_tile(self, x, y, self.name, self.NumBank[0], g)
        del self.NumBank[0]

    def MakeHumanMove(self, owner, g):
        while True:
            display_grid()
            move_input = input("Your number is", player.NumBank[0], "and your color is", str(player.name)+". \n", "What is your move? Structure it as X,Y: ")
            match = re.match(r"(\d+),\s*(\d+)", move_input)
            if match:
                x, y = map(int, match.groups())
                print(f"X: {x}, Y: {y}")
                inbounds = (xMin <= x < x_max and yMin <= y < y_max)
                if inbounds:
                    if get_owner(MainGrid[y][x]) == none and is_valid(MainGrid[y][x]):
                        break
                    else:
                        print("Invalid input.")
                else:
                    print("Out of bounds.")
        grid.add_tile(self, x, y, self.name, self.NumBank[0], g)

class Grid:
    def __init__(self, 
    x_max=10, y_max=8, 
    roll_max=20,
    hole_percentage=10,
    evenrowoffsets= [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)],
    oddrowoffsets=[(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
):
        # Grid dimensions and settings
        self.x_max = x_max  
        self.y_max = y_max  
        self.roll_max = roll_max
        self.hole_percentage = hole_percentage
        self.evenrowoffsets = evenrowoffsets
        self.oddrowoffsets = oddrowoffsets

        self.state = self.initialize_state()
        
        self.adj_mask = np.zeros((y_max, x_max), dtype=bool)

    
    def initialize_state(self):
        valid_bit = 0b1000000000000000
        grid = np.full((self.y_max, self.x_max), valid_bit, dtype=np.uint16)
        if self.hole_percentage != 0:
            hole_mask = np.random.rand(self.y_max, self.x_max) < (self.hole_percentage / 100)
            grid[hole_mask] = grid[hole_mask] & 0b0111111111111111 # This gets rid of the valid bits on the holes.
        grid = grid & 0b1111111110000000 # Clears the x and y bits. Probably unecessary, but it doesn't hurt.
        
        xMask = np.arange(0, self.y_max*self.x_max) % self.x_max 
        yMask = np.arange(0, self.y_max*self.x_max) // self.x_max # Makes a mask of the X and y values,
        xMask = xMask.reshape(self.y_max, self.x_max) # makes it shaped like the grid, 
        yMask = yMask.reshape(self.y_max, self.x_max)
        
        grid = grid | yMask # and applies it to the grid.
        grid = grid | xMask << 3 
        return grid
    
    def display(self, g):
        raise NotImplementedError
    
    def get_adjacent_tiles(self, x, y):
        offsets = np.array(self.evenrowoffsets if y % 2 == 0 else self.oddrowoffsets)  
        neighbor_coords = np.array([x, y]) + offsets
        ys, xs = neighbor_coords[:, 1], neighbor_coords[:, 0]
        in_bounds = (xs >= 0) & (xs < self.x_max) & (ys >= 0) & (ys < self.y_max)
        is_empty = (get_owner(neighbor_coords == none) & is_valid(neighbor_coords))
        ys, xs = ys[in_bounds & is_empty], xs[in_bounds & is_empty]
        return np.column_stack((xs, ys))

    def add_tile(self, x, y, owner, value, g): 
        if get_owner(self.grid[y][x]) != none: print("Critical Error! Tile already taken.")
        set_owner(self.grid[y][x], owner)
        set_value(self.grid[y][x], value)
        self.adj_mask[y][x] = 0

    def update_neighbors(self, x, y, pvalue, num):
        neighbors = get_adjacent_tiles(x, y)
        owners = get_owner(neighbors)
        values = get_value(neighbors)
        update_adjacency(self, xs, ys, neighbors, values)
        is_ally = (values == owners)
        is_weaker_enemy = ((values != owners) & (values != none)) & ((values < num) & (values != 0)) 
        if len(is_weaker_enemy != 0): set_owner(neighbors & is_weaker_enemy, pvalue)
        if len(is_ally != 0): set_value(neighbors & is_ally, values + 1)
        pvalue.score += num      

    def update_adjacency(self, xs, ys, neighbors, values):
        is_taken = (values != none)
        is_untaken = (values == none)
        self.adj_mask[ys[is_taken], xs[is_taken]] = 0
        self.adj_mask[ys[is_untaken], xs[is_untaken]] = 1  

class Winner:
    def __init__(self, name):
        self.name = []
        self.player = []
        self.score = 0

#endregion
#region LegacyCode
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

def ApplyMechanics(p, x, y, num, g, adjmask, adjtilesset, NumBank):
    
    IsAdjacentToSomethingCheck(x, y, g, adjmask, adjtilesset)
    g[y][x] = set_adjacent(g[y][x], False)
    adjmask[y][x] = False   
    if (x, y) in adjacent_tiles:
        adjacent_tiles.remove((int(x),int(y)))
    
    if is_valid(g[y][x]):
        g[y][x] = set_valid(g[y][x], False)
    else:
        print("Critical Error! Chose an invalid tile!!!!!")
    if not np.any(g & 0b1000000000000000):
      print("Critical Error, No valid tiles remain!")
      GetWinner(Player1, Player2, Player3)
      exit()
    offsets = np.array(EvenRowOffsets if y % 2 == 0 else OddRowOffsets)  
    
    neighbor_coords = np.array([x, y]) + offsets
    ys, xs = neighbor_coords[:, 1], neighbor_coords[:, 0]
    in_bounds = (xs >= 0) & (xs < x_max) & (ys >= 0) & (ys < y_max)
    ys, xs = ys[in_bounds], xs[in_bounds]
    
    values = get_value(g[ys, xs])
    x, y, num = int(x), int(y), int(num)
    
    if adjmask[y][x]:
      adjmask[y][x] = False;
      if (x, y) in adjtilesset:
        adjtilesset.remove((x, y))
      else:
        print("Warning! Tile in adjmask, but not adjacent tiles.")
    
    owners = get_owner(g[ys, xs])
    is_ally = (p.name == owners)
    is_enemy = ((p.name != owners) & (p.name != none))
    is_weaker_tile = (values < num) & (values != 0) 
    is_weaker_enemy = is_enemy & is_weaker_tile
    g[y][x] = set_owner(g[y][x], p.name)
    g[y][x] = set_value(g[y][x], num)
    p.score += num

    p.SumOfRolls += num
    if values[is_ally].size > 0: 
      values[is_ally] += 1
      p.score += np.count_nonzero(is_ally)
      tiles = g[ys, xs].copy()
      tiles[is_ally] = set_value(tiles[is_ally], values[is_ally])
      g[ys[is_ally], xs[is_ally]] = tiles[is_ally]

    if values[is_weaker_enemy].size > 0:
      p.score += int(np.sum(values[is_weaker_enemy]))
      tiles = g[ys, xs].copy()
      tiles[is_weaker_enemy] = set_owner(tiles[is_weaker_enemy], p.name)
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


def GameTest(p, p1, p2, stochastity, g, simnum, adjmask, adjtilesset, p3): 
    winners = []
    players = [p1, p2]
    if p3 is not None:
      players.append(p3)
    players = [p1, p2] + ([p3] if p3 else [])
    RelativeP1, RelativeP2, RelativeP3 = players[0], players[1], players[2] if len(players) > 2 else None
    root = np.copy(g)
    tempPlayer = copy.deepcopy(p)
    tempP1 = copy.deepcopy(RelativeP1)
    tempP2 = copy.deepcopy(RelativeP2)
    for _ in range(int(simnum)): # SHOULD BE SIMNUM
        p1tempnumbank = RelativeP1.NumBank.copy()
        p2tempnumbank = RelativeP2.NumBank.copy()
        random.shuffle(p1tempnumbank)
        random.shuffle(p2tempnumbank)
        if p3 != None:
            p3tempnumbank = RelativeP3.NumBank.copy()
            random.shuffle(p3tempnumbank)
            tempP3 = copy.deepcopy(RelativeP3)
        for num in p1tempnumbank:
            p1num, p2num, p3num = p1tempnumbank[0], p2tempnumbank[0], p3tempnumbank[0] if p3 else None
            if not np.any(g & 0b1000000000000000): 
                break
            GreedyBot(tempP1, 1, stochastity, root, adjtilesset, adjmask, p1tempnumbank[0]) # This starts the loop at player 1, but with simulations, this isn't always necessarily the case. Fix pls :3
            if not np.any(g & 0b1000000000000000): # Checks if any tile has the valid bit.
                break # if none do, break out of the loop.
            GreedyBot(tempP2, 1, stochastity, root, adjtilesset, adjmask, p2tempnumbank[0])
            if not np.any(g & 0b1000000000000000):
                break
            if PlayerCount == 3:
                if not np.any(g & 0b1000000000000000): 
                    break   
                GreedyBot(tempP3, 1, stochastity, root, adjtilesset, adjmask, p3tempnumbank[0])
        winner = GetWinner(tempP1, tempP2, None)
        winners.append(winner)
    MoveGoodness = EvalFromMoveList(winners, tempPlayer)
    return MoveGoodness

def MonteCarlosSearch(p, p1, p2, stochastity, fakegrid, adjmask, adjtilesset, simnum, num):
    if num == None:
        num = p.NumBank[0]
    move_list = [] 
    neighbors = np.argwhere(adjmask)  # Each element is [y, x]
    if len(neighbors) == 0:
        neighbors = np.argwhere(is_valid(fakegrid))
        
    for coord in neighbors:
        grid_copy = np.copy(fakegrid)
        y, x = coord
        move(p, num, x, y, grid_copy, adjmask, adjtilesset, p.NumBank)
        MoveGoodness = GameTest(p, p1, p2, stochastity, fakegrid, simnum, adjmask, adjtilesset, None)
        move_list.append((x, y, MoveGoodness))
    print("before i error out, here's the adjmask", np.argwhere(adjmask)) #debug
    best_move = max(move_list, key=lambda move: move[2])
    print("I, the humble MCTS bot, playing as", str(p.name)+",", "with number", str(num)+",", "chose my move to be", "("+str(best_move[0])+", "+str(best_move[1])+")", "out of", len(move_list)) # debug
    return best_move
            
def MCTSbot(p, p1, p2, stochastity, simnum):
    root = copy.deepcopy(MainGrid)
    adjmaskcopy = copy.deepcopy(adj_mask)
    adjtilesset = copy.deepcopy(adjacent_tiles)
    best_move = MonteCarlosSearch(p, p1, p2, stochastity, root, adjmaskcopy, adjtilesset, simnum, p.NumBank[0])
    move(p, p.NumBank[0], best_move[0], best_move[1], root, adjmask, adjtilesset, p.NumBank)
    

"""
YOU CAN VECTORISE GREEDY BOT! especially stochastity, you can probably make a really long list of random numbers using np and count through it
"""
def GreedyBot(p, greediness, stochastity, g, adjtilesset, adjmask, num): 
    if num == None:
        num = p.NumBank[0]
    if stochastity != 0 and stochastity > random.randint(1, 100):
        RandomMove(p, num, g)
    else:
      scores = OrderedSet()
      try:
        greediness = int(greediness)
      except ValueError:
        print("Warning, GreedyBot played a random move! Greediness not defined properly.")
        RandomMove(p, num)
        return
      if greediness > len(adjtilesset):
        greediness = len(adjtilesset)
      if len(adjtilesset) != 0:
          for x, y in adjtilesset:
              PossibleScore = ScoreFromAbsorption(p, x, y, g)
              scores.append(((x, y), PossibleScore))
          top_moves = sorted(scores, key=lambda item: item[1], reverse=True)[:greediness]
          best_move = random.choice(top_moves)
          (x, y), _ = best_move
          ApplyMechanics(p, x, y, num, g, adjmask, adjtilesset, p.NumBank[0])
      else:
          RandomMove(p, num, g, adjmask, adjtilesset, p.NumBank)

def RandomMove(p, num, g, adjmask, adjtilesset, NumBank):
    yx = np.argwhere(is_valid(g)) 
    if len(yx) != 0:
        y, x = yx[np.random.randint(len(yx))]
        ApplyMechanics(p, x, y, num, g, adjmask, adjtilesset, NumBank)
        return x, y
    
def RandomAdjacentTileBot(p, num, g, adjmask, adjtilesset, NumBank):
    if adjacent_tiles:
        print("Adjacent tile move made (move number", p.MoveNumber, ")")
        x, y = adjacent_tiles.pop()
        ApplyMechanics(p, x, y, num, g, adjmask, adjtilesset, NumBank)
        return True, x, y
    else:
        return RandomMove(p, num, g)

def GetWinner(p1, p2, p3):
    print(p1.name, p1.score, p2.name, p2.score, Player3.name, Player3.score)
    winner = Winner("")
    scores = [p1.score, p2.score]
    if p3 is not None:
        scores.append(p3.score)
    winner.score = max(scores)
    if p1.score == winner.score:
        winner.name.append(p1.name)
        winner.player.append("Player1")
    if p2.score == winner.score:
        winner.name.append(p2.name)
        winner.player.append("Player2")
    if p3 is not None and p3.score == winner.score:
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
  owners = (MainGrid & 0b0110000000000000) >> 13
  values = (MainGrid & 0b0001111100000000) >> 8
  valids = (MainGrid & 0b1000000000000000) > 0

  print("The scores are as follows:",
    str(Player1.name).capitalize() + ":", Player1.score,
    str(Player2.name).capitalize() + ":", Player2.score,
    str(Player3.name).capitalize() + ":", Player3.score)

  print("The current sum of rolls is",
    str(Player1.name).capitalize() + ":", Player1.SumOfRolls,
    str(Player2.name).capitalize() + ":", Player2.SumOfRolls,
    str(Player3.name).capitalize() + ":", Player3.SumOfRolls)

  print("   0   1   2   3   4   5   6   7   8   9")

  for y in range(y_max):
    row_str = ""
    for x in range(x_max):
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

def IsAdjacentToSomethingCheck(x, y, g, adjmask, adjtilesset):
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (xMin <= nx < x_max and yMin <= ny < y_max):
            continue
        if get_owner(g[ny][nx]) == none and is_valid(g[ny][nx]):
            if (nx, ny) not in adjtilesset:
                adjtilesset.add((nx, ny))
                adjmask[ny][nx] = True

def ScoreFromAbsorption(p, x, y, g):
    PossibleScore = 0
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (xMin <= nx < x_max and yMin <= ny < y_max):
            continue
        GridYxValue = get_value(g[ny][nx])
        ChosenSpot = g[ny][nx]
        if int(get_owner(ChosenSpot)) == int(p.name):
            PossibleScore += 1
        elif get_owner(ChosenSpot) !=none and get_owner(ChosenSpot) != p.name and p.NumBank[0] > GridYxValue:
            PossibleScore += GridYxValue
    return PossibleScore

def move(p, num, x, y, g, adjmask, adjtilesset, NumBank):
    if p is None or num is None or x is None or y is None:
        print("Warning: Parameter unset!")
    if not np.any(g & 0b1000000000000000):
        print("No valid tiles! Critical Error!")
    if not (0 <= x < x_max and 0 <= y < y_max):
        print("Out of bounds! Critical Error!")
    if get_owner(g[y][x]) != none:
        print("Tile already occupied! Critical Error!")
    ApplyMechanics(p, x, y, num, g, adjmask, adjtilesset, NumBank)

def Play(p, g, adjmask, adjtilesset, NumBank): # FIX THESE TO UTILISE THE GRID
    if p.FirstTime:
        random.shuffle(p.NumBank)
        p.FirstTime = False 
    if len(p.NumBank) == 0:
        display_grid()
        print("Whoops,", str(p.name)+"'s", "number bank ran out.")
        exit()
    if p.MoveType == 1:
        RandomMove(p, p.NumBank[0], g, adjmask, adjtilesset, p.NumBank)
    elif p.MoveType == 2:
        x, y = HumanMoveInput(p)
        move(p, p.NumBank[0], x, y, g, adjmask, adjtilesset, NumBank)
    elif p.MoveType == 3:
        MoveMade = RandomAdjacentTileBot(p, p.NumBank[0], g, adjmask, adjtilesset, p.NumBank)
    elif p.MoveType == 4:
        GreedyBot(p, 5, 0, g, adjtilesset, adjmask, p.NumBank[0])
    elif p.MoveType == 5:
        GreedyBot(p, 3, 0, g, adjtilesset, adjmask, p.NumBank[0])
    elif p.MoveType == 6:
        GreedyBot(p, 1, 0, g, adjtilesset, adjmask, p.NumBank[0])
    elif p.MoveType == 7:
        MCTSbot(p, Player1, Player2, MCTSStochasticity, MCTSSimnum)
    else:
        print("FATAL ERROR. Movetype is poorly defined.")
        exit()

def GameIsOver(gridshown, g):
    if not np.any(g & 0b1000000000000000):
        if gridshown == True:
            display_grid()
        return True
    return False

# def ResetStates():
#     player
# endregion

# region MainLoop
while True:
    if not np.any(MainGrid & 0b1000000000000000):
        break
    Play(Player1, MainGrid, adj_mask, adjacent_tiles, Player1.NumBank)
    if GameIsOver(True, MainGrid):
        break
    Play(Player2, MainGrid, adj_mask, adjacent_tiles, Player2.NumBank)
    if GameIsOver(True, MainGrid):
        break
    if PlayerCount == 3:
        if GameIsOver(True, MainGrid):
            break
        Play(Player3, MainGrid, adj_mask, adjacent_tiles, Player3.NumBank)
                  
GetWinner(Player1, Player2, Player3)
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
