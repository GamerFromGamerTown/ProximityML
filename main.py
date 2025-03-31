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
    import math 
    import time
    # import mcts # maybe
    #sys.stdout = None  # Disable all printing if desired as a speed check

    # These control the player types:
    IsAdjacentUsed = True # The adjacency checks add a decent amount of overhead, but are critical for all bots, barring the RL-algorithm
    p1movetype = 2  # e.g., 1: random, 2: human, 3: RandomAdjacentTileBot, 4 is easy, 5 is medium, 6 is hard (greediest move)
    p2movetype = 6
    p3movetype = 6
    HoleRandomnessType = 1  # 0 for none, 1 for pure randomness, 2 for perlin (not yet implemented)
    PlayerCount = 2
    RandomHoleOccurancePercentage = int(10)
    global GlobalMoveNum

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
        grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
    elif HoleRandomnessType == 1:
        grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)
        hole_mask = np.random.rand(8, 10) < RandomHoleOccurancePercentage/100
        # Remove the valid bit from holes (bitwise AND with complement)
        grid[hole_mask] = grid[hole_mask] & 0b0111111111111111  
    else:
        print("Warning, HoleRandomnessType is poorly defined. Proceeding with no holes.")
        grid = np.full((8, 10), 0b1000000000000000, dtype=np.uint16)

    GlobalMoveNum = 0
    try: 
    holemasksum = hole_mask.sum()
    MoveMax = (xMax * yMax) - holemasksum
    except:
    MoveMax = xMax * yMax

    # endregion
    # region MainFunctions

    class Player:
        def __init__(self, name):
            self.name = name  # this holds the bit mask value for the player (red, green, or blue)
            self.score = int(0)
            self.NumBank = list(range(1, RollMax+1)) * 2
            self.FirstTime = True
            self.MoveType = int(0)
            self.MoveNumber = int(0)
            self.SumOfRolls = int(0)

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
        IsAdjacentToSomethingCheck(x, y)
        grid[y][x] = set_adjacent(grid[y][x], False)
        adj_mask[y][x] = False   
        if (x, y) in adjacent_tiles:
            adjacent_tiles.remove((int(x),int(y)))
        
        if is_valid(grid[y][x]):
            grid[y][x] = set_valid(grid[y][x], False)
        else:
            print("Critical Error! Chose an invalid tile!!!!!")

        global GlobalMoveNum
        GlobalMoveNum += 1
        if GlobalMoveNum > MoveMax:
        print("GlobalMoveNumber is equal to or greater than MoveMax")
        EndGame()
        exit()
        offsets = np.array(EvenRowOffsets if y % 2 == 0 else OddRowOffsets)  
        
        neighbor_coords = np.array([x, y]) + offsets
        ys, xs = neighbor_coords[:, 1], neighbor_coords[:, 0]
        in_bounds = (xs >= 0) & (xs < xMax) & (ys >= 0) & (ys < yMax)
        ys, xs = ys[in_bounds], xs[in_bounds]
        
        values = get_value(grid[ys, xs])
        x, y, num = int(x), int(y), int(num)
        
        if adj_mask[y][x]:
        adj_mask[y][x] = False;
        if (x, y) in adjacent_tiles:
            adjacent_tiles.remove((x, y))
        else:
            print("Warning! Tile in adj_mask, but not adjacent tiles.")
        
        owners = get_owner(grid[ys, xs])
        is_ally = (player.name == owners)
        is_enemy = ((player.name != owners) & (player.name != none))
        is_weaker_tile = (values < num) & (values != 0) 
        is_weaker_enemy = is_enemy & is_weaker_tile
        grid[y][x] = set_owner(grid[y][x], player.name)
        grid[y][x] = set_value(grid[y][x], num)
        player.score += num

        player.SumOfRolls += num
        if values[is_ally].size > 0: 
        values[is_ally] += 1
        player.score += np.count_nonzero(is_ally)
        tiles = grid[ys, xs].copy()
        tiles[is_ally] = set_value(tiles[is_ally], values[is_ally])
        grid[ys[is_ally], xs[is_ally]] = tiles[is_ally]

        if values[is_weaker_enemy].size > 0:
        player.score += int(np.sum(values[is_weaker_enemy]))
        tiles = grid[ys, xs].copy()
        tiles[is_weaker_enemy] = set_owner(tiles[is_weaker_enemy], player.name)
        grid[ys[is_weaker_enemy], xs[is_weaker_enemy]] = tiles[is_weaker_enemy]
        absorbed_owners = owners[is_weaker_enemy]
        absorbed_values = values[is_weaker_enemy]
        for p in [Player1, Player2, Player3]:
            player_mask = (absorbed_owners == p.name)
            if np.any(player_mask):
            penalty = int(np.sum(absorbed_values[player_mask]).item())
            p.score -= penalty

    def GreedyBot(player, greediness):
        scores = OrderedSet()
        try:
        greediness = int(greediness)
        except ValueError:
        print("Warning, GreedyBot played a random move! Greediness not defined properly.")
        RandomMove(player, player.NumBank[0])
        return
        if greediness > len(adjacent_tiles):
        greediness = len(adjacent_tiles)
        if len(adjacent_tiles) != 0:
            for x, y in adjacent_tiles:
                PossibleScore = ScoreFromAbsorption(player, x, y)
                scores.append(((x, y), PossibleScore))
            top_moves = sorted(scores, key=lambda item: item[1], reverse=True)[:greediness]
            best_move = random.choice(top_moves)
            (x, y), _ = best_move
            ApplyMechanics(player, x, y, player.NumBank[0])
        else:
            print("Warning, GreedyBot played a random move!")
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
            display_grid()

    def RandomMove(player, num):
        yx = np.argwhere(is_valid(grid)) 
        if len(yx) != 0:
            y, x = yx[np.random.randint(len(yx))]
            ApplyMechanics(player, x, y, num)
            return x, y
        

    def RandomAdjacentTileBot(player, num):
        if adjacent_tiles:
            print("Adjacent tile move made (move number", player.MoveNumber, ")")
            x, y = adjacent_tiles.pop()
            ApplyMechanics(player, x, y, num)
            return True, x, y
        else:
            return RandomMove(player, num)

    def display_grid():
    owners = (grid & 0b0110000000000000) >> 13
    values = (grid & 0b0001111100000000) >> 8
    valids = (grid & 0b1000000000000000) > 0

    print("The scores are as follows:",
        str(Player1.name).capitalize() + ":", Player1.score,
        str(Player2.name).capitalize() + ":", Player2.score,
        str(Player3.name).capitalize() + ":", Player3.score)

    print("The current sum of rolls is",
        str(Player1.name).capitalize() + ":", Player1.SumOfRolls,
        str(Player2.name).capitalize() + ":", Player2.SumOfRolls,
        str(Player3.name).capitalize() + ":", Player3.SumOfRolls)

    print("   0   1   2   3   4   5   6   7   8   9")

    for y in range(yMax):
        row_str = ""
        for x in range(xMax):
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


    def HumanMoveInput(player):
    while True:
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
        if GlobalMoveNum >= MoveMax:
            print("MoveNum > MoveMax! Critical Error!")
        if not (0 <= x < xMax and 0 <= y < yMax):
            print("Out of bounds! Critical Error!")
        if get_owner(grid[y][x]) != none:
            print("Tile already occupied! Critical Error!")
        ApplyMechanics(player, x, y, num)

    def IsAdjacentToSomethingCheck(x, y):
        offsets = EvenRowOffsets if y % 2 == 0 else OddRowOffsets
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if not (xMin <= nx < xMax and yMin <= ny < yMax):
                continue
            if get_owner(grid[ny][nx]) == none and is_valid(grid[ny][nx]):
                if (nx, ny) not in adjacent_tiles:
                    adjacent_tiles.add((nx, ny))
                    adj_mask[y][x] = True

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
            RandomMove(player, player.NumBank[0])
        elif player.MoveType == 2:
            x, y = HumanMoveInput(player)
            move(player, player.NumBank[0], x, y)
        elif player.MoveType == 3:
            MoveMade = RandomAdjacentTileBot(player, player.NumBank[0])
        elif player.MoveType == 4:
            GreedyBot(player, 5)
        elif player.MoveType == 5:
            GreedyBot(player, 3)
        elif player.MoveType == 6:
            GreedyBot(player, 1)
        else:
            print("Hey, movetype is poorly defined. Warning!")
        del player.NumBank[0]

    def ValidTilesCheck():
        if GlobalMoveNum >= MoveMax:
            display_grid()
            return True
        return False

    # def ResetStates():
    #     player
    # endregion

    # region MainLoop
    while True:
        if GlobalMoveNum >= MoveMax:
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
    save every 10th game or so
    optimise to hell before AI training! try to make state values binary 


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
