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
from __future__ import annotations

# region Initialize
import numpy as np 
import random
import time
import copy
import re  # regex
"""Here's how the bits are structured!
bit 15 (the first one), shows if you can place a tile on it.
bits 14-13 (the next two) show their owner
bits 12-8 (the next 5) contain their value
bits 7-3 contain a tile's x value (so the AI can understand the grid better)
bits 2-0 contain a tile's y value
nice and snug!"""
VALID_MASK = 0b1000000000000000
OWNER_MASK = 0b0110000000000000
VALUE_MASK = 0b0001111100000000
X_BITS = 0b0000000011111000
Y_BITS = 0b0000000000000111
# Define player “colors” using bit masks
none, red, green, blue = 0b00, 0b01, 0b10, 0b11

owner_symbols = {
    0: "·",  # represents no owner
    1: "R",  # red
    2: "G",  # green
    3: "B"   # blue
}

# 15: IsValid, 14-13: Owner, 13-8 = value, 7 IsAdjacent, 6-3 x, 2-0 y (nice and snug)
# ADD AN X, Y BIT !! very useful for AI
def get_owner(tile):
    return (tile & OWNER_MASK) >> 13

def set_owner(tile, owner):
    cleared = tile & (~OWNER_MASK & 0xFFFF)     # Zero out owner bits
    result = cleared | (owner << 13)
    return np.uint16(result)

def get_value(tile):
    return (tile & VALUE_MASK) >> 8

def set_value(tile, value):
    cleared = tile & (~VALUE_MASK & 0xFFFF)
    return np.uint16(cleared | (value << 8))

def set_valid(tile, YN):
    cleared = tile & (~VALID_MASK & 0xFFFF)
    bit = (VALID_MASK if YN else 0)
    return np.uint16(cleared | bit)

def is_valid(tile):
  return tile & VALID_MASK

# endregion
# region PrimaryCode

from __future__ import annotations

# region Initialize
import numpy as np 
import random
import time
import copy
import re  # regex
"""Here's how the bits are structured!
bit 15 (the first one), shows if you can place a tile on it.
bits 14-13 (the next two) show their owner
bits 12-8 (the next 5) contain their value
bits 7-3 contain a tile's x value (so the AI can understand the grid better)
bits 2-0 contain a tile's y value
nice and snug!"""
VALID_MASK = 0b1000000000000000
OWNER_MASK = 0b0110000000000000
VALUE_MASK = 0b0001111100000000
X_BITS = 0b0000000011111000
Y_BITS = 0b0000000000000111
# Define player “colors” using bit masks
none, red, green, blue = 0b00, 0b01, 0b10, 0b11

owner_symbols = {
    0: "·",  # represents no owner
    1: "R",  # red
    2: "G",  # green
    3: "B"   # blue
}

# 15: IsValid, 14-13: Owner, 13-8 = value, 7 IsAdjacent, 6-3 x, 2-0 y (nice and snug)
# ADD AN X, Y BIT !! very useful for AI
def get_owner(tile):
    return (tile & OWNER_MASK) >> 13

def set_owner(tile, owner):
    cleared = tile & (~OWNER_MASK & 0xFFFF)     # Zero out owner bits
    result = cleared | (owner << 13)
    return np.uint16(result)

def get_value(tile):
    return (tile & VALUE_MASK) >> 8

def set_value(tile, value):
    cleared = tile & (~VALUE_MASK & 0xFFFF)
    return np.uint16(cleared | (value << 8))

def set_valid(tile, YN):
    cleared = tile & (~VALID_MASK & 0xFFFF)
    bit = (VALID_MASK if YN else 0)
    return np.uint16(cleared | bit)

def is_valid(tile):
  return tile & VALID_MASK

# endregion
# region PrimaryCode

from __future__ import annotations

# region Initialize
import numpy as np 
import random
import time
import copy
import re  # regex
"""Here's how the bits are structured!
bit 15 (the first one), shows if you can place a tile on it.
bits 14-13 (the next two) show their owner
bits 12-8 (the next 5) contain their value
bits 7-3 contain a tile's x value (so the AI can understand the grid better)
bits 2-0 contain a tile's y value
nice and snug!"""
VALID_MASK = 0b1000000000000000
OWNER_MASK = 0b0110000000000000
VALUE_MASK = 0b0001111100000000
X_BITS = 0b0000000011111000
Y_BITS = 0b0000000000000111
# Define player “colors” using bit masks
none, red, green, blue = 0b00, 0b01, 0b10, 0b11

owner_symbols = {
    0: "·",  # represents no owner
    1: "R",  # red
    2: "G",  # green
    3: "B"   # blue
}

# 15: IsValid, 14-13: Owner, 13-8 = value, 7 IsAdjacent, 6-3 x, 2-0 y (nice and snug)
# ADD AN X, Y BIT !! very useful for AI
def get_owner(tile):
    return (tile & OWNER_MASK) >> 13

def set_owner(tile, owner):
    cleared = tile & (~OWNER_MASK & 0xFFFF)     # Zero out owner bits
    result = cleared | (owner << 13)
    return np.uint16(result)

def get_value(tile):
    return (tile & VALUE_MASK) >> 8

def set_value(tile, value):
    cleared = tile & (~VALUE_MASK & 0xFFFF)
    return np.uint16(cleared | (value << 8))

def set_valid(tile, YN):
    cleared = tile & (~VALID_MASK & 0xFFFF)
    bit = (VALID_MASK if YN else 0)
    return np.uint16(cleared | bit)

def is_valid(tile):
  return tile & VALID_MASK

# endregion
# region PrimaryCode

class GameState:
    def __init__(self, 
    turn = 0,
    x_max=10, y_max=8, 
    roll_max=20,
    hole_percentage=10,
    evenrowoffsets= [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)],
    oddrowoffsets=[(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)]
):
        # Grid dimensions and settings
        self.turn = turn
        self.x_max = x_max  
        self.y_max = y_max  
        self.roll_max = roll_max
        self.hole_percentage = hole_percentage
        self.evenrowoffsets = evenrowoffsets
        self.oddrowoffsets = oddrowoffsets

        self.state = self.initialize_state()
        
        self.adj_mask = np.zeros((y_max, x_max), dtype=bool)

    
    def initialize_state(self):
        grid = np.full((self.y_max, self.x_max), VALID_MASK, dtype=np.uint16)
        if self.hole_percentage != 0:
            hole_mask = np.random.rand(self.y_max, self.x_max) < (self.hole_percentage / 100)
            grid[hole_mask] &= ~VALID_MASK # This gets rid of the valid bits on the holes.
        
        xMask = np.arange(0, self.y_max*self.x_max) % self.x_max 
        yMask = np.arange(0, self.y_max*self.x_max) // self.x_max # Makes a mask of the X and y values,
        xMask = xMask.reshape(self.y_max, self.x_max) # makes it shaped like the grid, 
        yMask = yMask.reshape(self.y_max, self.x_max)
        
        grid = grid | yMask # and applies it to the grid.
        grid = grid | xMask << 3 
        return grid
    
    def display(self):
        raise NotImplementedError
    
    def get_adjacent_tiles(self, x, y):
        offsets = np.array(self.evenrowoffsets if y % 2 == 0 else self.oddrowoffsets)  
        neighbor_coords = np.array([x, y]) + offsets
        ys, xs = neighbor_coords[:, 1], neighbor_coords[:, 0]
        in_bounds = (xs >= 0) & (xs < self.x_max) & (ys >= 0) & (ys < self.y_max)
        tiles = self.state[ys[in_bounds], xs[in_bounds]]
        is_empty = (get_owner(tiles) == none) & (is_valid(tiles) != 0)
        ys, xs = ys[in_bounds & is_empty], xs[in_bounds & is_empty]
        return np.column_stack((xs, ys))

    def add_tile(self, x, y, owner, value): 
        self.turn += 1
        if get_owner(self.state[y][x]) != none: print("Critical Error! Tile already taken.")
        self.state[y, x] = set_owner(self.state[y, x], owner)
        self.state[y, x] = set_value(self.state[y, x], value)
        self.state[y, x] = set_valid(self.state[y, x], False)
        self.adj_mask[y][x] = False

    def update_neighbors(self, x, y, player, roll_value):
        """player is the Player instance who just placed roll_value at (x, y)."""
        neighbors = self.get_adjacent_tiles(x, y)
        xs, ys = neighbors[:,0], neighbors[:,1]
        owners = get_owner(self.state[ys, xs])
        values = get_value(self.state[ys, xs])
        self._update_adjacency(xs, ys, values)
        is_ally = (owners == player.name)
        is_weaker_enemy = (owners != player.name) & (owners != none) & (values < roll_value) & (values != 0)
        if np.any(is_weaker_enemy):
            self.state[ys[is_weaker_enemy], xs[is_weaker_enemy]] = set_owner(self.state[ys[is_weaker_enemy], xs[is_weaker_enemy]], player.name)
        if np.any(is_ally):
            inc = values[is_ally] + 1
            self.state[ys[is_ally], xs[is_ally]] = set_value(self.state[ys[is_ally], xs[is_ally]], inc)
        player.score += roll_value      

    def score_from_absorption(self, x, y, player, roll_value):
        score = 0
        neighbors = self.get_adjacent_tiles(x, y)
        owners = get_owner(self.state[neighbors[:,1], neighbors[:,0]])
        values = get_value(self.state[neighbors[:,1], neighbors[:,0]])
        is_ally = owners == player.name
        is_weaker_enemy = (owners != player.name) & (owners != none) & (values < roll_value) & (values != 0)
        if np.any(is_weaker_enemy):
            score += values[is_weaker_enemy].sum()
        if np.any(is_ally):
            score += (values[is_ally] + 1).sum()
        return score

    def _update_adjacency(self, xs, ys, values):
        is_taken = values != none
        is_untaken = values == none
        self.adj_mask[ys[is_taken], xs[is_taken]] = False
        self.adj_mask[ys[is_untaken], xs[is_untaken]] = True  

    def clone(self):
        new = GameState(
            turn=self.turn,
            x_max=self.x_max,
            y_max=self.y_max,
            roll_max=self.roll_max,
            hole_percentage=self.hole_percentage,
            evenrowoffsets=self.evenrowoffsets,
            oddrowoffsets=self.oddrowoffsets)
        new.state    = self.state.copy()
        new.adj_mask = self.adj_mask.copy()
        return new

    def is_terminal(self):  
        return not np.any(self.state & VALID_MASK)
    
    def return_winner(self, players):
        if not self.is_terminal():
            print("Warning, asking for a winner when the game isn't over. Proceeding anyway.")
        scores = [p.score for p in players]
        idx, _ = max(enumerate(scores), key=lambda x: x[1])
        return idx + 1

    def rollout(self, simnum: int, stochasticity: float, players: list["Player"]):
        winners = np.empty(simnum, dtype=np.uint8)
        for n in range(simnum):
            sim = self.clone()
            sim_players = [p.clone() for p in players]
            for p in sim_players:
                random.shuffle(p.NumBank)
            while not sim.is_terminal():
                current_player = sim_players[sim.turn % len(sim_players)]
                current_player.make_greedy_move(sim, greediness=2, stochasticity=stochasticity)
            winners[n] = sim.return_winner(sim_players)
        return winners

    def evaluate(self, simnum: int, stochasticity: float, players: list["Player"], target_player: "Player") -> float:
        winners = self.rollout(simnum, stochasticity, players)
        return np.count_nonzero(winners == target_player.name) / simnum


class Player:
    def __init__(self, name: int):
        """Create a new player with a 2‑bit colour mask in *name*."""
        self.name = name                       # 0b01, 0b10, 0b11 or 1, 2, 3
        self.score = 0
        self.NumBank = list(range(1, 21)) * 2  # two of each d20 roll
        self.FirstTime = True
        self.MoveNumber = 0
        self.SumOfRolls = 0
        self.id = 0

    # ------------------------------------------------------------
    #  cloning / utility
    # ------------------------------------------------------------
    def clone(self) -> "Player":
        return copy.deepcopy(self)

    def roll(self) -> int:
        """Pop the next number from NumBank (FIFO)."""
        if not self.NumBank:
            raise ValueError("NumBank exhausted")
        value = self.NumBank.pop(0)
        self.SumOfRolls += value
        self.MoveNumber += 1
        return value

    # ------------------------------------------------------------
    #  strategies (all share signature: (game, **kwargs))
    # ------------------------------------------------------------
    def make_random_move(self, game: GameState) -> None:
        """Place on any empty valid tile chosen uniformly at random."""
        yx = np.argwhere(is_valid(game.state))
        if len(yx) == 0:
            raise RuntimeError("No valid tiles left for random move")
        y, x = yx[np.random.randint(len(yx))]
        game.add_tile(x, y, self.name, self.roll())

    def make_random_adjacent_move(self, game: GameState) -> None:
        """Prefer a random adjacent spot; fall back to fully random if none."""
        yx = np.argwhere(game.adj_mask)
        if len(yx) == 0:
            self.make_random_move(game)
            return
        y, x = yx[np.random.randint(len(yx))]
        game.add_tile(x, y, self.name, self.roll())

    def make_greedy_move(self, game: GameState, *, greediness: int = 1, stochasticity: float = 0.1) -> None:
        """Choose among top‑*greediness* scoring moves; pick randomly with *stochasticity*."""
        yx = np.argwhere(game.adj_mask)
        if len(yx) == 0:
            self.make_random_move(game)
            return

        # explore with probability "stochasticity"
        if random.random() < stochasticity:
            y, x = yx[np.random.randint(len(yx))]
            game.add_tile(x, y, self.name, self.roll())
            return

        scores = []
        roll_value = self.roll()  # roll once per decision
        for y, x in yx:
            score = game.score_from_absorption(x, y, self, roll_value)
            scores.append(((y, x), score))
        top_moves = sorted(scores, key=lambda t: t[1], reverse=True)[:greediness]
        (y, x), _ = random.choice(top_moves)
        game.add_tile(x, y, self.name, roll_value)

    def make_human_move(self, game: GameState) -> None:
        """Prompt a human for an X,Y coordinate."""
        while True:
            game.display()
            prompt = f"Your number is {self.NumBank[0]}, colour {self.name}. Move X,Y: "
            move_input = input(prompt)
            m = re.match(r"(\d+),\s*(\d+)", move_input)
            if not m:
                print("Format must be X,Y (e.g., 3,5)")
                continue
            x, y = map(int, m.groups())
            if 0 <= x < game.x_max and 0 <= y < game.y_max and get_owner(game.state[y][x]) == none and is_valid(game.state[y][x]):
                break
            print("Invalid move; try again.")
        game.add_tile(x, y, self.name, self.roll())

    def make_flat_monte_carlo_move(self, game: GameState, players: list["Player"], *, sims: int = 100, stochasticity: float = 0.1) -> None:
        """Flat (one‑ply) Monte‑Carlo search: try every legal move, evaluate via rollouts, picks the best."""
        yx = np.argwhere(game.adj_mask)
        if len(yx) == 0:
            self.make_random_move(game)
            return

        best_winrate = -1.0
        best_move: tuple[int, int] | None = None
        for y, x in yx:
            sim_game = game.clone()
            sim_players = [p.clone() for p in players]
            sim_self = sim_players[players.index(self)]  # map to clone
            sim_game.add_tile(x, y, sim_self.name, sim_self.roll())
            wr = sim_game.evaluate(sims, stochasticity, sim_players, sim_self)
            if wr > best_winrate:
                best_winrate = wr
                best_move = (x, y)
        x_b, y_b = best_move
        game.add_tile(x_b, y_b, self.name, self.roll())

#endregion
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
