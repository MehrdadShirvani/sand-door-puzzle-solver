# Sand Door Puzzle Solver

A Python project for solving and visualizing the sand door grid puzzle. The goal is to empty a grid of sand by opening gates and doors in a valid sequence while minimizing the total cost.

This repository includes:

- a Tkinter GUI for interactive solving and animation
- a CLI for quick experiments and scripted runs
- multiple search strategies, including BFS, IDDFS, UCS, and A*
- exhaustive analysis tools that compare greedy play against optimal solutions

## Why this project

The puzzle combines pathfinding, state-space search, and physics-like flow rules. It is a good example of how graph-search algorithms behave when the state transitions are nontrivial and the cost function is not simply the number of moves.

## Features

- 8 solving algorithms
  - DFS
  - BFS
  - IDS
  - UCS
  - A* with the sand-bearing-column heuristic
  - A* with the structural heuristic
  - Local Search (hill climbing seeded from the Greedy plan)
  - Greedy scan strategy
- Effective branching-factor estimation for every search run
- Random board generation with reproducible seeds
- Fixed special-case board for validation
- GUI and command-line modes
- Animated replay of the solution path
- Analysis output for comparing greedy and optimal strategies

## Project structure

- `problem.py` - main solver, GUI, and CLI
- `analysis.py` - exhaustive board analysis and plot generation
- `HEURISTIC.md` - definitions and admissibility/consistency proofs for the A* heuristics
- `test_local_search.py` - unit tests (environment edge cases, plan scoring, Local Search)
- `test_anim_smoke.py` - script-style smoke test (UCS vs. A* cost agreement, joins)
- `analysis_output/` - generated CSV and PNG analysis results

## Requirements

- Python 3.9 or newer
- Tkinter, which is included with standard Python installations on Windows
- matplotlib (optional; only needed for `analysis.py` / `--analyze` plots)

See `requirements.txt`. The core solver (`problem.py`, CLI, tests,
`evaluate_boards.py`) uses only the standard library.

## Complete Windows PowerShell setup

Run each block below in a normal PowerShell window.

### 1. Check the Python version (3.9+)

```powershell
python --version
```

### 2. Check that Tkinter is available

```powershell
python -c "import tkinter; print('Tkinter OK')"
```

### 3. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked by the execution policy:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command ".\.venv\Scripts\Activate.ps1"
```

or simply use `.\.venv\Scripts\python.exe` in place of `python` below.

### 4. Install dependencies (and check matplotlib)

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
python -c "import matplotlib; print('matplotlib', matplotlib.__version__)"
```

matplotlib is only required for the exhaustive-analysis plots; every other
feature runs without it.

### 5. Launch the GUI

```powershell
python problem.py
```

### 6. Run the CLI

```powershell
python problem.py --cli
python problem.py --cli --algo UCS
python problem.py --cli --algo "Local Search"
```

### 7. Run the fixed test board

```powershell
python problem.py --cli --special-case --algo "A* (column)" --no-animate
```

### 8. Run a random board

```powershell
python problem.py --cli --rows 4 --cols 4 --seed 7 --algo UCS
```

### 9. Run the unit tests

```powershell
python -m unittest test_local_search -v
```

The slow-but-complete smoke test (~3-4 minutes, runs UCS + both A*
variants over 12 seeded random boards) is a plain script:

```powershell
python test_anim_smoke.py
```

### 10. Run exhaustive analysis

```powershell
python analysis.py --rows 2 --cols 2
python problem.py --analyze --rows 2 --cols 3 --sample 400 --seed 0
```

### 11. Run the solver benchmark

```powershell
python evaluate_boards.py
```

### 12. Chain commands with `;`, not `&&`

```powershell
python -m unittest test_local_search; python evaluate_boards.py
```

## Quick start

### Launch the GUI

```powershell
python problem.py
```

This opens the interactive interface where you can:

- set rows and columns
- generate a random board
- load the special-case board
- choose a solver
- solve the puzzle
- replay the plan step by step

### Run the CLI on the fixed test board

```powershell
python problem.py --cli --special-case --algo "A* (column)" --no-animate
```

### Run a random board through the CLI

```powershell
python problem.py --cli --algo UCS
```

## Supported commands

```powershell
# GUI
python problem.py

# GUI with custom board size and seed
python problem.py --rows 5 --cols 5 --seed 42

# CLI on a random board
python problem.py --cli

# CLI with a specific solver
python problem.py --cli --algo UCS
python problem.py --cli --algo "A* (column)"

# CLI with the fixed special-case board
python problem.py --cli --special-case --algo Greedy --no-animate
python problem.py --cli --special-case --algo "A* (column)"

# Every registered algorithm works through --algo, including Local Search
python problem.py --cli --special-case --algo "Local Search" --no-animate

# CLI with animation delay
python problem.py --cli --special-case --delay 0.3

# Custom random board size
python problem.py --cli --rows 4 --cols 4 --seed 7

# Exhaustive analysis
python analysis.py --rows 2 --cols 2
python problem.py --analyze --rows 2 --cols 3 --sample 400
```

All commands above run as-is in **Windows PowerShell** (they use no shell
operators beyond simple arguments). To chain commands, use `;` instead of
`&&`, e.g.:

```powershell
python -m unittest test_local_search; python test_anim_smoke.py
```

## Puzzle rules

The board is a grid of cells with different sand loads:

- empty
- half-full
- full

Each action opens a gate or door. Sand can flow downward or sideways under the puzzle rules, and joined cells can drain together as a single connected body when the joining condition is met.

The project implements the weighted cost model from the puzzle specification:

- bottom gate actions cost more than simple side-door moves
- the solver minimizes the true cost, not only the raw number of actions
- BFS and IDDFS are still useful for minimizing the number of openings, while UCS and A* optimize cost

## Algorithm summary

- DFS: deep exploration, not cost-optimal
- BFS: shortest by number of openings
- IDS: depth-limited search with path pruning
- UCS: cost-optimal by weighted path cost
- A* (sand): informed but weaker heuristic, cost-optimal
- A* (column): stronger structural heuristic, cost-optimal
- Greedy: deterministic scan strategy, not globally optimal
- Local Search: hill climbing from Greedy; never worse than Greedy, not optimal

## Effective branching factor

For a search that expands N nodes and finds a plan at depth d, the
effective branching factor b is the solution of

```text
N = 1 + b + b^2 + ... + b^d = (b^(d+1) - 1) / (b - 1)     (b != 1)
```

`effective_branching_factor(n, d)` in `problem.py` solves this by bisection
on b in (1, 100]. Edge cases are handled without division errors: if
N <= 1 or d == 0 the branching factor is undefined and `None` (reported as
`n/a`) is returned; for d == 1, b = N - 1 exactly; for N == d + 1 (a bare
chain), b = 1 exactly.

**Limitations.** The formula assumes a *uniform* search tree: constant
branching at every level, a goal found only at depth d, no duplicate
detection and no pruning. Real searches here use visited/closed sets and
heuristic ordering, so the measured b is NOT the true branching factor of
the state space. It is still useful as a rough, problem-relative measure of
how much a heuristic prunes: comparing b for UCS vs. A* on the same board
quantifies the heuristic's effective reach. Node counts for Greedy and
Local Search are 0 because neither performs systematic successor
expansion (Greedy scans deterministically; Local Search mutates a plan),
so their b is reported as `n/a`.

## Analysis mode (all commands below are PowerShell-compatible)

The project can enumerate states and compare greedy performance against the optimal cost-based solver. It writes results to `analysis_output/`:

- CSV summary
- histogram of greedy-to-optimal ratios
- greedy-vs-optimal cost scatter plot
- optimal-plan-length vs. side-door action scatter plot

This is available from the CLI and the GUI.

## Special test case

The fixed board used for validation is:

```text
1 0
0 1
0 1
1 0
```

This board is accessible through the GUI using the Special case button or via:

```powershell
python problem.py --cli --special-case
```

## Example result

```text
DFS         : 24 openings, cost  64
BFS         :  7 openings, cost  47
IDS         :  7 openings, cost  47
UCS         : 10 openings, cost  34
A* (sand)   : 10 openings, cost  34
A* (column) : 10 openings, cost  34
Greedy      :  8 openings, cost  48
```

This demonstrates the difference between minimizing the number of actions and minimizing the weighted cost.

### CLI output and validation

Every CLI run prints the initial board, the selected algorithm, the number
of door openings, the weighted total cost, whether the goal state was
reached, the execution time, the node-expansion count, and the action
sequence. Invalid inputs are rejected with clear errors: algorithm names
must be one of the registered ones, `--rows`/`--cols` must be 1-12,
`--seed` non-negative, and `--sample` positive (analysis boards are
capped at 4x4).

## Notes

The main implementation is contained in `problem.py`, which keeps the solver logic and visualization in a single place for simplicity and portability.

## Repository name suggestion

`sand-door-puzzle-solver`

This name is descriptive, clear, and works well on GitHub.

## Benchmark script (`evaluate_boards.py`)

Evaluates UCS, A* (sand), A* (column), Greedy and Local Search on the
fixed special-case board and three seeded random boards, recording cost,
actions, type-A/type-B counts, expanded nodes, time, depth and the
effective branching factor. Writes `analysis_output/benchmark_results.csv`
and prints a summary table. All seeds are fixed and documented in the
script's docstring, so results are exactly reproducible.

Example output (special-case board, 4x2):

```text
board       algorithm       cost  act   A   B  nodes  depth     b*  time_s
special     UCS               34   10   7   3   3677    10  2.134  0.1341
special     A* (sand)         34   10   7   3   3611    10  2.129  0.1402
special     A* (column)       34   10   7   3   3484    10  2.121  0.1358
special     Greedy            48    8   8   0      0     8    n/a  0.0001
special     Local Search      47    7   7   0      0     7    n/a  0.0123
```

## Generated plots and CSV files

All generated artifacts live in `analysis_output/`:

| file | produced by | contents |
|------|-------------|----------|
| `results_<r>x<c>.csv` | `analysis.py` | per-state: board, opt cost, greedy cost, ratio, plan length, type-B count |
| `greedy_opt_ratio_histogram.png` | `analysis.py` | frequency histogram of greedy/optimal ratios |
| `plot1_greedy_vs_optimal.png` | `analysis.py` | scatter: greedy cost (x) vs. optimal cost (y) |
| `plot2_actions_vs_typeb.png` | `analysis.py` | scatter: optimal plan length (x) vs. type-B actions (y) |
| `benchmark_results.csv` | `evaluate_boards.py` | per board × algorithm measurements incl. nodes, time, effective b |

## Heuristic admissibility and consistency

Both A* heuristics are proven admissible and consistent in
[HEURISTIC.md](HEURISTIC.md). Short version: side doors can never fully
empty a column (they strand a half-unit in a HALF cell that cannot use
side doors again), so every sand-bearing column needs ≥ 1 bottom-row gate
opening (`heuristic_sand`), and additionally every non-bottom sand cell
needs ≥ 1 opening of its own gate (creating a join *is* that opening)
(`heuristic_column`). With an admissible + consistent heuristic, A* returns
cost-optimal plans — empirically confirmed: UCS, A* (sand) and A*
(column) report identical costs on all tested boards.

## Implementation summary (verified in this environment)

- 8 registered algorithms, all runnable through the CLI and GUI.
- `test_local_search.py`: 22 tests — **all pass** (environment edge cases,
  plan scoring, Local Search guarantees, join rules, cost formulas).
- `test_anim_smoke.py`: passes; UCS = A* costs on 12 seeded random boards.
- `analysis.py --rows 2 --cols 2`: 80 states analysed, 77.5% greedy =
  optimal, mean ratio 1.029, max 1.176; CSV + 3 PNGs written.
- `evaluate_boards.py`: 20 measurements written to CSV (see table above).

## Known limitations

- The exhaustive analysis enumerates **all** 3^(rows·cols) states, so it is
  practical only up to 4×4 boards (the CLI enforces this cap).
- IDS and DFS can exceed their node/depth limits (`SearchLimitExceeded`)
  on large open boards; UCS/A* remain complete.
- The effective branching factor assumes a uniform tree (see above) and is
  undefined (`n/a`) for Greedy and Local Search, which do not expand nodes.
- Local Search is a local optimum around Greedy; it is never worse than
  Greedy but usually not optimal (e.g. cost 47 vs. 34 on the special case).
- matplotlib is required only for the analysis plots; without it,
  `--analyze` prints an install hint instead of failing silently.
