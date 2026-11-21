"""Benchmark the puzzle solvers on fixed boards and the special test case.

For every (board, algorithm) pair, records:

  weighted solution cost, number of actions, number of type-A (bottom gate)
  and type-B (side door) actions, expanded nodes, execution time, solution
  depth and the effective branching factor.

Results are written to analysis_output/benchmark_results.csv and a concise
summary table is printed.  Every board below is generated from a FIXED seed,
so the whole experiment is reproducible:

  python evaluate_boards.py

Board configuration (documented for reproduction):

  board id      size   seed   generator
  ------------  -----  -------------------------------
  special       4x2    -      special_case_state()  (fixed hand-made grid)
  random-3x3    3x3    42     generate_random_state(rng=Random(42))
  random-3x4    3x4    7      generate_random_state(rng=Random(7))
  random-4x3    4x3    123    generate_random_state(rng=Random(123))

Algorithms evaluated: UCS, A* (sand), A* (column), Greedy, Local Search.
(Local Search uses seed=7, iterations=25.)
"""

from __future__ import annotations

import csv
import os
import random
import time

import problem as p

OUT_DIR = "analysis_output"
ALGOS = ["UCS", "A* (sand)", "A* (column)", "Greedy", "Local Search"]
LOCAL_SEARCH_KWARGS = {"iterations": 25, "seed": 7}


def make_boards():
    return [
        ("special", p.special_case_state()),
        ("random-3x3", p.generate_random_state(3, 3, rng=random.Random(42))),
        ("random-3x4", p.generate_random_state(3, 4, rng=random.Random(7))),
        ("random-4x3", p.generate_random_state(4, 3, rng=random.Random(123))),
    ]


def run_one(algorithm: str, board) -> dict:
    counter = {"n": 0}
    original = p.successors

    def counting(state):
        counter["n"] += 1
        return original(state)

    p.successors = counting
    try:
        started = time.perf_counter()
        if algorithm == "Local Search":
            actions = p.solve_local_search(board, **LOCAL_SEARCH_KWARGS)
        else:
            actions = p.solve(algorithm, board)
        elapsed = time.perf_counter() - started
    finally:
        p.successors = original

    cost = p.path_cost(board, actions)
    n_type_a = sum(1 for a in actions if a[2] == "down")
    rows = len(board)
    cols = len(board[0])
    ebf = p.effective_branching_factor(counter["n"], len(actions))
    return {
        "board_rows": rows,
        "board_cols": cols,
        "algorithm": algorithm,
        "cost": cost,
        "actions": len(actions),
        "type_a": n_type_a,
        "type_b": len(actions) - n_type_a,
        "expanded_nodes": counter["n"],
        "time_s": round(elapsed, 4),
        "depth": len(actions),
        "eff_bf": "" if ebf is None else f"{ebf:.3f}",
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    records = []
    for board_id, board in make_boards():
        for algorithm in ALGOS:
            record = run_one(algorithm, board)
            record = {"board": board_id, **record}
            records.append(record)

    csv_path = os.path.join(OUT_DIR, "benchmark_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    # Concise summary table.
    header = (
        f"{'board':<12}{'algorithm':<14}{'cost':>6}{'act':>5}{'A':>4}{'B':>4}"
        f"{'nodes':>8}{'depth':>7}{'b*':>8}{'time_s':>9}"
    )
    print(header)
    print("-" * len(header))
    for r in records:
        print(
            f"{r['board']:<12}{r['algorithm']:<14}{r['cost']:>6}{r['actions']:>5}"
            f"{r['type_a']:>4}{r['type_b']:>4}{r['expanded_nodes']:>8}"
            f"{r['depth']:>7}{r['eff_bf']:>8}{r['time_s']:>9}"
        )
    print(f"\nCSV written to {csv_path}")


if __name__ == "__main__":
    main()
