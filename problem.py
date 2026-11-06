from __future__ import annotations

import argparse
import heapq
import queue
import random
import threading
import time
from collections import deque
from typing import Iterable, List, Optional, Sequence, Tuple

State = Tuple[Tuple[int, ...], ...]
Action = Tuple[int, int, str]
# (next_state, action, cost)
Successor = Tuple[State, Action, int]

# A "world" is a grid plus the set of bottom gates that are currently held open
# (i.e. joined cells).  Join (r, c) connects cell (r, c) with the cell below it.
# Plain State values are accepted anywhere a world is expected and mean "no
# joins" - the helpers below normalize both forms.
World = Tuple[State, frozenset]
Join = Tuple[int, int]
EMPTY_JOINS: frozenset = frozenset()

HALF = 1  # half-full, stored in half-units (0.5 sand)
FULL = 2  # full of sand (1.0 sand)

EMPTY_COST_VALUE = 0.0
ALGORITHMS = ("DFS", "BFS", "IDS", "UCS", "Greedy", "A* (sand)", "A* (column)")


def to_half_units(values: Sequence[Sequence[float]]) -> State:
    """Convert values like 0, 0.5, 1.0 into half-unit integers: 0, 1, 2."""
    rows = []
    for row in values:
        rows.append(tuple(int(round(value * 2)) for value in row))
    return tuple(rows)


def from_half_units(state: State) -> List[List[float]]:
    return [[cell / 2 for cell in row] for row in state]


def unpack(world) -> Tuple[State, frozenset]:
    """Split a state-or-world into (grid, open joins)."""
    if len(world) == 2 and isinstance(world[1], frozenset):
        return world[0], world[1]
    return world, EMPTY_JOINS


def pack(grid: Sequence[Sequence[int]], joins: frozenset) -> World:
    return (tuple(tuple(row) for row in grid), joins)


def join_is_valid(grid: State, row: int, col: int) -> bool:
    """A joined pair stays joined only while the rule holds:

    both cells contain sand, the lower cell is full, and the upper cell is
    full or half-full (case 1: full over half/full, case 2: half over full).
    """
    return grid[row][col] > 0 and grid[row + 1][col] == FULL


def prune_joins(grid: State, joins: frozenset) -> frozenset:
    """Drop every join that no longer satisfies the staying-open rule."""
    rows = len(grid)
    return frozenset(j for j in joins if j[0] + 1 < rows and join_is_valid(grid, j[0], j[1]))


def connected_body(joins: frozenset, seed: Join) -> set:
    """All cells connected to `seed` through open (joined) bottom gates."""
    body = {seed}
    frontier = [seed]
    while frontier:
        r, c = frontier.pop()
        for gate in ((r - 1, c), (r, c)):
            if gate in joins:
                for cell in (gate, (gate[0] + 1, gate[1])):
                    if cell not in body:
                        body.add(cell)
                        frontier.append(cell)
    return body


def print_grid(grid, label: str = "", joins: Optional[frozenset] = None) -> None:
    grid, embedded_joins = unpack(grid)
    if joins is None:
        joins = embedded_joins
    symbols = {
        0: ".",
        1: "H",
        2: "F",
    }
    if label:
        print(label)
    for r, row in enumerate(grid):
        print(" ".join(symbols.get(cell, "?") for cell in row))
        if r + 1 < len(grid):
            print(" ".join("=" if (r, c) in joins else " " for c in range(len(row))))
    if joins:
        print("(= marks joined cells: the gate between them is held open)")
    print()


def generate_random_state(rows: int, cols: int, *, rng: Optional[random.Random] = None) -> State:
    """Generate a random board with roughly half empty cells, some half-filled, and some full."""
    rng = rng or random.Random()
    board: List[List[int]] = []
    for _ in range(rows):
        row: List[int] = []
        for _ in range(cols):
            roll = rng.random()
            if roll < 0.5:
                value = 0
            elif roll < 0.75:
                value = 1
            else:
                value = 2
            row.append(value)
        board.append(row)
    return tuple(tuple(r) for r in board)


def load_state_from_digits(lines: Sequence[str]) -> State:
    """Parse a hand-written grid where 1 means sand-filled and 0 means empty.

    Each '1' becomes a FULL (1.0 sand) cell and each '0' an EMPTY cell.
    """
    board: List[List[int]] = []
    for line in lines:
        digits = [ch for ch in line if ch in "01"]
        if not digits:
            raise ValueError(f"Could not parse grid line: {line!r}")
        board.append([FULL if ch == "1" else 0 for ch in digits])
    width = len(board[0])
    if any(len(row) != width for row in board):
        raise ValueError("All grid lines must have the same length.")
    return tuple(tuple(r) for r in board)


def special_case_state() -> State:
    """The hand-made test case required by the problem statement:

        1 0
        0 1
        0 1
        1 0

    In the digits, 1 means the cell contains sand and 0 means empty.
    """
    return load_state_from_digits(["1 0", "0 1", "0 1", "1 0"])


def is_empty_state(state) -> bool:
    grid, _ = unpack(state)
    return all(cell == 0 for row in grid for cell in row)


def iter_actions(state) -> Iterable[Action]:
    grid, _ = unpack(state)
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] > 0:
                if r + 1 <= rows:
                    yield (r, c, "down")
                if c > 0 and grid[r][c] >= FULL:
                    yield (r, c, "left")
                if c + 1 < cols and grid[r][c] >= FULL:
                    yield (r, c, "right")


def apply_action(state, row: int, col: int, direction: str):
    """Apply one door-opening action and return the resulting world.

    Bottom gates obey the joining rule: when opening the gate between an upper
    cell and the cell below it, if after the transfer both cells still contain
    sand and the lower cell is full (case 1: full over half/full - half over
    full; case 2: half over full), the gate stays open and the sand in the two
    cells connects.  A connected body of sand drains together when the bottom
    gate of any of its cells is opened.
    """
    grid, joins = unpack(state)
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    next_grid = [list(r) for r in grid]

    current = next_grid[row][col]
    if current <= 0:
        return state

    if direction == "down":
        if row + 1 < rows:
            # The sand of the whole connected body pours through this gate.
            body = connected_body(joins, (row, col))
            body = {cell for cell in body if next_grid[cell[0]][cell[1]] > 0}
            body_total = sum(next_grid[r][c] for r, c in body)
            below = next_grid[row + 1][col]
            transfer = min(body_total, 2 - below)
            remaining = transfer
            # Sand drains from the opened cell and everything connected ABOVE
            # it, funnelling down through the opened gate (gravity).
            for body_row, body_col in sorted(body):
                if body_row > row:
                    continue
                if remaining <= 0:
                    break
                take = min(next_grid[body_row][body_col], remaining)
                next_grid[body_row][body_col] -= take
                remaining -= take
            next_grid[row + 1][col] += transfer
            new_joins = prune_joins(tuple(tuple(r) for r in next_grid), joins)
            # The gate itself stays open in case 1 / case 2.
            if next_grid[row][col] > 0 and next_grid[row + 1][col] == FULL:
                new_joins = new_joins | {(row, col)}
            return pack(next_grid, new_joins)
        # Bottom row: the whole connected body drains out of the grid.
        body = connected_body(joins, (row, col))
        for body_row, body_col in body:
            next_grid[body_row][body_col] = 0
        return pack(next_grid, prune_joins(tuple(tuple(r) for r in next_grid), joins))

    if direction == "left":
        if col <= 0:
            return state
        target = next_grid[row][col - 1]
        if current >= FULL and target < FULL:
            next_grid[row][col] -= 1
            next_grid[row][col - 1] += 1
        return pack(next_grid, prune_joins(tuple(tuple(r) for r in next_grid), joins))

    if direction == "right":
        if col + 1 >= cols:
            return state
        target = next_grid[row][col + 1]
        if current >= FULL and target < FULL:
            next_grid[row][col] -= 1
            next_grid[row][col + 1] += 1
        return pack(next_grid, prune_joins(tuple(tuple(r) for r in next_grid), joins))

    raise ValueError(f"Unknown direction: {direction!r}")


def gate_cost(before_value: int, after_value: int) -> int:
    """Cost of Action A (a bottom gate).

    cost = 1 + 4 * (s + s') where s and s' are the sand amounts of the upper
    cell before and after flushing, expressed as 0 (empty), 0.5 (half) or 1
    (full).  Half-units make this exact integer arithmetic.
    """
    return 1 + 2 * (before_value + after_value)


def side_cost() -> int:
    """Cost of Action B (a side door) - always 1."""
    return 1


def action_cost(state, action: Action) -> int:
    grid, _ = unpack(state)
    row, col, direction = action
    if direction == "down":
        return gate_cost(grid[row][col], apply_action(state, row, col, "down")[0][row][col])
    return side_cost()


def successors(state: State) -> List[Successor]:
    """All (next_state, action, cost) pairs reachable in one door opening."""
    result: List[Successor] = []
    for action in iter_actions(state):
        next_state = apply_action(state, *action)
        if unpack(next_state)[0] == unpack(state)[0] and unpack(next_state)[1] == unpack(state)[1]:
            continue
        result.append((next_state, action, action_cost(state, action)))
    return result


def reconstruct_path(
    parents: dict[State, Optional[Tuple[State, Action]]], goal: State
) -> List[Action]:
    path: List[Action] = []
    current = goal
    while True:
        entry = parents.get(current)
        if entry is None:
            break
        previous, action = entry
        path.append(action)
        current = previous
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# Search algorithms
# ---------------------------------------------------------------------------

NODE_LIMIT = 400_000


class SearchLimitExceeded(RuntimeError):
    pass


def solve_dfs(initial_state: State) -> List[Action]:
    """Depth-first search (graph search with a visited set, iterative)."""
    if is_empty_state(initial_state):
        return []
    stack: List[Tuple[State, List[Action]]] = [(initial_state, [])]
    visited = {initial_state}
    nodes = 0
    while stack:
        state, path = stack.pop()
        if is_empty_state(state):
            return path
        nodes += 1
        if nodes > NODE_LIMIT:
            raise SearchLimitExceeded("DFS exceeded the node limit.")
        for next_state, action, _cost in successors(state):
            if next_state in visited:
                continue
            visited.add(next_state)
            stack.append((next_state, path + [action]))
    raise ValueError("No emptying sequence was found for the given board.")


def solve_bfs(initial_state: State) -> List[Action]:
    """Breadth-first search - optimal in the number of door openings."""
    if is_empty_state(initial_state):
        return []

    frontier: deque[State] = deque([initial_state])
    parents: dict[State, Optional[Tuple[State, Action]]] = {initial_state: None}

    while frontier:
        state = frontier.popleft()
        if is_empty_state(state):
            return reconstruct_path(parents, state)
        for next_state, action, _cost in successors(state):
            if next_state in parents:
                continue
            parents[next_state] = (state, action)
            frontier.append(next_state)

    raise ValueError("No emptying sequence was found for the given board.")


def solve_ids(initial_state: State) -> List[Action]:
    """Iterative deepening depth-first search - optimal in action count."""

    def dls(state: State, depth: int, path: List[Action], on_path: set) -> Optional[List[Action]]:
        if is_empty_state(state):
            return path
        if depth == 0:
            return None
        for next_state, action, _cost in successors(state):
            if next_state in on_path:
                continue
            found = dls(next_state, depth - 1, path + [action], on_path | {next_state})
            if found is not None:
                return found
        return None

    if is_empty_state(initial_state):
        return []

    depth = 0
    while True:
        found = dls(initial_state, depth, [], {initial_state})
        if found is not None:
            return found
        depth += 1
        if depth > 40:
            raise SearchLimitExceeded("IDS exceeded its depth limit.")


def solve_ucs(initial_state: State) -> List[Action]:
    """Uniform-cost search - optimal under the weighted action costs."""
    if is_empty_state(initial_state):
        return []

    counter = 0
    frontier: List[Tuple[int, int, State]] = [(0, counter, initial_state)]
    best_cost: dict[State, int] = {initial_state: 0}
    parents: dict[State, Optional[Tuple[State, Action]]] = {initial_state: None}
    settled: set = set()

    while frontier:
        cost, _, state = heapq.heappop(frontier)
        if state in settled:
            continue
        settled.add(state)
        if is_empty_state(state):
            return reconstruct_path(parents, state)
        for next_state, action, step_cost in successors(state):
            new_cost = cost + step_cost
            if next_state in settled or new_cost >= best_cost.get(next_state, 10**9):
                continue
            best_cost[next_state] = new_cost
            parents[next_state] = (state, action)
            counter += 1
            heapq.heappush(frontier, (new_cost, counter, next_state))

    raise ValueError("No emptying sequence was found for the given board.")


# ---------------------------------------------------------------------------
# Heuristics for A*
#
# Both are admissible (never overestimate the true cost) and consistent, so
# A* with either one returns a cost-optimal plan just like UCS.
# ---------------------------------------------------------------------------


def total_sand(state) -> int:
    """Total sand in the grid, measured in half-units."""
    grid, _ = unpack(state)
    return sum(sum(row) for row in grid)


def heuristic_sand(state) -> int:
    """Heuristic 1 - sand-bearing columns (weak, join-aware).

    h(s) = number of columns that contain at least one sand cell.

    Rationale: a side door moves exactly one half-unit out of a FULL cell,
    leaving it half-full, and a half-full cell cannot use a side door at all.
    Therefore at least one half-unit of sand always remains in a column that
    ever contained sand, and that remainder can only leave downwards, through
    the column's own bottom-row gate.  Every gate opening costs at least 1,
    so each sand-bearing column contributes at least 1 to the total cost.
    Joins do not break this: a joined body drains through the gate of the
    bottom-row cell it sits in, which is still an opening in that column.
    """
    grid, _ = unpack(state)
    cols = len(grid[0]) if grid else 0
    return sum(1 for c in range(cols) if any(row[c] > 0 for row in grid))


def heuristic_column(state) -> int:
    """Heuristic 3 - structural bound (strong, join-aware).

    h(s) = N_above + C_sand

    where N_above is the number of non-empty cells that are NOT in the bottom
    row and C_sand is the number of columns containing sand (the same bound as
    heuristic 1).

    Rationale (two independent, non-overlapping lower bounds):

    1. N_above - every non-bottom cell holding sand must have its own bottom
       gate opened at least once.  Its sand can leave either by a direct
       downward transfer or through a join with the cell below (the join is
       itself created by opening that same gate).  Side doors cannot replace
       this: they move exactly one half-unit out of a FULL cell and leave it
       half-full, and a half-full cell cannot export anything, so some sand
       always remains and must eventually pass through the cell's own bottom
       gate.  Each opening costs at least 1.

    2. C_sand - see heuristic 1: each sand-bearing column needs at least one
       exit opening in its bottom row, at a cost of at least 1.

    The two terms count disjoint openings (gates of non-bottom cells vs. exit
    gates in the bottom row), so their sum cannot overestimate.  Joins are
    handled honestly: creating a join still costs one opening of the upper
    cell's gate, and draining a joined body still costs one opening of the
    exit gate.  The heuristic is consistent: no single action lowers it by
    more than that action's cost.
    """
    grid, _ = unpack(state)
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    above = sum(1 for r in range(rows - 1) for cell in grid[r] if cell > 0)
    return above + sum(1 for c in range(cols) if any(row[c] > 0 for row in grid))


HEURISTICS = {
    "A* (sand)": heuristic_sand,
    "A* (column)": heuristic_column,
}


def solve_astar(initial_state: State, heuristic) -> List[Action]:
    """A* search with an admissible, consistent heuristic - cost-optimal.

    Identical to UCS except that the priority is f = g + h(state) instead of
    the plain path cost g.
    """
    if is_empty_state(initial_state):
        return []

    counter = 0
    frontier: List[Tuple[int, int, State]] = [
        (heuristic(initial_state), counter, initial_state)
    ]
    best_cost: dict[State, int] = {initial_state: 0}
    parents: dict[State, Optional[Tuple[State, Action]]] = {initial_state: None}
    settled: set = set()

    while frontier:
        _f, _, state = heapq.heappop(frontier)
        if state in settled:
            continue
        settled.add(state)
        g = best_cost[state]
        if is_empty_state(state):
            return reconstruct_path(parents, state)
        for next_state, action, step_cost in successors(state):
            new_cost = g + step_cost
            if next_state in settled or new_cost >= best_cost.get(next_state, 10**9):
                continue
            best_cost[next_state] = new_cost
            parents[next_state] = (state, action)
            counter += 1
            heapq.heappush(frontier, (new_cost + heuristic(next_state), counter, next_state))

    raise ValueError("No emptying sequence was found for the given board.")


def solve_greedy(initial_state: State) -> List[Action]:
    """Special greedy strategy.

    Scan the cells independently from top to bottom (left to right inside a
    row).  Whenever a scanned cell contains sand, open its bottom gate and go
    on.  Passes are repeated, always in this fixed top-to-bottom order, until
    the grid is empty.
    """
    rows = len(initial_state)
    cols = len(initial_state[0]) if rows else 0
    state = initial_state
    actions: List[Action] = []

    while not is_empty_state(state):
        grid, _ = unpack(state)
        progress = False
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] > 0:
                    action = (r, c, "down")
                    next_state = apply_action(state, r, c, "down")
                    if next_state != state:
                        actions.append(action)
                        state = next_state
                        progress = True
        if not progress:
            raise ValueError("Greedy got stuck: sand cannot leave the grid.")
    return actions


SOLVERS = {
    "DFS": solve_dfs,
    "BFS": solve_bfs,
    "IDS": solve_ids,
    "UCS": solve_ucs,
    "Greedy": solve_greedy,
    "A* (sand)": lambda state: solve_astar(state, heuristic_sand),
    "A* (column)": lambda state: solve_astar(state, heuristic_column),
}


def solve(algorithm: str, initial_state: State) -> List[Action]:
    try:
        solver = SOLVERS[algorithm]
    except KeyError:
        raise ValueError(f"Unknown algorithm {algorithm!r}. Choose one of {ALGORITHMS}.")
    return solver(initial_state)


def solve_min_actions(initial_state: State) -> List[Action]:
    """Backwards-compatible alias for the BFS solver."""
    return solve_bfs(initial_state)


def path_cost(initial_state: State, actions: Sequence[Action]) -> int:
    """Total weighted cost of a plan under the gate/side-door cost model."""
    state = initial_state
    total = 0
    for action in actions:
        total += action_cost(state, action)
        state = apply_action(state, *action)
    return total


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------


def show_action_sequence(start_state, actions: Sequence[Action], delay: float = 0.7) -> None:
    """Print a simple animation of the board as each action is applied."""
    current = start_state
    print("Initial state")
    print_grid(current)

    for step, action in enumerate(actions, start=1):
        row, col, direction = action
        current = apply_action(current, row, col, direction)
        print(f"Step {step}: open {direction} door at ({row}, {col})")
        print_grid(current)
        if delay > 0:
            time.sleep(delay)


def run_gui(rows: int, cols: int, seed: Optional[int], algorithm: str = "BFS") -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk

    cell_size = 76
    colors = {0: "#f1f5f9", HALF: "#fbbf24", FULL: "#b45309"}
    labels = {0: "Empty", HALF: "Half", FULL: "Full"}
    result_queue: queue.Queue = queue.Queue()

    class SandPuzzleApp:
        def __init__(self, root: tk.Tk) -> None:
            self.root = root
            self.root.title("Sand Door Puzzle")
            self.root.minsize(520, 440)
            self.state = generate_random_state(rows, cols, rng=random.Random(seed))
            self.algorithm = algorithm if algorithm in ALGORITHMS else "BFS"
            self.solution: List[Action] = []
            self.solution_states: List[State] = []
            self.step_index = 0
            self.playing = False
            self.solving = False
            # Animation state: the world we animate FROM, the gate opened by
            # the current step, and the tween progress t in [0, 1].
            self.anim_from = None
            self.anim_gate: Optional[Action] = None
            self.anim_t = 1.0
            self.animating = False
            self.step_delay_ms = 650

            controls = ttk.Frame(root, padding=10)
            controls.pack(fill="x")

            ttk.Label(controls, text="Rows").grid(row=0, column=0, padx=(0, 4))
            self.rows_var = tk.StringVar(value=str(rows))
            ttk.Spinbox(controls, from_=1, to=12, width=4, textvariable=self.rows_var).grid(row=0, column=1, padx=(0, 12))

            ttk.Label(controls, text="Columns").grid(row=0, column=2, padx=(0, 4))
            self.cols_var = tk.StringVar(value=str(cols))
            ttk.Spinbox(controls, from_=1, to=12, width=4, textvariable=self.cols_var).grid(row=0, column=3, padx=(0, 12))

            ttk.Label(controls, text="Seed").grid(row=0, column=4, padx=(0, 4))
            self.seed_var = tk.StringVar(value="" if seed is None else str(seed))
            ttk.Entry(controls, width=9, textvariable=self.seed_var).grid(row=0, column=5, padx=(0, 8))

            ttk.Label(controls, text="Algorithm").grid(row=0, column=6, padx=(0, 4))
            self.algorithm_var = tk.StringVar(value=self.algorithm)
            self.algorithm_box = ttk.Combobox(
                controls, values=list(ALGORITHMS), state="readonly",
                width=8, textvariable=self.algorithm_var,
            )
            self.algorithm_box.grid(row=0, column=7, padx=(0, 8))

            self.random_button = ttk.Button(controls, text="Randomize", command=self.randomize)
            self.random_button.grid(row=0, column=8, padx=4)
            self.special_button = ttk.Button(controls, text="Special case", command=self.load_special_case)
            self.special_button.grid(row=0, column=9, padx=4)
            self.solve_button = ttk.Button(controls, text="Solve", command=self.solve)
            self.solve_button.grid(row=0, column=10, padx=4)
            self.analyze_button = ttk.Button(controls, text="Analyze", command=self.run_analysis)
            self.analyze_button.grid(row=0, column=11, padx=4)

            board_frame = ttk.Frame(root, padding=(10, 0, 10, 6))
            board_frame.pack(fill="both", expand=True)
            self.canvas = tk.Canvas(board_frame, background="white", highlightthickness=0)
            vertical = ttk.Scrollbar(board_frame, orient="vertical", command=self.canvas.yview)
            horizontal = ttk.Scrollbar(board_frame, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
            self.canvas.grid(row=0, column=0, sticky="nsew")
            vertical.grid(row=0, column=1, sticky="ns")
            horizontal.grid(row=1, column=0, sticky="ew")
            board_frame.rowconfigure(0, weight=1)
            board_frame.columnconfigure(0, weight=1)
            self.canvas.bind("<Button-1>", self.edit_cell)

            navigation = ttk.Frame(root, padding=(10, 4, 10, 10))
            navigation.pack(fill="x")
            self.reset_button = ttk.Button(navigation, text="Reset", command=self.reset)
            self.reset_button.pack(side="left", padx=(0, 5))
            self.previous_button = ttk.Button(navigation, text="Previous", command=self.previous)
            self.previous_button.pack(side="left", padx=5)
            self.play_button = ttk.Button(navigation, text="Play", command=self.toggle_play)
            self.play_button.pack(side="left", padx=5)
            self.next_button = ttk.Button(navigation, text="Next", command=self.next)
            self.next_button.pack(side="left", padx=5)
            ttk.Label(navigation, text="Speed").pack(side="left", padx=(16, 4))
            self.speed_var = tk.IntVar(value=3)
            ttk.Scale(
                navigation, from_=1, to=6, variable=self.speed_var,
                command=lambda _v: self.apply_speed(), length=120,
            ).pack(side="left", padx=2)
            self.status_var = tk.StringVar(value="Click cells to cycle between empty, half-full, and full.")
            ttk.Label(navigation, textvariable=self.status_var).pack(side="left", padx=12)

            self.draw_board()
            self.root.after(100, self.check_solver_result)

        def clear_solution(self) -> None:
            self.stop_playback()
            self.solution = []
            self.solution_states = []
            self.step_index = 0
            self.update_status()

        def draw_board(self, gate_flash: Optional[Action] = None, t: float = 1.0) -> None:
            """Draw the board.

            Cells are drawn as sand tanks whose fill height matches the sand
            level.  Vertically joined cells are merged into ONE tank: the sand
            of the whole connected run pools at its bottom instead of each
            cell filling separately.  `gate_flash` marks the gate opened by
            the current step; `t` in [0, 1] interpolates between the previous
            state (t = 0) and the current one (t = 1) so sand levels slide
            smoothly instead of jumping.
            """
            self.canvas.delete("all")
            grid, joins = unpack(self.state)
            prev_grid = prev_joins = None
            if self.anim_from is not None:
                prev_grid, prev_joins = unpack(self.anim_from)

            rows_count = len(grid)
            cols_count = len(grid[0]) if rows_count else 0
            margin = 6
            gate_w = 12  # width of a gate opening in a cell's bottom edge

            def interp(rr, cc):
                """Interpolated sand level (half-units) of cell (rr, cc)."""
                cur = grid[rr][cc]
                if prev_grid is None:
                    return float(cur)
                return prev_grid[rr][cc] + (cur - prev_grid[rr][cc]) * t

            def open_below(rr, cc):
                """Is the gate between (rr, cc) and the cell below open,
                considering current and (during a tween) previous joins?"""
                if (rr, cc) in joins:
                    return True
                return prev_joins is not None and t < 0.5 and (rr, cc) in prev_joins

            # Group each column into vertical runs of joined cells; every run
            # is drawn as ONE tank whose sand pools at its bottom.
            for c in range(cols_count):
                r = 0
                while r < rows_count:
                    run_top = r
                    while r + 1 < rows_count and open_below(r, c):
                        r += 1
                    run_bottom = r
                    r += 1

                    cx1 = c * cell_size + margin
                    cy1 = run_top * cell_size + margin
                    cx2 = cx1 + cell_size - 2 * margin
                    cy2 = run_bottom * cell_size + cell_size - margin

                    # Total sand in the run (interpolated, half-units); the
                    # fill fraction is measured against the run's capacity.
                    sand = sum(interp(rr, c) for rr in range(run_top, run_bottom + 1))
                    capacity = 2 * (run_bottom - run_top + 1)
                    fill_frac = min(1.0, sand / capacity)

                    inner_top = cy1 + 2
                    inner_bot = cy2 - 2
                    fill_h = (inner_bot - inner_top) * fill_frac
                    if fill_h > 0.5:
                        sand_color = "#b45309" if sand >= capacity - 0.25 else "#eab308"
                        self.canvas.create_rectangle(
                            cx1 + 2, inner_bot - fill_h, cx2 - 2, inner_bot,
                            fill=sand_color, outline="",
                        )

                    # Tank outline: one box around the whole run.  Internal
                    # joins get a sky-blue gate connector; the run's bottom
                    # edge opens (gap) when its gate is the one flashing.
                    bottom_flash = (
                        gate_flash is not None and gate_flash[2] == "down"
                        and gate_flash[0] == run_bottom and gate_flash[1] == c
                    )
                    parts = [
                        (cx1, cy1, cx2, cy1),   # top
                        (cx1, cy1, cx1, cy2),   # left
                        (cx2, cy1, cx2, cy2),   # right
                    ]
                    mid1 = (cx1 + cx2) / 2 - gate_w / 2
                    mid2 = (cx1 + cx2) / 2 + gate_w / 2
                    if bottom_flash:
                        parts.append((cx1, cy2, mid1, cy2))
                        parts.append((mid2, cy2, cx2, cy2))
                    else:
                        parts.append((cx1, cy2, cx2, cy2))
                    for (px1, py1, px2, py2) in parts:
                        hot = bottom_flash and py1 == cy2
                        self.canvas.create_line(
                            px1, py1, px2, py2,
                            fill="#0ea5e9" if hot else "#334155",
                            width=4 if hot else 2,
                        )
                    # sky-blue connectors across each internal join,
                    # drawn over the sand so the join stays visible
                    for rr in range(run_top, run_bottom):
                        if open_below(rr, c):
                            gy = rr * cell_size + cell_size - margin
                            self.canvas.create_line(
                                mid1, gy, mid2, gy, fill="#0ea5e9", width=4,
                                capstyle="butt",
                            )
                            self.canvas.create_line(
                                (cx1 + cx2) / 2, gy - 5,
                                (cx1 + cx2) / 2, gy + 5,
                                fill="#0ea5e9", width=2,
                            )

                    # labels as white badges so they stay readable on sand
                    for rr in range(run_top, run_bottom + 1):
                        lvl = interp(rr, c)
                        if lvl > 0.05:
                            text = labels[1] if lvl < FULL else labels[FULL]
                            tx = (cx1 + cx2) / 2
                            ty = rr * cell_size + margin + 12
                            self.canvas.create_rectangle(
                                tx - 22, ty - 9, tx + 22, ty + 9,
                                fill="#ffffff", outline="#334155", width=1,
                            )
                            self.canvas.create_text(
                                tx, ty, text=text, fill="#1e293b",
                                font=("Segoe UI", 9, "bold"),
                            )

            # --- gate-flash arrows (drawn last, on top of everything) ---
            if gate_flash is not None:
                gr, gc, gdir = gate_flash
                gx1 = gc * cell_size + margin
                gy1 = gr * cell_size + margin
                gx2 = gx1 + cell_size - 2 * margin
                gy2 = gy1 + cell_size - 2 * margin
                mid1 = (gx1 + gx2) / 2 - gate_w / 2
                mid2 = (gx1 + gx2) / 2 + gate_w / 2
                pulse = "#0ea5e9" if t < 1 else "#64748b"
                if gdir == "down":
                    self.canvas.create_line(
                        mid1, gy2 + 1, mid2, gy2 + 1, fill=pulse, width=5
                    )
                    arrow_y = gy2 + 10 + 6 * (1 - t)
                    self.canvas.create_line(
                        (gx1 + gx2) / 2, gy2 + 3,
                        (gx1 + gx2) / 2, arrow_y,
                        arrow="last", fill=pulse, width=2,
                    )
                else:
                    if gdir == "left":
                        ax1, ax2 = gx1 - 14, gx1 - 2
                    else:
                        ax1, ax2 = gx2 + 2, gx2 + 14
                    ay = (gy1 + gy2) / 2
                    self.canvas.create_line(
                        ax1, ay, ax2, ay,
                        arrow="last" if gdir == "right" else "first",
                        fill=pulse, width=2,
                    )
            self.canvas.configure(
                scrollregion=(0, 0, max(1, cols_count * cell_size), max(1, rows_count * cell_size))
            )

        def edit_cell(self, event: tk.Event) -> None:
            if self.solving:
                return
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            grid, _ = unpack(self.state)
            col = int(x // cell_size)
            row = int(y // cell_size)
            if row >= len(grid) or col >= len(grid[0]):
                return
            board = [list(line) for line in grid]
            board[row][col] = (board[row][col] + 1) % 3
            self.state = tuple(tuple(line) for line in board)
            self.clear_solution()
            self.draw_board()

        def randomize(self) -> None:
            try:
                new_rows = int(self.rows_var.get())
                new_cols = int(self.cols_var.get())
                if not 1 <= new_rows <= 12 or not 1 <= new_cols <= 12:
                    raise ValueError("Rows and columns must be between 1 and 12.")
                seed_text = self.seed_var.get().strip()
                new_seed = int(seed_text) if seed_text else None
            except ValueError as error:
                messagebox.showerror("Invalid grid settings", str(error), parent=self.root)
                return
            self.stop_playback()
            self.state = generate_random_state(
                new_rows, new_cols, rng=random.Random(new_seed)
            )
            self.clear_solution()
            self.draw_board()

        def load_special_case(self) -> None:
            self.stop_playback()
            self.rows_var.set("4")
            self.cols_var.set("2")
            self.state = special_case_state()
            self.clear_solution()
            self.draw_board()

        def solve(self) -> None:
            if self.solving:
                return
            self.algorithm = self.algorithm_var.get()
            self.solving = True
            self.solve_button.configure(state="disabled")
            self.random_button.configure(state="disabled")
            self.special_button.configure(state="disabled")
            self.analyze_button.configure(state="disabled")
            self.status_var.set(f"Searching with {self.algorithm}...")
            start_state = self.state

            def search() -> None:
                try:
                    result_queue.put((start_state, solve(self.algorithm, start_state), None))
                except Exception as error:
                    result_queue.put((start_state, None, error))

            threading.Thread(target=search, daemon=True).start()

        def run_analysis(self) -> None:
            """Run the exhaustive Greedy-vs-optimal analysis in the background.

            Uses the Rows/Columns spinboxes as the board size and analyses ALL
            3^(rows*cols) initial states (or warns when that is too many).
            Results (CSV + PNGs) are written to analysis_output/.
            """
            if self.solving:
                return
            self.solving = True
            self.solve_button.configure(state="disabled")
            self.random_button.configure(state="disabled")
            self.special_button.configure(state="disabled")
            self.analyze_button.configure(state="disabled")
            try:
                rows = int(self.rows_var.get())
                cols = int(self.cols_var.get())
                if not 1 <= rows <= 4 or not 1 <= cols <= 4:
                    raise ValueError("Analysis supports boards up to 4x4 (3^16 states).")
                n_states = 3 ** (rows * cols)
            except ValueError as error:
                messagebox.showerror("Invalid analysis settings", str(error), parent=self.root)
                self.solving = False
                self.solve_button.configure(state="normal")
                self.random_button.configure(state="normal")
                self.special_button.configure(state="normal")
                self.analyze_button.configure(state="normal")
                return
            self.status_var.set(f"Analysing {n_states} states of the {rows}x{cols} board...")

            def worker() -> None:
                try:
                    import analysis as analysis_mod
                    import os
                    os.makedirs(analysis_mod.OUT_DIR, exist_ok=True)
                    results = analysis_mod.analyse(rows, cols)
                    if results:
                        csv_path = os.path.join(analysis_mod.OUT_DIR, f"results_{rows}x{cols}.csv")
                        analysis_mod.save_csv(results, csv_path)
                        analysis_mod.make_plots(results, analysis_mod.OUT_DIR)
                        analysis_mod.print_summary(results)
                        result_queue.put(("__analysis__", (rows, cols, len(results)), None))
                    else:
                        result_queue.put(("__analysis__", None, RuntimeError("No solvable states found.")))
                except Exception as error:
                    result_queue.put(("__analysis__", None, error))

            threading.Thread(target=worker, daemon=True).start()

        def check_solver_result(self) -> None:
            try:
                start_state, payload, error = result_queue.get_nowait()
            except queue.Empty:
                self.root.after(100, self.check_solver_result)
                return
            if start_state == "__analysis__":
                self.solving = False
                self.solve_button.configure(state="normal")
                self.random_button.configure(state="normal")
                self.special_button.configure(state="normal")
                self.analyze_button.configure(state="normal")
                if error is not None:
                    messagebox.showerror("Analysis failed", str(error), parent=self.root)
                    self.status_var.set("Analysis failed.")
                else:
                    rows, cols, count = payload
                    self.status_var.set(
                        f"Analysis done: {count} states -> analysis_output/ "
                        f"(results_{rows}x{cols}.csv + 3 PNG plots)"
                    )
                self.root.after(100, self.check_solver_result)
                return
            actions, error = payload, error
            self.solving = False
            self.solve_button.configure(state="normal")
            self.random_button.configure(state="normal")
            self.special_button.configure(state="normal")
            self.analyze_button.configure(state="normal")
            if start_state == self.state:
                if error is not None:
                    messagebox.showerror("Unable to solve puzzle", str(error), parent=self.root)
                    self.status_var.set("No solution was found.")
                else:
                    self.solution = actions or []
                    states = [start_state]
                    current = start_state
                    for action in self.solution:
                        current = apply_action(current, *action)
                        states.append(current)
                    self.solution_states = states
                    self.step_index = 0
                    self.update_status()
            self.root.after(100, self.check_solver_result)

        def update_status(self) -> None:
            if not self.solution_states:
                if not self.solving:
                    self.status_var.set("Click cells to cycle between empty, half-full, and full.")
                return
            cost = path_cost(self.solution_states[0], self.solution)
            if self.step_index == 0:
                text = (
                    f"{self.algorithm}: {len(self.solution)} openings · cost {cost} · Initial state"
                )
            else:
                row, col, direction = self.solution[self.step_index - 1]
                text = (
                    f"{self.algorithm}: {len(self.solution)} openings · cost {cost} · "
                    f"Step {self.step_index}/{len(self.solution)}: "
                    f"open {direction} at row {row + 1}, column {col + 1}"
                )
            self.status_var.set(text)

        def apply_speed(self) -> None:
            """Map the 1..6 speed slider to the per-step delay in ms."""
            self.step_delay_ms = [1600, 1100, 800, 650, 420, 250][max(0, min(5, self.speed_var.get() - 1))]

        def gate_for_step(self, step_index: int) -> Optional[Action]:
            if 1 <= step_index <= len(self.solution):
                return self.solution[step_index - 1]
            return None

        def start_tween(self, gate: Optional[Action]) -> None:
            """Animate from the previously displayed world to self.state."""
            self.anim_gate = gate
            self.animating = True
            self.anim_t = 0.0
            self.animate_tick()

        def animate_tick(self) -> None:
            if not self.animating:
                return
            self.anim_t = min(1.0, self.anim_t + 0.12)
            self.draw_board(self.anim_gate, self.anim_t)
            if self.anim_t < 1.0:
                self.root.after(16, self.animate_tick)
            else:
                self.animating = False
                self.anim_from = None
                self.anim_gate = None
                self.draw_board()
                if self.playing:
                    self.root.after(self.step_delay_ms, self.advance_playback)

        def show_step(self, animate: bool = True) -> None:
            previous = self.state
            self.state = self.solution_states[self.step_index]
            gate = self.gate_for_step(self.step_index)
            if animate and not self.animating and previous != self.state:
                self.anim_from = previous
                self.start_tween(gate)
            else:
                self.draw_board()
            self.update_status()

        def next(self) -> None:
            if self.step_index >= len(self.solution):
                self.stop_playback()
                return
            self.step_index += 1
            self.show_step()
            if not self.animating and self.step_index == len(self.solution):
                self.stop_playback()

        def previous(self) -> None:
            if self.step_index == 0:
                return
            self.step_index -= 1
            self.show_step()

        def reset(self) -> None:
            self.stop_playback()
            if self.solution_states:
                self.step_index = 0
                self.show_step(animate=False)

        def toggle_play(self) -> None:
            if self.playing:
                self.stop_playback()
            elif self.solution:
                if self.step_index >= len(self.solution):
                    self.step_index = 0
                    self.show_step(animate=False)
                self.playing = True
                self.play_button.configure(text="Pause")
                self.advance_playback()

        def advance_playback(self) -> None:
            if not self.playing or self.animating:
                return
            self.next()
            # Continuation is normally handled by animate_tick; if no tween
            # ran (identical consecutive states), advance directly.
            if self.playing and not self.animating:
                if self.step_index >= len(self.solution):
                    self.stop_playback()
                else:
                    self.root.after(self.step_delay_ms, self.advance_playback)

        def stop_playback(self) -> None:
            self.playing = False
            self.play_button.configure(text="Play")

    root = tk.Tk()
    app = SandPuzzleApp(root)
    root._app_probe = app
    import os
    if getattr(root, "_scripted", False) or os.environ.get("SANDBOX_SCRIPTED") == "1":
        return app
    root.mainloop()
    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve the sand-door puzzle with DFS, BFS, IDS, UCS, Greedy or A* and visualize the plan."
    )
    parser.add_argument("--cli", action="store_true", help="Run the command-line interface instead of the GUI.")
    parser.add_argument("--algo", choices=ALGORITHMS, default="BFS", help="Search algorithm to use (default: BFS).")
    parser.add_argument("--special-case", action="store_true", help="Use the fixed 4x2 test grid instead of a random board.")
    parser.add_argument("--rows", type=int, default=None, help="Number of rows in the grid.")
    parser.add_argument("--cols", type=int, default=None, help="Number of columns in the grid.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible generation.")
    parser.add_argument("--delay", type=float, default=0.7, help="Seconds to pause between animation frames.")
    parser.add_argument("--no-animate", action="store_true", help="Do not animate the solution. Only print the action list.")
    parser.add_argument(
        "--analyze", action="store_true",
        help="Exhaustive analysis mode: enumerate initial states, compare Greedy "
             "against the optimum, and write histogram analysis_output/. "
             "Use with --rows/--cols and optionally --sample N. Requires matplotlib."
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="With --analyze: analyse a random sample of N states instead of all."
    )
    return parser.parse_args()


def run_analysis(args: argparse.Namespace) -> None:
    """Delegate to analysis.py (imported lazily to avoid a circular import)."""
    try:
        import analysis
    except ImportError as error:
        print("Analysis requires matplotlib:", error)
        print("Install it with:  pip install matplotlib")
        return
    rows = args.rows or 2
    cols = args.cols or 2
    # analysis.parse-free entry point: replicate its main() with our args.
    import os
    os.makedirs(analysis.OUT_DIR, exist_ok=True)
    results = analysis.analyse(rows, cols, limit=args.sample, seed=args.seed)
    if not results:
        print("No results - nothing to plot.")
        return
    csv_path = os.path.join(analysis.OUT_DIR, f"results_{rows}x{cols}.csv")
    analysis.save_csv(results, csv_path)
    analysis.make_plots(results, analysis.OUT_DIR)
    analysis.print_summary(results)


def main() -> None:
    args = parse_args()
    if args.analyze:
        run_analysis(args)
        return
    if not args.cli:
        run_gui(args.rows or 3, args.cols or 4, args.seed, algorithm=args.algo)
        return

    if args.special_case:
        initial_state = special_case_state()
        print("Fixed special-case board:")
    else:
        rows = args.rows or 4
        cols = args.cols or 5
        rng = random.Random(args.seed)
        initial_state = generate_random_state(rows, cols, rng=rng)
        print(f"Random board generated with seed={args.seed}:")

    print_grid(initial_state)

    actions = solve(args.algo, initial_state)
    total_cost = path_cost(initial_state, actions)
    print(f"{args.algo}: {len(actions)} door openings, weighted cost {total_cost}")
    if actions:
        print("Actions:")
        for index, action in enumerate(actions, start=1):
            row, col, direction = action
            print(f"  {index}. open {direction} door at ({row}, {col})")
    else:
        print("No actions required; the grid is already empty.")

    if not args.no_animate and actions:
        print("\nAnimation:")
        show_action_sequence(initial_state, actions, delay=args.delay)


if __name__ == "__main__":
    main()
