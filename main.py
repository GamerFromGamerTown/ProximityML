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
# 1 = rand, 2 = human
Move1Type = 1 # HUMAN DOESN'T WORK, FIX IT !!
Move2Type = 1
Move3Type = 1
PlayerCount = 2 
NumBank1 = NumBank2 = NumBank3 = list(range(1, 21)) * 2
random.shuffle(NumBank1)
random.shuffle(NumBank2)
random.shuffle(NumBank3)
NONE, RED, GREEN, BLUE = "None", "Red", "Green", "Blue" # Players.
xMax = int(9) # Sets X parameter to 1-10.
yMax = int(7) # Sets Y parameter to 1-8.
xMin = int(0)
yMin = int(0)
RollMax = int(20) # Sets roll to d20.
count = 0
ValidTiles = []
grid = [[{"Owner": "None", "Value": 0, "IsHole": False, "IsAdjacent": False, "IsValid": True} for _ in range(xMax)] for _ in range(yMax)] # Adds a 10x8 grid, with each hexagon having their owner, value, hole status.
EvenRowOffsets = [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
OddRowOffsets  = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
valid_tiles = set()
adjacent_tiles = set()
# endregion
# It's Coding Time!
# region MainFunc

class Player:
  def __init__(self, name):
    self.name = name
    self.score = 0
    self.NumBank = list(range(1, 21)) * 2
    self.FirstTime = True


def PlayerAssignment():
  PossiblePlayers = [RED, GREEN, BLUE]
  PlayerNums = ["Player1", "Player2", "Player3"]
  temp = random.sample(PossiblePlayers, 3)
  global Player1
  global Player2
  global Player3
  Player1, Player2, Player3 = Player(temp[0]), Player(temp[1]), Player(temp[2])

PlayerAssignment()

def ApplyMechanics(player, x, y):
    offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets # If X is even, check which tiles it's congruent to.
    for dx, dy in offsets: # It repeats this six times, for every possible neighbour.
      new_x, new_y = x + dx, y + dy
      if not (xMin <= new_x < xMax and yMin <= new_y < yMax): # Checks if it's inbounds
        continue # If it is not, move to the next possible adjacent hexagon.
      ChosenSpot = grid[new_y][new_x] 
      if str(ChosenSpot["Owner"].lower()) == str(player.name.lower()):
        ChosenSpot["Value"] += 1
        player.score += 1
      elif ChosenSpot["Owner"] and ChosenSpot["Owner"] != player and ChosenSpot["Value"] < grid[y][x]["Value"]:
        player.score += ChosenSpot["Value"]
        if str(ChosenSpot["Owner"].lower()) == str(Player1.name.lower()):
          #print(ChosenSpot["Value"])
          Player1.score -= int(ChosenSpot["Value"])
        elif str(ChosenSpot["Owner"].lower()) == str(Player2.name.lower()):
          Player2.score -= int(ChosenSpot["Value"])
        elif str(ChosenSpot["Owner"].lower()) == str(Player3.name.lower()):
          Player3.score -= int(ChosenSpot["Value"])
        ChosenSpot["Owner"] = player.name
        player.score += grid[y][x]["Value"]

def RandomMove(player, num): # Just a function to call.
  if ValidTiles:  # Ensure there is at least one valid tile to choose from
      choice = random.randint(0, len(ValidTiles)-1)
      ChosenHex = ValidTiles[choice]
      x, y = int(choice) % xMax, int(choice) // xMax
      ChosenHex["Owner"] = player.name
      ChosenHex["Value"] = num
      Scores[player.name] += ChosenHex["Value"] # Adds the value to the player's final score.
      return x, y

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
  ValidTiles = [hexagon for row in grid for hexagon in row if hexagon["Owner"] == "None" and not hexagon["IsHole"]] 
  if player is None or num is None or x is None or y is None:
    print("Warning: Parameter unset!")
  if not ValidTiles: # If there aren't any valid tiles, end the loop.
    print("Invalid choice! Critical Error!")
    #break
  if not (0 <= x <= xMax and 0 <= y <= yMax): # Checks if it's inbounds
    print("Out of bounds! Critical Error!")
    #break
  if grid[y][x]["Owner"] != "None":
    print("Tile already occupied! Critical Error!")
    #break
  grid[y][x]["Owner"] = player
  grid[y][x]["Value"] = int(num)
  ApplyMechanics(player, x, y)

def IsAdjacentCheck(x, y):
  offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets # If X is even, check which tiles it's congruent to.
  for dx, dy in offsets: # It repeats this six times, for every possible neighbour.
    new_x, new_y = x + dx, y + dy
    if not (xMin <= new_x < xMax and yMin <= new_y < yMax): # Checks if it's inbounds
      continue # If it is not, move to the next possible adjacent hexagon.
    ChosenSpot = grid[y][x] 
    if ChosenSpot["Owner"] != None:
      IsAdjacent = bool(1)
      return IsAdjacent
      break
  IsAdjacent = bool(0)
  return IsAdjacent

def ScoreFromAbsorption(x,y):
  PossibleScore = 0
  offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets # If X is even, check which tiles it's congruent to.
  for dx, dy in offsets: # It repeats this six times, for every possible neighbour.
    new_x, new_y = x + dx, y + dy
    if not (xMin <= new_x < xMax and yMin <= new_y < yMax): # Checks if it's inbounds
      continue # If it is not, move to the next possible adjacent hexagon.
    ChosenSpot = grid[new_y][new_x] 
    if str(ChosenSpot["Owner"].lower()) == str(player.name.lower()):
      PossibleScore += 1
    elif ChosenSpot["Owner"] and ChosenSpot["Owner"] != player and ChosenSpot["Value"] < grid[y][x]["Value"]:
      PossibleScore += ChosenSpot
  return PossibleScore


def Play(player):
  if player.FirstTime:
    random.shuffle(player.NumBank)
    player.FirstTime = False 
  if len(player.NumBank) == 0:
    print("My work here is done.")
    exit()
  if Move1Type == 1:
    x, y = RandomMove(player, player.NumBank[0])
    ApplyMechanics(player, x, y)
    del player.NumBank[0]
  if Move2Type == 2:
    x, y = HumanMoveInput()
    move(player, player.NumBank[0], x, y)
    del player.NumBank[0]

# endregion

# region MainLoop
ValidTiles = [hexagon for row in grid for hexagon in row if hexagon["Value"] == int(0) and not hexagon["IsHole"]]  # Consider removing the hole check.

while True:
  ValidTiles = [hexagon for row in grid for hexagon in row if hexagon["Value"] == int(0) and not hexagon["IsHole"]]  # Consider removing the hole check.
  if not ValidTiles:
    print(grid)
    break
  Play(Player1)
  Play(Player2)
  if PlayerCount == 3:
    Play(Player3)
  
print(Player1.name, Player1.score, Player2.name, Player2.score, Player3.name, Player3.score) 
winner = max(Player1.score, Player2.score, Player3.score)
if Player1.score == winner: # Definitely a better way to do this, just a stopgap.
  print("Player1 is the winner!", "("+Player1.name+")")
elif Player2.score == winner:
  print("Player2 is the winner!", "("+Player1.name+")")
elif Player3.score == winner:
  print("Player3 is the winner!", "("+Player1.name+")")
else:
  print("A tie I'm too lazy to sort out!")

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
12) optimise, esp. state values and excessive loops [X]
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

reallyeasy) consider round(ValidTiles/8) random moves, the greediest wins
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
