from __future__ import annotations

# region Initialize
import numpy as np 
import random
import time
import copy
import re  # regex

PlayerCount= 2
P1MoveType = 1
P2MoveType = 7
P3MoveType = 1


# 0: None,
# 1: Player.make_human_move,
# 2: Player.make_random_move,
# 3: Player.make_random_adjacent_move,
# 4: Player.make_hard_move,
# 5: Player.make_medium_move,
# 6: Player.make_easy_move,
# 7: Player.make_flat_monte_carlo_move

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
# Define player "colors” using bit masks
none, red, blue, green = 0b00, 0b01, 0b10, 0b11

owner_symbols = {
    0: "·",  # represents no owner
    1: "R",  # red
    2: "B",  # green
    3: "G"   # blue
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

def set_value(tile, tile_value):
    cleared = tile & (~VALUE_MASK & 0xFFFF)
    return np.uint16(cleared | (tile_value << 8))

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
        turn_max = self.x_max * self.y_max

        self.state = self.initialize_state()
        
        self.adj_mask = np.zeros((y_max, x_max), dtype=bool)

    
    def initialize_state(self): # This initialises a 10x8 grid, with each tile having a 16-bit value.
        grid = np.full((self.y_max, self.x_max), VALID_MASK, dtype=np.uint16)
        if self.hole_percentage != 0:
            hole_mask = np.random.rand(self.y_max, self.x_max) < (self.hole_percentage / 100)
            grid[hole_mask] &= (~VALID_MASK & 0xFFFF) # This gets rid of the valid bits on the holes.
        
        xMask = np.arange(0, self.y_max*self.x_max) % self.x_max 
        yMask = np.arange(0, self.y_max*self.x_max) // self.x_max # Makes a mask of the X and y values,
        xMask = xMask.reshape(self.y_max, self.x_max) # makes it shaped like the grid, 
        yMask = yMask.reshape(self.y_max, self.x_max)
        
        grid = grid | yMask # and applies it to the grid.
        grid = grid | xMask << 3 
        return grid
    
    def display_grid(self):
        spacing = "  "
        indent  = "  "
        for y, row in enumerate(self.state):
            tiles = ""
            tiles += str(y)
            if y % 2 == 1: tiles+=indent
            for x, cell in enumerate(row):
                owner_code = get_owner(cell)
                symbol = str(owner_symbols[owner_code])
                tile_value = get_value(cell)
                
                if 0 < tile_value < 10: tile_value = str(0) + str(tile_value)
                elif tile_value == 0: tile_value = ""
                symbol = symbol + str(tile_value)
                if owner_code == 0: symbol = str(spacing)+symbol+str(spacing)
                else: symbol = str(" ")+symbol+str(" ")
                if not is_valid(cell) and get_value(cell) == 0: symbol = "  X  "
                tiles += symbol
            print(tiles)

        bottom_x_list = ""
        if self.y_max % 2 == 0: 
            bottom_x_list += " "
        for n in range(self.x_max):
            bottom_x_list +=  "    " + str(n)
        
        print(bottom_x_list)
    
    def get_adjacent_tiles(self, x, y): # This function returns the tiles surrounding a given tile from a x, y pair. 
        offsets = np.array(self.evenrowoffsets if y % 2 == 0 else self.oddrowoffsets)  
        neighbor_coords = np.array([x, y]) + offsets
        ys, xs = neighbor_coords[:, 1], neighbor_coords[:, 0]
        in_bounds = (xs >= 0) & (xs < self.x_max) & (ys >= 0) & (ys < self.y_max)
        tiles = self.state[ys[in_bounds], xs[in_bounds]]
        # is_not_empty = (get_owner(tiles) != none) & (is_valid(tiles) != 0)
        ys, xs = ys[in_bounds], xs[in_bounds]
        # ys, xs = ys[is_not_empty], xs[is_not_empty]
        return np.column_stack((xs, ys))

    def add_tile(self, x, y, player, tile_value): # This adds a tile to the grid, and calls the update_neighors function to absorb/reinforce surrounding tiles.
        self.turn += 1
        if get_owner(self.state[y][x]) != none: print("Critical Error! Tile already taken.")
        self.state[y, x] = set_owner(self.state[y, x], player.name)
        self.state[y, x] = set_value(self.state[y, x], tile_value)
        self.state[y, x] = set_valid(self.state[y, x], False)
        self.adj_mask[y][x] = False
        self.update_neighbors(x, y, player, tile_value)

    def update_neighbors(self, x, y, player, tile_value): # This, after one places a tile, adds 1 to all surrounding allies, and changes weaker enemy's owner's to the placer's.  
        """player is the Player instance who just placed tile_value at (x, y)."""
        neighbors = self.get_adjacent_tiles(x, y)
        xs, ys = neighbors[:,0], neighbors[:,1]
        owners = get_owner(self.state[ys, xs])
        values = get_value(self.state[ys, xs])
        self._update_adjacency(xs, ys, values)
        # print(str(player.name)+"!!!!")
        is_ally = (owners == player.name)
        is_weaker_enemy = (owners != player.name) & (owners != none) & (values < tile_value) & (values != 0)
        if np.any(is_weaker_enemy):
            self.state[ys[is_weaker_enemy], xs[is_weaker_enemy]] = set_owner(self.state[ys[is_weaker_enemy], xs[is_weaker_enemy]], player.name)
        if np.any(is_ally):
            inc = values[is_ally] + 1
            self.state[ys[is_ally], xs[is_ally]] = set_value(self.state[ys[is_ally], xs[is_ally]], inc)
        player.score += tile_value      

    def score_from_absorption(self, x, y, player, tile_value): # This returns how many points you'd get from absorbing a tile.
        score = 0
        neighbors = self.get_adjacent_tiles(x, y)
        owners = get_owner(self.state[neighbors[:,1], neighbors[:,0]])
        values = get_value(self.state[neighbors[:,1], neighbors[:,0]])
        is_ally = owners == player.name
        is_weaker_enemy = (owners != player.name) & (owners != none) & (values < tile_value) & (values != 0)
        if np.any(is_weaker_enemy):
            score += values[is_weaker_enemy].sum()
        if np.any(is_ally):
            score += (values[is_ally] + 1).sum()
        return score

    def _update_adjacency(self, xs, ys, values): # This updates the mask that shows which available places to place a tile that are adjacent to a tile. 
        # This makes it faster for bots, since instead of scan== 0ning every tile on the grid to get the greediest move, they only consider tiles that could actually boost their score.
        is_taken = values != none
        is_untaken = values == none
        self.adj_mask[ys[is_taken], xs[is_taken]] = False
        self.adj_mask[ys[is_untaken], xs[is_untaken]] = True  

    def clone(self): # This function just copies the whole grid, useful for simulation purposes.
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

    def is_terminal(self): # This sees if there are any valid moves remaining.
        # if self.turn > int(self.turn_max): print("Warning: Turn is over the expected maximum of", turn_max)
        return not np.any(self.state & VALID_MASK)
    
    def return_winner(self, players): # This returns a wunner.
        if not self.is_terminal():
            print("Warning, asking for a winner when the game isn't over. Proceeding anyway.")
        scores = [p.score for p in players]
        idx, _ = max(enumerate(scores), key=lambda x: x[1])
        return idx + 1

    def rollout(self, simnum: int, stochasticity: float, players: list["Player"]): # This plays many simulated games with the greedy bot, and returns a list of who wins.
        winners = np.empty(simnum, dtype=np.uint8)
        for n in range(simnum):
            sim = self.clone()
            sim_players = [p.clone() for p in players]
            for p in sim_players:
                random.shuffle(p.NumBank)
            while not sim.is_terminal():
                current_player = sim_players[sim.turn % len(sim_players)]
                current_player.make_greedy_move(game=sim, greediness=2, stochasticity=stochasticity)
            winners[n] = sim.return_winner(sim_players)
        return winners

    def evaluate(self, simnum: int, stochasticity: float, players: list["Player"], target_player: "Player") -> float: # This gives a ratio of how "good" a move is by the win/loss ratio.
        winners = self.rollout(simnum, stochasticity, players)
        return np.count_nonzero(winners == target_player.name) / simnum

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

    # ------------------------------------------------------------
    #  strategies (all share signature: (game, **kwargs))
    # ------------------------------------------------------------
    def make_random_move(self, game: GameState) -> None: 
        """Place on any empty valid tile chosen uniformly at random."""
        yx = np.argwhere(is_valid(game.state))
        if len(yx) == 0:
            raise RuntimeError("No valid tiles left for random move")
        y, x = yx[np.random.randint(len(yx))]
        game.add_tile(x, y, self, self.roll())

    def make_random_adjacent_move(self, game: GameState) -> None: 
        """Prefer a random adjacent spot; fall back to fully random if none."""
        if len(yx) != 0: yx = np.argwhere(game.adj_mask)
        if len(yx) == 0:
            self.make_random_move(game)
            return
        y, x = yx[np.random.randint(len(yx))]
        game.add_tile(x, y, self, self.roll())

    def make_greedy_move(self, greediness, game: GameState, *, stochasticity: float = 0.1) -> None:
        """Choose among top‑*greediness* scoring moves; pick randomly with *stochasticity*."""
        yx = np.argwhere(game.adj_mask)
        if len(yx) == 0:
            self.make_random_move(game)
            return

        # explore with probability "stochasticity"
        if random.random() < stochasticity:
            y, x = yx[np.random.randint(len(yx))]
            game.add_tile(x, y, self, self.roll())
            return

        scores = []
        tile_value = self.roll()  # roll once per decision
        for y, x in yx:
            score = game.score_from_absorption(x, y, self, tile_value)
            scores.append(((y, x), score))
        top_moves = sorted(scores, key=lambda t: t[1], reverse=True)[:greediness]
        (y, x), _ = random.choice(top_moves)
        game.add_tile(x, y, self, tile_value)

    def make_easy_move(self): # This is a wrapper for make_greedy_move, with a greediness of 5.
        make_greedy_move(self, greediness=5)

    def make_medium_move(self): # This is a wrapper for make_greedy_move, with a greediness of 3.
        make_greedy_move(self, greediness=3)

    def make_hard_move(self): # This is a wrapper for make_greedy_move, with a greediness of 1.
        make_greedy_move(self, greediness=1)


    def make_human_move(self, game: GameState) -> None:
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
            if 0 <= x < game.x_max and 0 <= y < game.y_max and get_owner(game.state[y][x]) == none and is_valid(game.state[y][x]):
                break
            print("Invalid move; try again.")
        game.add_tile(x, y, self, self.roll())

    def make_flat_monte_carlo_move(self, game: GameState, players: list["Player"], *, sims: int = 100, stochasticity: float = 0.1) -> None:
        """Flat (one‑ply) Monte‑Carlo search: try every legal move, evaluate via rollouts, picks the best."""
        if self.score == 0: yx = np.argwhere(game.state & VALID_MASK)
        else: yx = np.argwhere(game.adj_mask)
        if len(yx) == 0:
            self.make_random_move(game)
            return

        best_winrate = -1.0
        best_move: tuple[int, int] | None = None
        for y, x in yx:
            sim_game = game.clone()
            sim_players = [p.clone() for p in players]
            sim_self = sim_players[players.index(self)]  # map to clone
            sim_game.add_tile(x, y, sim_self, sim_self.roll())
            wr = sim_game.evaluate(sims, stochasticity, sim_players, sim_self)
            print(f"\rConsidering move {x}, {y} with goodness {wr}", end='', flush=True)
            if wr > best_winrate:
                best_winrate = wr
                best_move = (x, y)
        x_b, y_b = best_move
        game.add_tile(x_b, y_b, self, self.roll())


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
while not game.is_terminal():
    print("MoveNum:", tempcount)
    tempcount += 1
    current_player = players[game.turn % PlayerCount]
    try:
        current_player.choose_move(game, players=players)
    except TypeError:
        current_player.choose_move(game)


winner = game.return_winner(players)
print(str(winner).capitalize(), "wins!")
game.display_grid()

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
