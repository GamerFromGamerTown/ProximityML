from __future__ import annotations
TotalSimulations = 0
# region Initialize

PlayerCount= 2
P1MoveType = 4
P2MoveType = 4
P3MoveType = 1
CoresToMultiThread = 5

# 0: None,
# 1: Player.make_human_move,
# 2: Player.make_random_move,
# 3: Player.make_random_adjacent_move,
# 4: Player.make_hard_move,
# 5: Player.make_medium_move,
# 6: Player.make_easy_move,
# 7: Player.make_flat_monte_carlo_move

""" TODO
* MCS bot places tiles where it shouldn't. Including over opponent's tiles and in holes.
* Better localise TotalSimulations
* Further optimisation, maybe JIT compile hot loops, maybe w/ numba
* Make this more suitable for AI training, add better interfacing.
* Maybe restructure X and Y each to take 4 bits, rather than have X at 5 and Y at 3.
* Work on a GUI !
* Finish MinMax bot.
* Create an "extended" adjacency mask, which is the adjacents of adj_mask. Allows for baiting, but computing further moves is often a waste."""

# region Imports
import numpy as np 
import random
import time
import copy
import re  # regex
import math
import torch
import gymnasium as gym
from concurrent.futures import ProcessPoolExecutor
# endregion

# Define player "colors” using bit masks
none, red, blue, green = 0b00, 0b01, 0b10, 0b11

owner_symbols = {
    0: "·",  # represents no owner
    1: "R",  # red
    2: "B",  # green
    3: "G"   # blue
}

"""Here's how the bits are structured!
bit 15 (the first one), shows if you can place a tile on it.
bits 14-13 (the next two) show their owner
bits 12-8 (the next 5) contain their value
bits 7-3 (the next 5) contains a tile's x value (so the AI can understand the grid better)
bits 2-0 (the next 3) contain a tile's y value
nice and snug!"""
VALID_MASK = 0b1000000000000000
OWNER_MASK = 0b0110000000000000
VALUE_MASK = 0b0001111100000000
X_BITS = 0b0000000011111000
Y_BITS = 0b0000000000000111

# region BitMaskOperations
# 15: IsValid, 14-13: Owner, 13-8 = value, 7 IsAdjacent, 6-3 x, 2-0 y (nice and snug)
# ADD AN X, Y BIT !! very useful for AI

def set_owner(tile, owner):
    cleared = tile & (~OWNER_MASK & 0xFFFF)     # Zero out owner bits
    result = cleared | (owner << 13)
    return np.uint16(result)

def set_value(tile, tile_value):
    cleared = tile & (~VALUE_MASK & 0xFFFF)
    return np.uint16(cleared | (tile_value << 8))
# endregion
# region PrimaryCode


class GameState:
    # region InitGameState
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
        self.turn_max = self.x_max * self.y_max

        self.state = self.initialize_state()
        self.neighbor_map = self.precompute_neighbors()
        
        self.adj_mask = np.zeros((y_max, x_max), dtype=bool)
        

    
    def initialize_state(self): # This initialises a 10x8 grid, with each tile having a 16-bit value.
        grid = np.full((self.y_max, self.x_max), VALID_MASK, dtype=np.uint16) 

        if self.hole_percentage != 0:
            hole_mask = np.random.rand(self.y_max, self.x_max) < (self.hole_percentage / 100)
            grid[hole_mask] &= (~VALID_MASK & 0xFFFF)               # This gets rid of the valid bits on the holes.
        
        self.valid_count = int(np.count_nonzero(hole_mask))
        xMask = np.arange(0, self.y_max*self.x_max) % self.x_max 
        yMask = np.arange(0, self.y_max*self.x_max) // self.x_max   # Makes a mask of the X and y values,
        xMask = xMask.reshape(self.y_max, self.x_max)               # makes it shaped like the grid, 
        yMask = yMask.reshape(self.y_max, self.x_max)
        
        grid = grid | yMask                                         # and applies it to the grid.
        grid = grid | xMask << 4 # changed this recently from 3 to 4, if code is funky this might be it
        return grid
    #endregion

    def display_grid(self):
        spacing = "  "
        indent  = "  "
        for y, row in enumerate(self.state):
            tiles = ""
            tiles += str(y)
            if y % 2 == 1: tiles+=indent
            for x, cell in enumerate(row):
                owner_code = ((cell >> 13) & 0b11)                  # Gets owner
                symbol = str(owner_symbols[owner_code])
                tile_value = ((cell >> 8) & 0b1_1111)               # Gets value
                
                if 0 < tile_value < 10: tile_value = str(0) + str(tile_value)
                elif tile_value == 0: tile_value = ""
                symbol = symbol + str(tile_value)
                if owner_code == 0: symbol = str(spacing)+symbol+str(spacing)
                else: symbol = str(" ")+symbol+str(" ")
                if not ((cell & VALID_MASK) != 0) and ((cell >> 8) & 0b1_1111) == 0: symbol = "  X  "  # Is valid + Gets value
                tiles += symbol
            print(tiles)

        bottom_x_list = ""
        if self.y_max % 2 == 0: 
            bottom_x_list += " "
        for n in range(self.x_max):
            bottom_x_list +=  "    " + str(n)
        
        print(bottom_x_list)
    
    def get_adjacent_tiles(self, x, y):         # This function returns the tiles surrounding a given tile from a x, y pair. 
        return self.neighbor_map[(x, y)]
    
    def precompute_neighbors(self):
        NeighborsMap = {}
        for y, row in enumerate(self.state):
            for x, tile in enumerate(row):
                offsets = np.array(self.evenrowoffsets if y % 2 == 0 else self.oddrowoffsets)  
                neighbor_coords = np.array([x, y]) + offsets
                ys, xs = neighbor_coords[:, 1], neighbor_coords[:, 0]
                in_bounds = (xs >= 0) & (xs < self.x_max) & (ys >= 0) & (ys < self.y_max)
                tiles = self.state[ys[in_bounds], xs[in_bounds]]
                ys, xs = ys[in_bounds], xs[in_bounds]
                NeighborsMap[(x, y)] = np.column_stack((xs, ys))
        return NeighborsMap
                

    def add_tile(self, x, y, player, tile_value, players): # This adds a tile to the grid, and calls the update_neighors function to absorb/reinforce surrounding tiles.
        self.turn += 1
        if ((self.state[y][x] >> 13) & 0b11) != none: print("Critical Error! Tile already taken.")  # Gets owner.
        root = self.state[y, x]
        self.state[y, x] = (
            (root & (~(OWNER_MASK | VALUE_MASK | VALID_MASK) & 0xFFFF)) # clear out old owner, value, and valid bits, leaving only x/y bits
            | (player.name  << 13)                                      # insert new owner into bits 14–13
            | (tile_value   <<  8)                                      # insert new tile value into bits 12–8
        )
        self.adj_mask[y][x] = False
        self.update_neighbors(x, y, player, tile_value, players)


    def update_neighbors(self, x, y, player, tile_value, players): # This, after one places a tile, adds 1 to all surrounding allies, and changes weaker enemy's owner's to the placer's.  
        """player is the Player instance who just placed tile_value at (x, y)."""
        neighbors = self.get_adjacent_tiles(x, y)
        xs, ys = neighbors[:,0], neighbors[:,1]
        owners = ((self.state[ys, xs] >> 13) & 0b11)            # Gets owners.
        values = ((self.state[ys, xs] >> 8) & 0b1_1111)         # Gets values.
        self._update_adjacency(xs, ys, values)
        is_ally = (owners == player.name)
        is_weaker_enemy = (owners != player.name) & (owners != none) & (values < tile_value) & (values != 0)
        if np.any(is_weaker_enemy):
            weaker_owners = owners[is_weaker_enemy]
            weaker_values = values[is_weaker_enemy]
            
            self.state[ys[is_weaker_enemy], xs[is_weaker_enemy]] = set_owner(self.state[ys[is_weaker_enemy], xs[is_weaker_enemy]], player.name)
            player.score += int(values[is_weaker_enemy].sum()) 
            stolen_per_owner = np.bincount(weaker_owners, weights=weaker_values, minlength=4)
            for p in players:
                if stolen_per_owner[p.name] > 0:
                    p.score -= int(stolen_per_owner[p.name])

            
        if np.any(is_ally):
            inc = values[is_ally] + 1
            self.state[ys[is_ally], xs[is_ally]] = set_value(self.state[ys[is_ally], xs[is_ally]], inc)
            player.score += int(len(is_ally))
        player.score += tile_value      

    def score_absorption(self, x, y, player, tile_value): # Returns points gained from placing tile_value at (x, y)
        xs, ys = self.neighbor_map[(x, y)].T # ≤ 6 coords already pre‑computed
        state  = self.state[ys, xs]          # grab neighbour tiles in one slice

        owners = (state >> 13) & 0b11        # get owners
        values = (state >>  8) & 0b1_1111    # get values

        is_ally         = owners == player.name
        is_weaker_enemy = (owners != player.name) & (owners != none) & (values < tile_value) & (values != 0)

        return (values[is_weaker_enemy].sum()   # absorbed enemy points
              +  values[is_ally].sum()          # ally tile values before +1
              +  is_ally.sum())                 # +1 per reinforced ally


    def _update_adjacency(self, xs, ys, values): # This updates the mask that shows which available places to place a tile that are adjacent to a tile. 
        # This makes it faster for bots, since instead of scan== 0ning every tile on the grid to get the greediest move, they only consider tiles that could actually boost their score.
        is_taken   = values != none
        is_untaken = values == none
        self.adj_mask[ys[is_taken], xs[is_taken]] = False
        self.adj_mask[ys[is_untaken], xs[is_untaken]] = True  

    def clone(self):
        # Faster clone ! Sped it up by around 20 per cent.
        # Clones specific parts rather than doing a deep copy and full initialisation every time.
        new = object.__new__(GameState)
        new.turn          = self.turn
        new.x_max         = self.x_max
        new.y_max         = self.y_max
        new.roll_max      = self.roll_max
        new.hole_percentage = self.hole_percentage
        new.evenrowoffsets = self.evenrowoffsets
        new.oddrowoffsets  = self.oddrowoffsets

        # reuse the same neighbor_map 
        new.neighbor_map = self.neighbor_map

        # shallow‑copy only the mutable state
        new.state    = self.state.copy()
        new.adj_mask = self.adj_mask.copy()
        return new

    def is_terminal(self): # This sees if there are any valid moves remaining.
        return not np.any(self.state & VALID_MASK)
    
    def return_winner(self, players): # This returns a wunner.
        if not self.is_terminal():
            print("Warning, asking for a winner when the game isn't over. Proceeding anyway.")
        scores = [p.score for p in players]
        idx, _ = max(enumerate(scores), key=lambda x: x[1])
        return idx + 1


    def _run_single_rollout(self, stochasticity: 0.1, players: list["Player"]):
        global TotalSimulations
        # winner = np.empty(1, dtype=np.uint8)
        winner = 0b00000000
        sim = self.clone()
        sim_players = [p.clone() for p in players]
        for p in sim_players:
            random.shuffle(p.NumBank)
        while not sim.is_terminal():
            current_player = sim_players[sim.turn % len(sim_players)]
            current_player.make_greedy_move(game=sim, greediness=2, stochasticity=stochasticity)
        winner = sim.return_winner(sim_players)
        return winner

    def rollout(self, simnum: int, stochasticity: 0.1, players: list["Player"]): # This plays many simulated games with the greedy bot, and returns a list of who wins.
        
        global TotalSimulations
        winners = np.empty(simnum, dtype=np.uint8)
        
        for n in range(simnum):
            winners[n] = self._run_single_rollout(stochasticity, players)
            TotalSimulations += 1
        return winners

    def evaluate(self, simnum: int, stochasticity: float, players: list["Player"], target_player: "Player") -> float: # This gives a ratio of how "good" a move is by the win/loss ratio.
        winners = self.rollout(simnum, stochasticity, players)
        return np.count_nonzero(winners == target_player.name) / simnum

    def get_legal_moves(self):
        np.argwhere(((game.state & VALID_MASK) != 0))

    def reset_state(self, players: list["Player"]):
        self.__init__()
        Player.__init__()


class Player:
    def __init__(self, name: int):
        """Create a new player with a 2‑bit color mask in *name*."""
        self.name = name                       # 0b01, 0b10, 0b11 or 1, 2, 3
        self.score = 0
        self.NumBank = list(range(1, 21)) * 2  # two of each d20 roll
        random.shuffle(self.NumBank)
        self.FirstTime = True
        self.MoveNumber = 0
        self.SumOfRolls = 0
        self.id = 0

    # ------------------------------------------------------------
    #  cloning / utility
    # ------------------------------------------------------------
    def clone(self) -> "Player": # This gets a copy of the player.
        return copy.deepcopy(self)

    def roll(self) -> int: 
        """Pop the next number from NumBank (FIFO)."""
        if not self.NumBank:
            raise ValueError("NumBank exhausted")
        tile_value = self.NumBank.pop(0)
        self.SumOfRolls += tile_value
        self.MoveNumber += 1
        return tile_value

    def compute_final_reward(self, game: GameState) -> None:
        win = False
        scores = [p.score for p in players]
        winners = game.return_winner(players)
        if self.state == winners: win = True
        ScoreRatio = self.score
        temp = 0
        for p in players:
            if p.name == self.name: continue
            temp += p.score
        if temp == 0: 
            print("Warning! Other players' scores equal 0. Proceeding as if they equal one.")
            temp = 1
        ScoreRatio = ScoreRatio / (temp / PlayerCount)
        base = 1 / (1 + math.exp(-10 * ScoreRatio))
        # This is a mix between a sigmoid function and a win/loss reward system. 
        return base + 0.7 if win else base # This encourages winnnp.argwhereing, but also rewards higher wins more than close ones, and close wins more than far ones.
        # https://en.wikipedia.org/wiki/Sigmoid_function


    # ------------------------------------------------------------
    #  strategies (all share signature: (game, **kwargs))
    # ------------------------------------------------------------
    def make_random_move(self, game: GameState, **kwargs) -> None: 
        """Place on any empty valid tile chosen uniformly at random."""
        yx = np.argwhere(((game.state & VALID_MASK) != 0)) # Gets a list of valid tiles.
        print(np.argwhere(((game.state & VALID_MASK) != 0)))
        if len(yx) == 0:
            raise RuntimeError("No valid tiles left for random move")
        y, x = yx[np.random.randint(len(yx))]
        game.add_tile(x, y, self, self.roll(), players)

    def make_random_adjacent_move(self, game: GameState, **kwargs) -> None: 
        """Prefer a random adjacent spot; fall back to fully random if none.""" 
        valid_mask = (game.state & VALID_MASK) != 0
        yx = np.argwhere(game.adj_mask & valid_mask)
        if len(yx) == 0:
            self.make_random_move(game, **kwargs)
            return
        y, x = yx[np.random.randint(len(yx))]
        game.add_tile(x, y, self, self.roll(), players)

    def make_greedy_move(self, greediness, game: GameState, *, stochasticity: float = 0.1, **kwargs) -> None:
        """Choose among top‑*greediness* scoring moves; pick randomly with *stochasticity*."""
        valid_mask = (game.state & VALID_MASK) != 0
        yx = np.argwhere(game.adj_mask & valid_mask)
        if len(yx) == 0:
            self.make_random_move(game, **kwargs)
            return

        # explore with probability "stochasticity"
        if random.random() < stochasticity:
            y, x = yx[np.random.randint(len(yx))]
            game.add_tile(x, y, self, self.roll(), players)
            return

        scores = []
        tile_value = self.roll()  # roll once per decision
        for y, x in yx:
            score = game.score_absorption(x, y, self, tile_value)
            scores.append(((y, x), score))
        top_moves = sorted(scores, key=lambda t: t[1], reverse=True)[:greediness]
        (y, x), _ = random.choice(top_moves)
        game.add_tile(x, y, self, tile_value, players)

    def make_easy_move(self, game, **kwargs): # This is a wrapper for make_greedy_move, with a greediness of 5.
        return self.make_greedy_move(greediness=5, game=game, **kwargs)

    def make_medium_move(self, game, **kwargs): # This is a wrapper for make_greedy_move, with a greediness of 3.
        return self.make_greedy_move(greediness=3, game=game, **kwargs)

    def make_hard_move(self, game, **kwargs):
        return self.make_greedy_move(greediness=1, game=game, **kwargs)

    def make_human_move(self, game: GameState, **kwargs) -> None:
        """Prompt a human for an X,Y coordinate."""
        game.display_grid()
        while True:
            prompt = f"Your number is {self.NumBank[0]}, color {self.name}. Move X,Y: "
            move_input = input(prompt)
            m = re.match(r"(\d+),\s*(\d+)", move_input)
            if not m:
                print("Format must be X,Y (e.g., 3,5)")
                continue
            x, y = map(int, m.groups())
            if 0 <= x < game.x_max and 0 <= y < game.y_max and ((game.state[y][x] >> 13) & 0b11) == none and ((game.state[y][x] & VALID_MASK) != 0):  # Gets owner / Is valid
                break
            print("Invalid move; try again.")
        game.add_tile(x, y, self, self.roll(), players)

    def make_flat_monte_carlo_move(self, game: GameState, players: list["Player"], *, sims: int = 100, stochasticity: float = 0.1, **kwargs) -> None:
        """Flat (one‑ply) Monte‑Carlo search: try every legal move, evaluate via rollouts, picks the best."""
        L = 600  # upper limit
        k = 6    # growth rate (adjust)
        x0 = 39.5  # midpoint
        sims = int(round(100 + (L - 100) / (1 + math.exp(-k * (game.turn - x0) / 79))))

        # ^ This means each turn has about 3000 simulations total, but it spreads more thinly early-game.
        valid_mask = (game.state & VALID_MASK) != 0
        yx = np.argwhere(valid_mask)
        if len(yx) == 0:
            self.make_greedy_move(game, **kwargs)
            return

        best_winrate = -1.0
        best_move: tuple[int, int] | None = None
        for y, x in yx:
            sim_game = game.clone()
            sim_players = [p.clone() for p in players]
            sim_self = sim_players[players.index(self)]  # map to clone
            sim_game.add_tile(x, y, sim_self, sim_self.roll(), players)
            wr = sim_game.evaluate(sims, stochasticity, sim_players, sim_self)
            global TotalSimulations
            elapsed = time.perf_counter() - start
            print(f"\rConsidering move ({x}, {y}). Its winrate is {round(wr, 3)} with {round(TotalSimulations/elapsed, 3)} simulations per second ({TotalSimulations} total)", end='', flush=True)
            if wr > best_winrate:
                best_winrate = wr
                best_move = (x, y)
                print(f"\nBest Move is currently ({best_move}). Its winrate is {round(best_winrate, 3)})", end='', flush=True)
        x_b, y_b = best_move
        print(f"Chose ({x_b}, {y_b})")
        game.add_tile(x_b, y_b, self, self.roll(), players)

    def make_minmax_move(self, game: GameState, players: list["Player"], *, sims: int = 100, stochasticity: float = 0.1, **kwargs):
        pass



move_type_map = {
    0: None,
    1: Player.make_human_move,
    2: Player.make_random_move,
    3: Player.make_random_adjacent_move,
    4: Player.make_hard_move,
    5: Player.make_medium_move,
    6: Player.make_easy_move,
    7: Player.make_flat_monte_carlo_move
}
# region PrerequistiteCode
start = time.perf_counter()

game    = GameState()
raw_players = [Player(red), Player(blue)]
types       = [P1MoveType, P2MoveType]
if PlayerCount == 3:
    raw_players.append(Player(green))
    types.append(P3MoveType)

players = []
count = -1
for p, movetype in zip(raw_players, types):
    count += 1
    print(raw_players[count], count)
    strat = move_type_map[movetype]
    # bind the method to this instance
    p.choose_move = strat.__get__(p, raw_players[count])
    players.append(p)

tempcount = 0
#endregion
#region MainLoop
while not game.is_terminal():
    tempcount += 1
    current_player = players[game.turn % PlayerCount]
    try:
        current_player.choose_move(game, players=players)
    except TypeError:
        current_player.choose_move(game)

winner = game.return_winner(players)
print(str(winner).capitalize(), "wins! Scores are", [p.score for p in players])
game.display_grid()
#endregion

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
12) implement MCS bots to encourage deeper thinking [✓] # try greedy rollouts and random rollouts
13) get a reinforcement learning agent to learn this game, with the help of forward-thinking bots at later stages [X]
(MCS is too compute-heavy to work well, at least currently. A greedy minmax, self-training, or something in-between could help.)
14) graphical implementation [-]
15) elo system? [X]
"""
