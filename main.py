# NOT production ready
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
import re  # regex
import sys
#sys.stdout = None  # Disable all printing if desired as a speed check

# These control the player types:
p1movetype = 6  # e.g., 1: random, 2: human, 3: RandomAdjacentTileBot, etc.
p2movetype = 1
p3movetype = 3
HoleRandomnessType = 0  # 0 for none, 1 for pure randomness, 2 for perlin (not yet implemented)
PlayerCount = 2 

# Number banks (shuffled)
NumBank1 = NumBank2 = NumBank3 = list(range(1, 21)) * 2
random.shuffle(NumBank1)
random.shuffle(NumBank2)
random.shuffle(NumBank3)

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


# Hexagonal neighbour offsets (depending on row parity)
EvenRowOffsets = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
OddRowOffsets  = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]

# Sets to track valid and adjacent tiles (using (x, y) tuples)
valid_tiles = set()  
adjacent_tiles = OrderedSet()

def numpyify(x):
  return np.uint16(~x & 0xFFFF)

def get_owner(tile):
    mask = 0b0110000000000000
    result = tile & numpyify(mask)
    owner = result >> 13
    return owner

def set_owner(tile, owner):
    mask = 0b0110000000000000  # Bits 13 and 14
    cleared = tile & ~mask     # Zero out owner bits
    result = cleared | (owner << 13)
    return np.uint16(result)

def get_value(tile):
    mask = 0b0001111100000000
    result = tile & numpyify(mask)
    owner_value = result >> 8
    return owner_value

def set_value(tile, value):
  mask =  0b0001111100000000
  result = tile &~ numpyify(mask)
  return (value << 8) | result

def is_valid(tile):
  mask =  0b1000000000000000
  return bool(tile & mask)

if HoleRandomnessType == 0:
    # This sets bit 15 (0b1000000000000000) indicating a valid tile.
    grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
elif HoleRandomnessType == 1:
    grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
    hole_mask = np.random.rand(8, 10) < 0.1  
    # Remove the valid bit from holes (bitwise AND with complement)
    grid[hole_mask] = grid[hole_mask] & 0b0111111111111111  
else:
    print("Warning, HoleRandomnessType is poorly defined. Proceeding with no holes.")
    grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)

for y in range(yMax):
    for x in range(xMax):
        if grid[y][x] & 0b1000000000000000:  # if valid
            valid_tiles.add((x, y))
# endregion

# region MainFunctions

class Player:
    def __init__(self, name):
        self.name = name  # this holds the bit mask value for the player (red, green, or blue)
        self.score = 0
        self.NumBank = list(range(1, RollMax+1)) * 2
        self.FirstTime = True
        self.MoveType = 0
        self.MoveNumber = 0
        self.SumOfRolls = 0

def PlayerAssignment():
    # Randomly assign player colors for visualization.
    PossiblePlayers = [red, green, blue]
    temp = random.sample(PossiblePlayers, 3)
    global Player1, Player2, Player3
    Player1, Player2, Player3 = Player(temp[0]), Player(temp[1]), Player(temp[2])
    Player1.MoveType = p1movetype 
    Player2.MoveType = p2movetype
    Player3.MoveType = p3movetype
    # might also create a mapping from owner value to Player for later use.
    owner_to_player = {Player1.name: Player1, Player2.name: Player2, Player3.name: Player3}

PlayerAssignment()

def ApplyMechanics(player, x, y, num):
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    player.MoveNumber += 1
    if (x, y) in adjacent_tiles:
        adjacent_tiles.remove((x, y))
    if (x, y) in valid_tiles:
        valid_tiles.remove((x, y))
    # Update owner and value
    grid[y][x] = set_owner(grid[y][x], player.name)
    grid[y][x] = set_value(grid[y][x], num)

    # Update score based on new value
    base_value = get_value(grid[y][x])
    player.score += base_value

    
    player.SumOfRolls += num
    IsAdjacentToSomethingCheck(x, y)
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (xMin <= nx < xMax and yMin <= ny < yMax):
            continue
        neighbor = grid[ny][nx]
        NeighborOwner = get_owner(neighbor)
        NeighborValue = int(get_value(neighbor))
        if NeighborOwner == player.name:
            NewValue = NeighborValue + 1
            grid[ny][nx] = set_value(neighbor, NewValue)
            player.score += 1
        elif get_owner(neighbor) !=none and NeighborOwner != player.name and NeighborValue < base_value:
            # Adjust scores for the opponent whose tile is being absorbed.
            if NeighborOwner == Player1.name:
                Player1.score -= NeighborValue
            elif NeighborOwner == Player2.name:
                Player2.score -= NeighborValue
            elif NeighborOwner == Player3.name:
                Player3.score -= NeighborValue
            player.score += NeighborValue
            grid[ny][nx] = set_owner(grid[ny][nx], player.name)

def HardBot(player):
    scores = OrderedSet()
    if len(adjacent_tiles) != 0:
        for x, y in adjacent_tiles:
            PossibleScore = ScoreFromAbsorption(player, x, y)  # Ensure this function is updated to use bitwise ops later.
            scores.append(((x, y), PossibleScore))
        best_move = max(scores, key=lambda item: item[1])
        print(f"HardBot is choosing move: {best_move}, with score {best_move[1]}")
        (x, y), _ = best_move
        ApplyMechanics(player, x, y, player.NumBank[0])
    else:
        print("Warning, hardbot played a random move!")
        RandomMove(player, player.NumBank[0])

def MediumBot(player):
    scores = OrderedSet()
    if len(adjacent_tiles) != 0:
        for x, y in adjacent_tiles:
            PossibleScore = ScoreFromAbsorption(player, x, y)
            scores.append(((x, y), PossibleScore))
        # NOTE: The slicing used here on the max result ([-3:]) seems off.
        # You might want to sort the scores list and pick the top 3 moves.
        top_3 = sorted(scores, key=lambda item: item[1], reverse=True)[:3]
        best_move = random.choice(top_3)
        print(f"MediumBot is choosing move: {best_move}, with score {best_move[1]}")
        (x, y), _ = best_move
        ApplyMechanics(player, x, y, player.NumBank[0])
    else:
        print("Warning, MediumBot played a random move!")
        RandomMove(player, player.NumBank[0])

class Winner:
    def __init__(self, name):
        self.name = []
        self.player = []
        self.score = 0

def EndGame():
    print(Player1.name, Player1.score, Player2.name, Player2.score, Player3.name, Player3.score)
    winner = Winner("")
    winner.score = max(Player1.score, Player2.score, Player3.score)
    if Player1.score == winner.score:
        winner.name.append(Player1.name)
        winner.player.append("Player1")
    if Player2.score == winner.score:
        winner.name.append(Player2.name)
        winner.player.append("Player2")
    if Player3.score == winner.score:
        winner.name.append(Player3.name)
        winner.player.append("Player3")
    
    if len(winner.name) == 1:
        print("The winner of the game is", str(winner.player[0]), "("+str(winner.name[0])+")")
    elif len(winner.name) == 2:
        print("Two-way tie! The winners are", str(winner.player), "and their colors are", str(winner.name))
    elif len(winner.name) == 3:
        print("Three-way tie!! The winners are", str(winner.player), "and their colors are", str(winner.name))

def RandomMove(player, num):
    if valid_tiles:
        x, y = valid_tiles.pop()
        ApplyMechanics(player, x, y, num)
        return x, y

def RandomAdjacentTileBot(player, num):
    if player.MoveNumber != 0:
        print("Adjacent tile move made (move number", player.MoveNumber, ")")
        x, y = adjacent_tiles.pop()
        valid_tiles.remove((x, y))
        ApplyMechanics(player, x, y, num)
        IsAdjacentToSomethingCheck(x, y)
        return True, x, y
    else:
        return RandomMove(player, num)

def display_grid():
  count = -1
  print("The scores are as follows:", 
      str(Player1.name).capitalize()+":", Player1.score, 
      str(Player2.name).capitalize()+":", Player2.score, 
      str(Player3.name).capitalize()+":", Player3.score)
  print("The current sum of rolls is", 
      str(Player1.name).capitalize()+":", Player1.SumOfRolls, 
      str(Player2.name).capitalize()+":", Player2.SumOfRolls, 
      str(Player3.name).capitalize()+":", Player3.SumOfRolls)
  print("   0   1   2   3   4   5   6   7   8   9")
  for row in grid:
      count += 1
      row_str = ""
      for tile in row:
          TileValue = get_value(tile)
          if not is_valid(tile) and int(TileValue) != 0:
              symbol = " X "
          elif get_owner(tile) == none:
              symbol = " · "
          else:
              tV = TileValue
              if tV < 10:
                  tV = str(0)+str(tV)
              symbol = owner_symbols[get_owner(tile)]+str(tV)
          row_str += symbol + " "
      if count % 2 == 1:
          print(count, "  "+row_str)
      else:
          print(count, row_str)
  print("     0   1   2   3   4   5   6   7   8   9")

def HumanMoveInput(player):
    while True:
        print("The scores are as follows:", 
              str(Player1.name).capitalize()+":", Player1.score, 
              str(Player2.name).capitalize()+":", Player2.score, 
              str(Player3.name).capitalize()+":", Player3.score)
        print("The current sum of rolls is", 
              str(Player1.name).capitalize()+":", Player1.SumOfRolls, 
              str(Player2.name).capitalize()+":", Player2.SumOfRolls, 
              str(Player3.name).capitalize()+":", Player3.SumOfRolls)
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

def move(player, num, x, y):
    if player is None or num is None or x is None or y is None:
        print("Warning: Parameter unset!")
    if not valid_tiles:
        print("Invalid choice! Critical Error!")
    if not (0 <= x < xMax and 0 <= y < yMax):
        print("Out of bounds! Critical Error!")
    if get_owner(grid[y][x]) !=none:
        print("Tile already occupied! Critical Error!")
    valid_tiles.remove((x,y))
    ApplyMechanics(player, x, y, num)
    IsAdjacentToSomethingCheck(x, y)

def IsAdjacentToSomethingCheck(x, y):
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (xMin <= nx < xMax and yMin <= ny < yMax):
            continue
        if get_owner(grid[ny][nx]) == none and not is_valid(grid[ny][nx]):
            if (nx, ny) not in adjacent_tiles:
                adjacent_tiles.add((nx, ny))

def ScoreFromAbsorption(player, x, y):
    PossibleScore = 0
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        if not (xMin <= nx < xMax and yMin <= ny < yMax):
            continue
        GridYxValue = get_value(grid[ny][nx])
        ChosenSpot = grid[ny][nx]
        if int(get_owner(ChosenSpot)) == int(player.name):
            PossibleScore += 1
        elif get_owner(ChosenSpot) !=none and get_owner(ChosenSpot) != player.name and player.NumBank[0] > GridYxValue:
            PossibleScore += GridYxValue
    return PossibleScore

def Play(player):
    if player.FirstTime:
        random.shuffle(player.NumBank)
        player.FirstTime = False 
    if len(player.NumBank) == 0:
        display_grid()
        print("Whoops,", str(player.name)+"'s", "number bank ran out.")
        exit()
    if player.MoveType == 1:
        x, y = RandomMove(player, player.NumBank[0])
        IsAdjacentToSomethingCheck(x, y)
    elif player.MoveType == 2:
        x, y = HumanMoveInput(player)
        move(player, player.NumBank[0], x, y)
    elif player.MoveType == 3:
        MoveMade = RandomAdjacentTileBot(player, player.NumBank[0])
    elif player.MoveType == 5:
        MediumBot(player)
    elif player.MoveType == 6:
        HardBot(player)
    else:
        print("hey, movetype is poorly defined. Warning!")
    del player.NumBank[0]

def ValidTilesCheck():
    if not valid_tiles:
        display_grid()
        return True
    return False
# endregion

# region MainLoop
while True:
    if not valid_tiles:
        display_grid()
        break
    Play(Player1)
    if ValidTilesCheck():
        break
    Play(Player2)
    if ValidTilesCheck():
        break
    if PlayerCount == 3:
        if ValidTilesCheck():
            break
        Play(Player3)
  
EndGame()
print(grid)
print("Value at (0,0):", get_value(grid[0][0]))
# endregion
# region Checklist 

"""
Checklist
1) get a grid of tiles [✓]
2) manually place some hexagons [✓]
3) get turns working [✓] YAY
4) determine which tiles touch which [✓]
5) get a representation of the grid (text-based first, hopefully graphical later) [✓]
6) implement logic (absorbing adjacent enemies, reinforcing allies) [✓] HELL YEAH
7) determine score on-the-go, without relying on checking every score in the loop [✓]
8) determine winner at the end [✓]
9) get "holes" working [✓]
10) get some basic rules-based bots to play against [✓] 
11) optimise, esp. state values and excessive loops [-] # a lot harder than i thought
12) implement MCTS bots to encourage deeper thinking [X] # try greedy rollouts and random rollouts
13) plug this into something like pytorch--first random, then easy, medium, hard, MCTS easy, hard, and then self-play [X]
(note, MCTS might be impossible due to state-space explosion, at least on my hardware--minmax )
14) elo system? [X]
"""
# endregion
# region misc
"""
other important things!
save every 100th game or so
optimise to hell before AI training! try to make state values binary 
(e.g., instead of [[{'Owner': 'Blue', 'Value': 5, 'IsHole': False}, try 
1100100
(11 = blue, 10 = red, 01 = green, 00 = none; 5=00101; false = 0)

maybe for some rules based ones

reallyeasy) consider round(valid_tiles/8) random moves, the greediest wins
easy) play a random move out of the greediest 5
medium) play a random move of the greediest 3
hard) play the greediest move
MCTS easy) use 2-ply search 
MCTS hard) use the highest computationally reasonable search

for holes, maybe do perlin noise, add a bias to the sides 4,4, normalize so only 
10, 15, 20, and 30 tiles meet a threshold respectively (e.g. 0.3), and then
any tile above the threshold becomes a hole. batch generate like 50k of these and choose
them at random, and utilise them around 20-40% of the time. don't calculate 
on-the-fly, it would be really expensive
"""
#endregion
