# region Intro
"""
Hey! This is my first Python project!
I'm going to try to have a computer randomly play a game inspired by "Proximity" of Rod Pierce.
Proximity is a turn-based strategy game where players compete to control hexagonal tiles on a 10x8 grid. If you place a tile (each are d20)
of a higher value adjacent to an opponent's tile of a lower value, you absorb it. Next to an ally, the ally's tile(s) increases by one.
When all tiles are filled, the highest score wins.

Its name is Jef.

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
import re # regex
import sys
NONE, RED, GREEN, BLUE = "None", "Red", "Green", "Blue" # Players.
ChosenX = 0
ChosenY = 0
xMax = int(9) # Sets X parameter to 1-10.
yMax = int(7) # Sets Y parameter to 1-8.
xMin = int(0)
yMin = int(0)
RollMax = int(20) # Sets roll to d20.
PlayerCount = 2 # Sets players to Red & Blue.
global Scores
Scores = {RED: 0, BLUE: 0, GREEN: 0} # Score database.
count = 0
BlueFinalScore = []
RedFinalScore = []
GreenFinalScore = []
global done
done = bool(False)
grid = [[{"Owner": None, "Value": 0, "IsHole": False} for _ in range(yMax)] for _ in range(xMax)] # Adds a 10x8 grid, with each hexagon having their owner, value, hole status.
NumOfTiles = len(grid) * len(grid[0]) # Base * Height
NumOfOccurrences = int(np.ceil(NumOfTiles/(PlayerCount*RollMax))) # This is how often the number shows up in the word bank.
NumberBank = np.random.permutation([num for num in range(1, int(RollMax + 1)) for _ in range(NumOfOccurrences)]) # This gives each player a bank of shuffled, random numbers to choose from, so the game doesn't get too uneven.
ValidTiles = []
# endregion
# It's Coding Time!
# region 
def RandomMove(): # Just a function to call.
  ValidTiles = []
  for row in grid:
      for hexagon in row:
          if hexagon["Owner"] is None and not hexagon["IsHole"]: # Searches every row for valid hexagons (ones that aren't holes or taken).
              ValidTiles.append(hexagon)
         

  if ValidTiles:  # Ensure there is at least one valid tile to choose from
      ChosenHex = random.choice(ValidTiles)
      ChosenHex["Owner"] = "Red"
      ChosenHex["Value"] = int(random.choice(NumberBank))
      Scores[RED] += ChosenHex["Value"] # Adds the value to Red's final score.

for row in grid:
   for hexagon in row:
       if hexagon["Owner"] is None and not hexagon["IsHole"]: # Searches every row for valid hexagons (ones that aren't holes or taken).
           ValidTiles.append(hexagon)


def HumanMoveInput():
  while True:
    global inbounds
    global match
    global ChosenX
    global ChosenY
    move = input(f"What is your move? Structure it as X,Y : ")
    match = re.match(r"(\d+),\s*(\d+)", move) # Extracts X and Y from input.
    if match:
      ChosenY, ChosenX = map(int, match.groups())
      ChosenX, ChosenY = ChosenX - 1, ChosenY - 1
      print(f"X: {ChosenX}, Y: {ChosenY}")
      inbounds = bool(xMin<=ChosenX<=xMax and yMin<=ChosenY<=yMax)
      if inbounds:
        break
      else:
        print("Invalid input. Please enter in the format X,Y (e.g., 3,4).")
# endregion

while not done:
    # Find all valid hexagons (not taken and not holes)
    ValidTiles = [hexagon for row in grid for hexagon in row if hexagon["Owner"] is None and not hexagon["IsHole"]]

    if not ValidTiles: # If there aren't any valid tiles, end the loop.
        done = True
        break

    while ValidTiles: # While there are valid tiles,
        RandomMove() # have the computer do a random move,
        HumanMoveInput() # and then prompt for input.

        if not inbounds: # If the input is out of bounds, then inform the user so.
            print("Out of bounds, please try again.")
            HumanMoveInput()
            continue

        if grid[ChosenX][ChosenY]["Owner"] != None or grid[ChosenX][ChosenY]["Value"] != int(0): # If it's already taken, inform the user so.
            print("Tile already taken, please try again.")
            print("Tile chosen was", str(ChosenX)+",", str(ChosenY)+", inbounds is", str(inbounds)+", and the tile's owner and value are", grid[ChosenX][ChosenY]["Owner"], "and", str(grid[ChosenX][ChosenY]["Value"]), "respectively.", "Here is the grid. \n \n", grid) # Debugging
            HumanMoveInput()
            continue

        # However, if it's blank and a valid move, then assign the chosen tile an owner and a random value.
        grid[ChosenX][ChosenY]["Owner"] = "Blue"
        grid[ChosenX][ChosenY]["Value"] = int(random.choice(NumberBank))
        print(grid)
        print(NumberBank)


# region WinnerCheck
for row in grid: # Final score check--may be unnecessary if you add ot the score every turn, but given my code is unreliable, it's a good sanity check.
 for hexagon in row:
    if hexagon["Owner"] is Blue: 
      BlueFinalScore.append(hexagon[value])
    elif hexagon["Owner"] is Red: 
      RedFinalScore.append(hexagon[value])
    elif hexagon["Owner"] is Green:
      GreenFinalScore.append(hexagon[value])
print(BlueFinalScore, RedFinalScore, GreenFinalScore)

# region Checklist 
"""
Checklist
1) get a grid of tiles [✓]
2) manually place some hexagons [✓]
3) get turns working [✓] YAY
4) get an adjacency map (which tiles touch which) [X]
5) implement logic (absorbing adjacent enemies, reinforcing allies) [X]
6) determine score on-the-go, without relying on checking every score in the loop [X]
7) determine winner at the end [X]
8) get a representation of the grid (graphical or text-based, depending on how silly you feel) [X]
9) get some basic rules-based bots to play against [X]
10) impliment MCTS bots to encourage deeper thinking [X]
11) plug this into something like pytorch--first random, then easy, medium, hard, MCTS easy, medium, hard, and then self-play [X]
""" 
# endregion
# region misc
"""
other important things!
instead of red, green. and blue, for the AI training maybe self, opp1, and opp2 would be wiser.
randomise which player the AI is playing as !!
save every 100th game or so
optimise to hell before AI training! try to make state values binary 
(e.g., instead of [[{'Owner': 'Blue', 'Value': 5, 'IsHole': False}, try 
1100100
(11 = blue, 10 = red, 01 = green, 00 = none; 5=00101; false = 0)

maybe for some rules based ones

easy) play a random move out of the greediest 5
medium) play a random move of the greediest 3
hard) play the greediest move
MCTS easy) use 2-ply search 
MCTS hard) use the highest computationally reasonable search
"""
#endregion