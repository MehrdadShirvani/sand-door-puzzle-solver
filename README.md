# Sand Door Puzzle

A solver and visualizer for the "sand door" grid puzzle. Sand drains through
gates in a grid of cells, and the goal is to find the cheapest plan that empties
the whole grid. Five search algorithms are implemented — **DFS**, **BFS**,
**IDS**, **UCS**, and a special **Greedy** scan — and any of them can be picked
from the GUI or the command line.

## Problem Statement

## Grid and cell states

The system is a grid with `r` rows and `c` columns. Each cell has one of three
states:

- `0`: full of sand
- `0.5`: half-full of sand
- `1`: empty

Each cell has a gate on its bottom edge and a door connecting it to each
adjacent cell.

## Actions and sand movement

Opening any door counts as one action.

- **Bottom gate:** If the cell contains sand, opening its bottom gate lets the
  sand fall into the cell below.

- **Side door:** If the cell is full, opening a side door moves half of its sand
  into the adjacent cell. If the cell is half-full, opening a side door has no
  effect.

Doors close after the sand has passed through or when opening them has no
effect. There is one exception: a door between two cells remains open when both
cells contain sand, the lower cell becomes full, and the upper cell is either
full or half-full. In this case, the sand in the two cells connects.

## Costs

Action A: top-down gate
cost = 1 + 4 * (s + s')
s: the state of the upper box BEFORE flushing (0, 1 or ½)
s': the state of the upper box AFTER flushing (0, 1 or ½)

Action B: side gate
cost = 1

## Objective

Empty all cells by moving the sand down and out through the bottom of the grid.
Find a sequence of actions that achieves this using the fewest possible door
openings.

## Initial state and visualization

Generate a random initial grid in which approximately half of the cells are
empty, with the remaining cells split between half-full and full.

Provide a visualization that shows each action in the sequence as it happens.
## Implementation

All of the logic lives in a single file, [`problem.py`](problem.py). Sand is
stored internally in *half-units* (`0`, `1`, `2`) so that the `0.5` sand
transfers are exact integer arithmetic.

| Symbol | Meaning                |
| ------ | ---------------------- |
| `.`    | empty cell             |
| `H`    | half-full cell (0.5)   |
| `F`    | full cell (1.0)        |

### Search algorithms

| Algorithm   | Class                          | Optimal in openings? | Notes                                                                       |
| ----------- | ------------------------------ | -------------------- | --------------------------------------------------------------------------- |
| **DFS**     | Iterative graph-search DFS     | No                   | Explores deep branches first; complete here thanks to the visited set.       |
| **BFS**     | Breadth-first search           | Yes (fewest openings)| The baseline "fewest door openings" solver.                                  |
| **IDS**     | Iterative deepening DFS        | Yes (fewest openings)| Depth-limited DFS with the current path only on the visited set.             |
| **UCS**     | Uniform-cost search (Dijkstra) | Yes (fewest cost)    | Uses the weighted gate/side-door costs, so it minimizes cost, not openings.  |
| **A* (sand)** | A* with the total-sand heuristic  | Yes (fewest cost) | f = g + h where h is the total remaining sand. Admissible but weak.         |
| **A* (column)** | A* with the per-column heuristic | Yes (fewest cost) | f = g + h where h combines the structural lower bounds below. Much stronger |
| **Greedy**  | Fixed deterministic strategy   | No                   | Scans the grid top-to-bottom, left-to-right; each sand-bearing cell gets its bottom gate opened. Passes repeat until the grid is empty. |

Cost model (as in the statement):

- **Bottom gate (Action A):** `cost = 1 + 4 * (s + s')`, where `s` / `s'` are
  the upper cell's sand amount (`0`, `0.5` or `1`) before / after flushing.
- **Side door (Action B):** `cost = 1`.

### A* heuristics

A* is UCS with an informed priority: nodes are ordered by `f = g + h(state)`,
where `g` is the path cost so far and `h` estimates the remaining cost. Both
heuristics below are **admissible** (never overestimate) and **consistent**,
so both A* variants are guaranteed to return a cost-optimal plan, exactly like
UCS — they just expand far fewer nodes because the search is steered toward
the goal. Side doors are deliberately *relaxed away* in both: they cost 1 but
remove no sand and cannot move sand out of the grid, so ignoring them keeps
the bounds safe.

#### Heuristic 1 — total remaining sand (used by `A* (sand)`)

```
h(s) = S            # S = total sand in the grid, in half-units
```

*Rationale:* sand leaves the grid only through bottom-row gates, and each exit
opening flushes at most 2 half-units at a cost of `1 + 2·(b + b')` (with `b'`
the sand left in the cell after flushing). With `S` half-units still to remove,
any plan therefore pays at least `ceil(S/2)` exit openings plus at least `2S`
from the flushing surcharges — comfortably more than `S`. So one cost unit per
remaining half-unit of sand is a safe lower bound. It is cheap to compute and
monotone, but it ignores *where* the sand sits, so it is weak: every cell that
gains sand mid-plan raises `h` back up even though that transfer was necessary.

#### Heuristic 3 — per-column structural bound (used by `A* (column)`)

```
h(s) = N_above + ceil(S / 2) + 2·S
```

where `S` is again the total sand in half-units and `N_above` is the number of
non-empty cells **not in the bottom row**. It sums three independent,
non-overlapping lower bounds:

1. **`N_above`** — every non-bottom cell holding sand must have its bottom
   gate opened at least once to pass its sand downward, and each opening costs
   at least 1.
2. **`ceil(S/2)`** — all `S` half-units must leave through bottom-row gates,
   each of which flushes at most 2 half-units, so at least `ceil(S/2)` exit
   openings are required.
3. **`2S`** — an exit opening flushing `t` half-units from a cell that held
   `b` costs `1 + 2(b + b')` with `b' = b − t`, i.e. `1 + 4b − 2t ≥ 1 + 2t`.
   Summed over all the sand that must exit, that is at least 2 per half-unit.

Because the three terms count disjoint aspects of any plan (interior gate
openings, exit-opening count, exit-opening surcharges), adding them cannot
overestimate. This dominates heuristic 1 and is much stronger on tall or
tightly-packed boards, since it also rewards the search for emptying the
*upper* rows, not just for reducing the total sand.

### Random initial state

`generate_random_state` builds an `r × c` grid where each cell is empty with
probability `0.5`, half-full with probability `0.25`, and full with probability
`0.25` — i.e. roughly half of the cells are empty and the rest are split evenly
between half-full and full. A seed makes boards reproducible.

## Usage

Requirements: Python 3.9+ (the GUI uses Tkinter, bundled with CPython on
Windows). No third-party packages.

```powershell
# GUI (default) — pick the algorithm from the dropdown, click cells to edit
python problem.py

# CLI with a random board, UCS solver, animated output
python problem.py --cli --algo UCS

# Fixed special-case board with every algorithm
python problem.py --cli --special-case --algo Greedy --no-animate
```

CLI flags:

| Flag             | Effect                                                            |
| ---------------- | ----------------------------------------------------------------- |
| `--cli`          | Run the command-line interface instead of the GUI.                |
| `--algo`         | `DFS`, `BFS`, `IDS`, `UCS`, `A* (sand)`, `A* (column)`, or `Greedy` (default `BFS`). |
| `--special-case` | Use the fixed 4×2 test grid described below.                       |
| `--rows N`       | Number of rows (GUI/CLI random board).                             |
| `--cols N`       | Number of columns (GUI/CLI random board).                          |
| `--seed N`       | Seed for the random board.                                         |
| `--delay S`      | Seconds between animation frames in the CLI (default `0.7`).       |
| `--no-animate`   | Print the plan only, skip the step-by-step animation.              |

### GUI

- **Rows / Columns / Seed** — configure and regenerate the random board.
- **Algorithm** — dropdown to select `DFS`, `BFS`, `IDS`, `UCS`, or `Greedy`.
- **Special case** — one click loads the fixed test grid.
- **Click any cell** to cycle it between empty → half-full → full.
- **Solve** runs the chosen algorithm on a background thread (the UI stays
  responsive), then **Play / Pause / Next / Previous / Reset** step through the
  plan as an animation. The status bar shows the number of openings and the
  weighted cost of the plan.

## Special test case

The required hand-made board is available in the GUI via the **Special case**
button, and on the CLI via `--special-case`:

```
1 0
0 1
0 1
1 0
```

(where `1` = sand-filled, `0` = empty). Every algorithm solves it; typical
results:

```
DFS    : 24 openings, cost  64
BFS    : 10 openings, cost  50
IDS    : 10 openings, cost  50
UCS    : 10 openings, cost  50
A* (sand)   : 10 openings, cost  50
A* (column) : 10 openings, cost  50
Greedy : 10 openings, cost  50
```

BFS, IDS, UCS and Greedy all reach the 10-opening optimum on this board, while
DFS wanders into a much longer plan — a nice illustration of why uninformed
depth-first search is not optimal.
