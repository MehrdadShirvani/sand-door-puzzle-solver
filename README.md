# Sand Door Puzzle

A solver and visualizer for the "sand door" grid puzzle. Sand drains through
gates in a grid of cells, and the goal is to find the cheapest plan that empties
the whole grid. Seven search algorithms are implemented — **DFS**, **BFS**,
**IDS**, **UCS**, **A\* (sand)**, **A\* (column)**, and a special **Greedy**
scan — and any of them can be picked from the GUI or the command line.

## How to start

### Prerequisites

- **Python 3.9 or newer** — the code uses `list[str]`-style generics and the
  GUI is built with **Tkinter**, which ships with the standard CPython
  installer on Windows (`python.org` downloads include `tcl/tk` by default).
- **No third-party packages.** There is no `pip install` step, no virtualenv,
  and no build step — the whole project is a single script, [`problem.py`](problem.py).
- On Linux you may need the Tk package separately (`sudo apt install
  python3-tk`); on macOS the standard installer or Homebrew Python already has
  it. Windows needs nothing extra.

Check that you have a suitable interpreter:

```powershell
python --version        # should print Python 3.9.x or newer
python -c "import tkinter; print('Tkinter OK')"
```

### Getting the project

Just place `problem.py` (and this `README.md`) anywhere you like — no other
files are needed. If it is inside a git repository:

```powershell
git clone <repository-url>
cd <repository-folder>
```

### Running it

From the project folder:

```powershell
# 1. Launch the GUI (default mode)
python problem.py

# 2. Or run a quick CLI solve of the fixed special-case board
python problem.py --cli --special-case --algo "A* (column)" --no-animate
```

The first command opens a window: set **Rows / Columns / Seed** or click
**Special case**, choose an **Algorithm** from the dropdown (DFS, BFS, IDS,
UCS, A* (sand), A* (column), Greedy), then press **Solve** and use
**Play / Next / Previous** to watch the plan unfold.

The second prints the board, the plan, and the weighted cost directly in the
terminal — useful for quick checks and for scripting.

### All CLI commands in one place

```powershell
# GUI (default)
python problem.py

# GUI, 5x5 board, reproducible via seed
python problem.py --rows 5 --cols 5 --seed 42

# CLI with a random board, animated output (default algorithm: BFS)
python problem.py --cli

# CLI, pick any algorithm: DFS | BFS | IDS | UCS | "A* (sand)" | "A* (column)" | Greedy
python problem.py --cli --algo UCS
python problem.py --cli --algo "A* (column)"

# CLI on the fixed 4x2 special-case board, plan only (no animation)
python problem.py --cli --special-case --algo Greedy --no-animate

# CLI with animation, 0.3 s between frames
python problem.py --cli --special-case --delay 0.3

# Custom board size and seed on the CLI
python problem.py --cli --rows 4 --cols 4 --seed 7
```

Full flag reference is in the [Usage](#usage) section below.

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

In CLI output a `=` line between two rows marks a **joined** pair: the gate
between the cell above and the cell below is held open (see the joining rule
in the problem statement), and the sand in the two cells drains as one body.

### Search algorithms

| Algorithm   | Class                          | Optimal in openings? | Notes                                                                       |
| ----------- | ------------------------------ | -------------------- | --------------------------------------------------------------------------- |
| **DFS**     | Iterative graph-search DFS     | No                   | Explores deep branches first; complete here thanks to the visited set.       |
| **BFS**     | Breadth-first search           | Yes (fewest openings)| The baseline "fewest door openings" solver.                                  |
| **IDS**     | Iterative deepening DFS        | Yes (fewest openings)| Depth-limited DFS with the current path only on the visited set.             |
| **UCS**     | Uniform-cost search (Dijkstra) | Yes (fewest cost)    | Uses the weighted gate/side-door costs, so it minimizes cost, not openings.  |
| **A* (sand)** | A* with the sand-bearing-columns heuristic | Yes (fewest cost) | f = g + h where h counts sand-bearing columns. Admissible but weak.         |
| **A* (column)** | A* with the structural heuristic | Yes (fewest cost) | f = g + h combining sand-bearing columns with non-bottom sand cells. Stronger |
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
the bounds safe. Joins (see the joining rule) are accounted for honestly: a
join is created by one gate opening, and a joined body drains through the exit
gate of the bottom-row cell it sits in, which is still an opening in that
column — so both heuristics stay admissible and consistent in the presence of
joins.

#### Heuristic 1 — sand-bearing columns (used by `A* (sand)`)

```
h(s) = C_sand      # number of columns that contain at least one sand cell
```

*Rationale:* a side door moves exactly one half-unit out of a FULL cell and
leaves it half-full, and a half-full cell cannot use a side door at all.
Therefore at least one half-unit of sand always remains in a column that ever
contained sand, and that remainder can only leave downwards, through the
column's own bottom-row gate. Every gate opening costs at least 1, so each
sand-bearing column contributes at least 1 to the total cost. It is cheap to
compute and monotone, but it ignores how much sand sits in each column, so it
is weak on boards with many filled cells.

#### Heuristic 3 — structural bound (used by `A* (column)`)

```
h(s) = N_above + C_sand
```

where `C_sand` is the number of sand-bearing columns (heuristic 1) and
`N_above` is the number of non-empty cells **not in the bottom row**. It sums
two independent, non-overlapping lower bounds:

1. **`N_above`** — every non-bottom cell holding sand must have its own bottom
   gate opened at least once. Its sand leaves either by a direct downward
   transfer or through a join with the cell below (the join is itself created
   by opening that same gate). Side doors cannot replace this: they move one
   half-unit out of a FULL cell and leave it half-full, so some sand always
   remains and must eventually pass through the cell's own bottom gate.
2. **`C_sand`** — each sand-bearing column needs at least one exit opening in
   its bottom row (see heuristic 1).

The two terms count disjoint openings (gates of non-bottom cells vs. exit
gates in the bottom row), so their sum cannot overestimate. This dominates
heuristic 1 and is much stronger on tall or tightly-packed boards, since it
rewards the search for emptying the *upper* rows, not just for reducing the
sand.

> **Why the heuristics changed when joins were introduced:** the earlier
> formulation assumed each exit opening flushes at most 2 half-units. With
> joined bodies that is false — a joined stack can drain entirely through one
> exit opening — so the old bound could overestimate. The formulas above are
> safe under joins as well as plain transfers.

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
- **Algorithm** — dropdown to select `DFS`, `BFS`, `IDS`, `UCS`, `A* (sand)`, `A* (column)`, or `Greedy`.
- **Special case** — one click loads the fixed test grid.
- **Click any cell** to cycle it between empty → half-full → full.
- **Solve** runs the chosen algorithm on a background thread (the UI stays
  responsive), then **Play / Pause / Next / Previous / Reset** step through the
  plan as an animated sequence:
  - cells are drawn as **sand tanks** whose fill height tracks the sand level,
  - between steps the sand levels **slide smoothly** to their new positions
    instead of jumping,
  - the **gate opened by the current step flashes** with an arrow showing the
    transfer direction, until the next step begins,
  - **joined cells render as one connected body**: the shared edge opens up and
    the sand flows visually through the gate gap,
  - a **Speed slider** (1–6) controls the per-step delay (1.6 s down to 0.25 s).
- The status bar shows the number of openings and the weighted cost of the plan.

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
DFS         : 24 openings, cost  64
BFS         :  7 openings, cost  47
IDS         :  7 openings, cost  47
UCS         : 10 openings, cost  34
A* (sand)   : 10 openings, cost  34
A* (column) : 10 openings, cost  34
Greedy      :  8 openings, cost  48
```

With the joining rule in force, UCS and both A\* variants find the true
cost-34 optimum on this board (a joined body drains through a single exit
gate, which plain BFS/IDS cannot exploit since they only count openings).
BFS/IDS still minimize the number of door openings (7), while the cost-aware
searches exploit joins to cut the weighted cost — a good illustration of the
difference between the two objectives. DFS still produces a much longer plan.
