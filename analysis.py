"""Exhaustive analysis of the sand-door puzzle.

Enumerates EVERY possible initial state of an r x c board (each cell one of
empty / half / full), computes for each state:

  - the optimal cost (via the A* / UCS solver, cost-optimal by construction)
  - the Greedy strategy's cost
  - Greedy_opt_ratio = greedy cost / optimal cost
  - the number of actions of the optimal plan and how many of them are
    type-B (side door) openings

and produces:

  1. a frequency histogram of Greedy_opt_ratio
  2. Plot 1: scatter, x = greedy cost, y = optimal cost
  3. Plot 2: scatter, x = number of actions to the goal (optimal plan length),
             y = number of type-B actions in the optimal plan

Outputs land in analysis_output/ as PNG files plus a CSV of the raw data.

Usage:
    python analysis.py [--rows 2] [--cols 2] [--sample N]
"""

from __future__ import annotations

import argparse
import csv
import itertools
import os
import sys
from typing import Iterable, List, Tuple

from problem import (
    apply_action,
    is_empty_state,
    path_cost,
    solve_astar,
    solve_greedy,
    total_sand,
)

OUT_DIR = "analysis_output"


def all_states(rows: int, cols: int) -> Iterable[Tuple[Tuple[int, ...], ...]]:
    """Every possible initial board: each cell independently 0, 1 or 2."""
    for values in itertools.product((0, 1, 2), repeat=rows * cols):
        yield tuple(
            tuple(values[r * cols + c] for c in range(cols)) for r in range(rows)
        )


def count_type_b(actions) -> int:
    """Number of side-door (type-B) openings in a plan."""
    return sum(1 for _r, _c, direction in actions if direction != "down")


def analyse(rows: int, cols: int, limit: int | None = None, seed: int | None = None):
    import random

    states = list(all_states(rows, cols))
    if limit is not None and limit < len(states):
        rng = random.Random(seed)
        states = rng.sample(states, limit)
        states.sort()

    print(f"Analysing {len(states)} initial states of a {rows}x{cols} board...")

    results = []
    skipped = 0
    for index, state in enumerate(states):
        if is_empty_state(state):
            continue  # trivial: already at the goal
        try:
            optimal_actions = solve_astar(state, lambda s: total_sand(s))
            greedy_actions = solve_greedy(state)
        except Exception:
            skipped += 1
            continue
        opt_cost = path_cost(state, optimal_actions)
        greedy_cost = path_cost(state, greedy_actions)
        results.append(
            {
                "state": ";".join(",".join(str(v) for v in row) for row in state),
                "opt_cost": opt_cost,
                "greedy_cost": greedy_cost,
                "greedy_opt_ratio": (greedy_cost / opt_cost) if opt_cost else 1.0,
                "opt_actions": len(optimal_actions),
                "opt_type_b": count_type_b(optimal_actions),
                "greedy_actions": len(greedy_actions),
            }
        )
        if (index + 1) % 500 == 0:
            print(f"  ... {index + 1}/{len(states)} done", flush=True)

    print(f"Analysed {len(results)} solvable states ({skipped} skipped).")
    return results


def save_csv(results, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"CSV written to {path}")


def make_plots(results, out_dir: str) -> None:
    import matplotlib

    matplotlib.use("Agg")  # headless: write PNGs, no window
    import matplotlib.pyplot as plt

    ratios = [r["greedy_opt_ratio"] for r in results]

    # --- 1. histogram of Greedy_opt_ratio ---
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(ratios, bins=30, color="#b45309", edgecolor="#334155")
    ax.set_xlabel("Greedy_opt_ratio = greedy cost / optimal cost")
    ax.set_ylabel("frequency")
    ax.set_title(f"Distribution of Greedy_opt_ratio (n = {len(ratios)})")
    fig.tight_layout()
    hist_path = os.path.join(out_dir, "greedy_opt_ratio_histogram.png")
    fig.savefig(hist_path, dpi=150)
    plt.close(fig)
    print(f"Histogram written to {hist_path}")

    # --- 2. Plot 1: x = greedy cost, y = optimal cost ---
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(
        [r["greedy_cost"] for r in results],
        [r["opt_cost"] for r in results],
        s=14, alpha=0.55, color="#0ea5e9", edgecolors="none",
    )
    lo = min(min(r["opt_cost"] for r in results), min(r["greedy_cost"] for r in results))
    hi = max(max(r["opt_cost"] for r in results), max(r["greedy_cost"] for r in results))
    ax.plot([lo, hi], [lo, hi], color="#334155", linewidth=1, linestyle="--",
            label="y = x (optimal = greedy)")
    ax.set_xlabel("cost by greedy solution")
    ax.set_ylabel("optimum cost")
    ax.set_title("Plot 1: greedy cost vs. optimal cost")
    ax.legend()
    fig.tight_layout()
    p1_path = os.path.join(out_dir, "plot1_greedy_vs_optimal.png")
    fig.savefig(p1_path, dpi=150)
    plt.close(fig)
    print(f"Plot 1 written to {p1_path}")

    # --- 3. Plot 2: x = actions to goal, y = type-B actions (optimal plan) ---
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(
        [r["opt_actions"] for r in results],
        [r["opt_type_b"] for r in results],
        s=14, alpha=0.55, color="#eab308", edgecolors="none",
    )
    ax.set_xlabel("number of actions to goal state (optimal plan length)")
    ax.set_ylabel("number of type-B actions in the optimal plan")
    ax.set_title("Plot 2: optimal plan length vs. type-B (side door) actions")
    fig.tight_layout()
    p2_path = os.path.join(out_dir, "plot2_actions_vs_typeb.png")
    fig.savefig(p2_path, dpi=150)
    plt.close(fig)
    print(f"Plot 2 written to {p2_path}")


def print_summary(results) -> None:
    ratios = [r["greedy_opt_ratio"] for r in results]
    worst = max(results, key=lambda r: r["greedy_opt_ratio"])
    exact = sum(1 for x in ratios if abs(x - 1.0) < 1e-9)
    print("\n=== Summary ===")
    print(f"states analysed       : {len(results)}")
    print(f"greedy == optimal     : {exact} ({100 * exact / len(results):.1f}%)")
    print(f"mean ratio            : {sum(ratios) / len(ratios):.3f}")
    print(f"max ratio             : {max(ratios):.3f}")
    print(f"worst state           : {worst['state']} "
          f"(greedy {worst['greedy_cost']} vs optimal {worst['opt_cost']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=2, help="board rows (default 2)")
    parser.add_argument("--cols", type=int, default=2, help="board cols (default 2)")
    parser.add_argument("--sample", type=int, default=None,
                        help="analyse a random sample of N states instead of all")
    parser.add_argument("--seed", type=int, default=0, help="sample seed")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    results = analyse(args.rows, args.cols, limit=args.sample, seed=args.seed)
    if not results:
        print("No results - nothing to plot.")
        return

    csv_path = os.path.join(OUT_DIR, f"results_{args.rows}x{args.cols}.csv")
    save_csv(results, csv_path)
    make_plots(results, OUT_DIR)
    print_summary(results)


if __name__ == "__main__":
    main()
