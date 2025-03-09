# Jef
## the lean, mean, hexagonal machine.

Hey! This is my first Python project! I'm trying to have a computer learn via reinforcement learning a game inspired by "Proximity", of Rod Pierce. 

Proximity is a turn-based strategy game where players compete to control hexagonal tiles on a 10x8 grid. Every turn, you place a hexagon, whose value is randomly* determined to be between 1 and 20. If you place a hexagon adjacent to an enemy of a lower value, you absorb it. If you place a tile adjacent to any ally, you increase its value by one, making it harder to absorb it. The highest score at the end wins!



### Try out Proximity!
https://www.mathsisfun.com/games/proximity.html

* I used a bank of 2 of each number between 1 and 20 so the game doesn't get too imbalanced--so the numbers aren't random in the truest sense. 
