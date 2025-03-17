# region Intro
"""
Hey! This is my first Python project!
I'm going to try to have a computer randomly play a game inspired by "Proximity" of Rod Pierce.
Proximity is a turn-based strategy game where players compete to control hexagonal tiles on a 10x8 grid. If you place a tile (each are d20)
of a higher value adjacent to an opponent's tile of a lower value, you absorb it. Next to an ally, the ally's tile(s) increases by one.
When all tiles are filled, the highest score wins.

Its name is Jef, thanks to a suggestion from a classmate.

This is the first step to using reinforcement learning to try to learn how to play this game.
I may take two training approaches, a binary training approach (all wins/losses are rewarded equally, no matter the margin), and a margin-based
approach (a landslide win is super to a thin one), and I want to see which plays better. I'm guessing the binary one will, but here's for trying!

If there's any suggestions you have, let me know!
Best,
-Gaymer <3
"""
# endregion

# region Initialize
import numpy as np 
import random
import re # rege
import sys
#import noise
# This controls what type of player p1, p2, and p3 are.
# 1: random, 2: human, 3: RandomAdjacentToSomethingMove, 
p1movetype = 1 # keep these 3 vars! they're used to define the actual value
p2movetype = 1
p3movetype = 1
HoleRandomnessType = 1 # 0 for 1 for pure randomness, 2 for perlin (which isn't yet implemented)
PlayerCount = 3 
NumBank1 = NumBank2 = NumBank3 = list(range(1, 21)) * 2
random.shuffle(NumBank1)
random.shuffle(NumBank2)
random.shuffle(NumBank3)
none, red, green, blue = "none", "red", "green", "blue" # Players.
xMax = int(10) # Sets X parameter to 1-10.
yMax = int(8) # Sets Y parameter to 1-8.
xMin = int(0)
yMin = int(0)
RollMax = int(20) # Sets roll to d20.
# Adds a 10x8 grid, with each hexagon having their owner, value, hole status. If it's a hole, it's invalid (opposite of IsHole).
EvenRowOffsets = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
OddRowOffsets  = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
valid_tiles = set()  
adjacent_tiles = [] 

if HoleRandomnessType == 0:
  grid = [[{"Owner": "none", "Value": 0, "IsHole": False, "IsAdjacent": False} for _ in range(xMax)] for _ in range(yMax)]
if HoleRandomnessType == 1:
  grid = [[{"Owner": "none", "Value": 0, "IsHole": True if random.random() < 0.1 else False, "IsAdjacent": False} for _ in range(xMax)] for _ in range(yMax)]
else:
  print("Warning, HoleRandomnessType is poorly defined. Proceeding with no holes.")
  grid = [[{"Owner": "none", "Value": 0, "IsHole": False, "IsAdjacent":False} for _ in range(xMax)] for _ in range(yMax)]


for y, row in enumerate(grid):
  for x, hexagon in enumerate(row):
    if hexagon["IsHole"] == False and hexagon["Value"] == 0:
      valid_tiles.add((x,y))

valid_tiles = list(valid_tiles)  # Convert set to list
random.shuffle(valid_tiles)  # Now we can shuffle it ! (why is valid_tiles not a list to begin with?)

# endregion
# It's Coding Time!
# region MainFunctions

class Player:
  def __init__(self, name):
    self.name = name
    self.score = 0
    self.NumBank = list(range(1, RollMax+1)) * 2
    self.FirstTime = True
    self.MoveType = 0


def PlayerAssignment():
  PossiblePlayers = [red, green, blue]
  PlayerNums = ["Player1", "Player2", "Player3"]
  temp = random.sample(PossiblePlayers, 3)
  global Player1
  global Player2
  global Player3
  Player1, Player2, Player3 = Player(temp[0]), Player(temp[1]), Player(temp[2]) # This makes each player randomly either red, green, or blue,
  Player1.MoveType = p1movetype 
  Player2.MoveType = p2movetype
  Player3.MoveType = p3movetype
  owner_to_player = {Player1.name: Player1, Player2.name: Player2, Player3.name: Player3}

PlayerAssignment()

def ApplyMechanics(player, x, y):
  base_value = grid[y][x]["Value"]  # value of the newly placed tile
  offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
  if (x,y) in adjacent_tiles:
    adjacent_tiles.remove((x,y))
  for dx, dy in offsets:
    new_x, new_y = x + dx, y + dy
    if not (xMin <= new_x < xMax and yMin <= new_y < yMax):
      continue
    neighbor = grid[new_y][new_x]
    # This reinforces surrounding tiles if it's owned by the player.
    if neighbor["Owner"] == player.name:
      neighbor["Value"] += 1
      player.score += 1
    # if neighbor is owned by an opponent and its value is less than the new tile's value
    elif neighbor["Owner"] != "none" and neighbor["Owner"] != player.name:
      if neighbor["Value"] < base_value:
        # Subtract the neighbor's value from the opponent
        if neighbor["Owner"] == Player1.name:
          Player1.score -= neighbor["Value"]
        elif neighbor["Owner"] == Player2.name:
          Player2.score -= neighbor["Value"]
        elif neighbor["Owner"] == Player3.name:
          Player3.score -= neighbor["Value"]
        # Add the neighbor's value to the current player's score
        player.score += neighbor["Value"]
        # Finally, change ownership of the neighbor tile
        neighbor["Owner"] = player.name

def EndGame():
  print(Player1.name, Player1.score, Player2.name, Player2.score, Player3.name, Player3.score) 
  winner = max(Player1.score, Player2.score, Player3.score)
  if Player1.score == winner: # Definitely a better way to do this, just a stopgap.
    print("Player1 is the winner!", "("+Player1.name+")")
  elif Player2.score == winner:
    print("Player2 is the winner!", "("+Player2.name+")")
  elif Player3.score == winner:
    print("Player3 is the winner!", "("+Player3.name+")")
  else:
    print("A tie I'm too lazy to sort out!")
  # SCHLAWG !! use enumerate()!

def RandomMove(player, num): # Just a function to call.
  if valid_tiles:  # Ensure there is at least one valid tile to choose from  
    x, y = valid_tiles.pop()
    ChosenHex = grid[y][x]
    ChosenHex["Owner"] = player.name
    ChosenHex["Value"] = num
    ApplyMechanics(player, x, y)
    player.score += ChosenHex["Value"] # Adds the value to the player's final score.
    return x, y


def RandomAdjacentTileBot(player, num):
  count = 0 
  count1 = 0
  if adjacent_tiles:  # Ensure there is at least one valid tile to choose from
    count += 1
    print("Adjacent tile, made adjacent move number", count1)
    x, y = adjacent_tiles.pop()
    ChosenHex = grid[y][x]
    ChosenHex["Owner"] = player.name
    ChosenHex["Value"] = num
    player.score += ChosenHex["Value"] # Adds the value to the player's final score.
    if (x, y) in valid_tiles:
      valid_tiles.remove((x, y))
    ApplyMechanics(player, x, y)
    IsAdjacentToSomethingCheck(x, y)
    MoveMade = True
    return MoveMade, x, y
  elif valid_tiles and not adjacent_tiles:
    count += 1
    print("No adjacent tile, forced to make random move number", count)
    x, y = RandomMove(player, num)
    MoveMade = True
    return MoveMade, x, y


def HumanMoveInput():
  while True:
    move = input(f"What is your move? Structure it as X,Y : ")
    match = re.match(r"(\d+),\s*(\d+)", move) # Extracts X and Y from input.
    if match:
      x, y = map(int, match.groups())
      print(f"X: {x}, Y: {y}")
      inbounds = bool(xMin<=x<=xMax and yMin<=y<=yMax)
      if inbounds == True:
        return x, y
        break
      else:
        print("Invalid input.")
        continue

def move(player, num, x, y):
  if player is None or num is None or x is None or y is None:
    print("Warning: Parameter unset!")
  if not valid_tiles: # If there aren't any valid tiles, end the loop.
    print("Invalid choice! Critical Error!")
  if not (0 <= x <= xMax and 0 <= y <= yMax): # Checks if it's inbounds
    print("Out of bounds! Critical Error!")
  if grid[y][x]["Owner"] != "none":
    print("Tile already occupied! Critical Error!")
  grid[y][x]["Owner"] = player.name
  grid[y][x]["Value"] = int(num)
  valid_tiles.remove((x,y))
  ApplyMechanics(player, x, y)

def IsAdjacentToSomethingCheck(x, y):
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
    for dx, dy in offsets:
        nx, ny = x + dx, y + dy
        # Check if within bounds.
        if not (xMin <= nx < xMax and yMin <= ny < yMax):
            continue
        # Only add if the tile is empty, not a hole, and not already in adjacent_tiles.
        if grid[ny][nx]["Owner"] == "none" and not grid[ny][nx]["IsHole"]:
            if (nx, ny) not in adjacent_tiles:
                adjacent_tiles.append((nx, ny))


def ScoreFromAbsorption(player, x,y):
  PossibleScore = 0
  offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets # If X is even, check which tiles it's congruent to.
  for dx, dy in offsets: # It repeats this six times, for every possible neighbour.
    new_x, new_y = x + dx, y + dy
    if not (xMin <= new_x < xMax and yMin <= new_y < yMax): # Checks if it's inbounds
      continue # If it is not, move to the next possible adjacent hexagon.
    ChosenSpot = grid[new_y][new_x] 
    if str(ChosenSpot["Owner"]) == str(player.name):
      PossibleScore += 1
    elif ChosenSpot["Owner"] and ChosenSpot["Owner"] != player.name and ChosenSpot["Value"] < grid[new_y][new_x]["Value"]:
      PossibleScore += ChosenSpot
  return PossibleScore


def Play(player):
  if player.FirstTime:
    random.shuffle(player.NumBank)
    player.FirstTime = False 
  if len(player.NumBank) == 0:
    print(grid)
    print("My work here is done.")
    exit()
  if player.MoveType == 1:
    x, y = RandomMove(player, player.NumBank[0])
    IsAdjacentToSomethingCheck(x, y)
    del player.NumBank[0]
  if player.MoveType == 2:
    x, y = HumanMoveInput()
    move(player, player.NumBank[0], x, y)
    del player.NumBank[0]
    print(grid)
  if player.MoveType == 3:
    MoveMade = RandomAdjacentTileBot(player, player.NumBank[0])
    if MoveMade:
      del player.NumBank[0]
    else: 
      print("Critical error! Move not recorded!")
    # THESE IF-THEN STATEMENTS WORK!!
    # (but are inefficent)
    # consider replacing them with something more dynamic!

def ValidTilesCheck():
  if not valid_tiles:
    print(grid)
    return True
  return False
# endregion
# region MainLoop
while True:
  if not valid_tiles:
    print(grid)
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

"""
possible helping code for the optimisation of play()
def move_random(player, num):
  x, y = RandomMove(player, num)
  ApplyMechanics(player, x, y)
  return x, y

def move_human(player, num):
  x, y = HumanMoveInput()
  move(player, player.NumBank[0], x, y)
  del player.NumBank[0]
  return x, y
  print(grid)

move_functs = {
  1: move_random,
  2: move_human
}
"""
# endregion
# region Checklist 

# HEY YOY!

# all of these loops are a huge headache; things like IsAdjacent and ValidTile can be calculated on
# the fly, with something like a dictionary or a class (?). like if (2, 4) is taken, its attribute
# ValidTile would be set to 0, and all adjacent tiles would be set to IsAdjacent. huge computational
# timesaver. DO IT NEXT !!!! (or maybe later, idk--just 3 minutes for 1000 random (!!) games is a lot)

# maybe, to prevent all the scanning of a full list, put things like IsAdjacent and ValidTile into
# their own, separate list that's faster to sort through. idk how translating x, y would work though

# if the robot is reading that and i'm not working on it, remind me !! (please :3)

"""
Checklist
1) get a grid of tiles [✓]
2) manually place some hexagons [✓]
3) get turns working [✓] YAY
4) determine which tiles touch which [✓]
5) get a representation of the grid (text-based first, hopefully graphical later) [X]
5.5) randomise who plays as who [✓]
6) implement logic (absorbing adjacent enemies, reinforcing allies) [✓] HELL YEAH
7) determine score on-the-go, without relying on checking every score in the loop [✓]
8) determine winner at the end [✓]
9) get "holes" working [X]
10) get some basic rules-based bots to play against [X] 
11) implement MCTS bots to encourage deeper thinking [X]
12) optimise, esp. state values and excessive loops [-] # IsAdjacent is very expensive current-form.
13) plug this into something like pytorch--first random, then easy, medium, hard, MCTS easy, hard, and then self-play [X]
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
