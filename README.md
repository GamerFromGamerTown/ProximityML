# Jef
## the lean, mean, hexagonal machine.

Hey! This is my first Python project! I'm trying to have a computer learn via reinforcement learning a game inspired by "Proximity", of Rod Pierce. 

Proximity is a turn-based strategy game where players compete to control hexagonal tiles on a 10x8 grid. Every turn, you place a hexagon, whose value is randomly* determined to be between 1 and 20. If you place a hexagon adjacent to an enemy of a lower value, you absorb it. If you place a tile adjacent to any ally, you increase its value by one, making it harder to absorb it. The highest score at the end wins!



### Try out Proximity!
https://www.mathsisfun.com/games/proximity.html

* I used a bank of 2 of each number between 1 and 20 so the game doesn't get too imbalanced--so the numbers aren't random in the truest sense. 

### Glossary

- **Stochastic**  
  Having a random probability distribution or pattern.

- **Greedy**  
  Playing whichever move maximizes immediate reward. For example, points—without looking ahead.

- **(Random, Greedy) Rollout**  
  Playing a full or partial game simulation from a given position, using a specific move policy (e.g., random, greedy). In this project, rollout usually means greedy play with some added stochasticity.

- **Flat Monte Carlo Search (MCS)**  
  A strategy that evaluates many or all moves in a position, performs a certain number of rollouts for each, and selects the move with the best result (e.g., highest win rate, lowest loss rate).

- **Monte Carlo Tree Search (MCTS)**  
  A strategy that builds a tree by selectively exploring moves based on results from rollouts. It balances exploration of new moves and exploitation of known good moves. I see this as infeasible for this project, since there is so much randomness after the first few moves that one will almost never see the same position twice.

- **MinMax**  
  A strategy that assumes both players play optimally: it chooses the move that minimizes the maximum advantage the opponent could gain (hence the name MinMax). Can search deeply when supported by efficient evaluation methods.
