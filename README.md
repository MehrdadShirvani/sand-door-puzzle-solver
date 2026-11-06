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

- 7 solving algorithms
  - DFS
  - BFS
  - IDS
  - UCS
  - A* with the sand-bearing-column heuristic
  - A* with the structural heuristic
  - Greedy scan strategy
- Random board generation with reproducible seeds
- Fixed special-case board for validation
- GUI and command-line modes
- Animated replay of the solution path
- Analysis output for comparing greedy and optimal strategies

## Project structure

- `problem.py` - main solver, GUI, and CLI
- `analysis.py` - exhaustive board analysis and plot generation
- `analysis_output/` - generated CSV and PNG analysis results

## Requirements

- Python 3.9 or newer
- Tkinter, which is included with standard Python installations on Windows
- No third-party packages are required for the core solver

Check your environment:

```powershell
python --version
python -c "import tkinter; print('Tkinter OK')"
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

# CLI with animation delay
python problem.py --cli --special-case --delay 0.3

# Custom random board size
python problem.py --cli --rows 4 --cols 4 --seed 7

# Exhaustive analysis
python problem.py --analyze --rows 2 --cols 2
python problem.py --analyze --rows 2 --cols 3 --sample 400
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
- A* (sand): informed but weaker heuristic
- A* (column): stronger structural heuristic
- Greedy: deterministic scan strategy, not globally optimal

## Analysis mode

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

## Notes

The main implementation is contained in `problem.py`, which keeps the solver logic and visualization in a single place for simplicity and portability.

## Repository name suggestion

`sand-door-puzzle-solver`

This name is descriptive, clear, and works well on GitHub.

