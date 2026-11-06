import random
from problem import ALGORITHMS, generate_random_state, solve, path_cost, apply_action, is_empty_state

rng = random.Random(123)
costs = {a: [] for a in ALGORITHMS}
for trial in range(12):
    rows, cols = rng.choice([(3, 3), (4, 3), (3, 4)])
    grid = generate_random_state(rows, cols, rng=rng)
    for algo in ("UCS", "A* (sand)", "A* (column)"):
        actions = solve(algo, grid)
        costs[algo].append(path_cost(grid, actions))
        state = grid
        for a in actions:
            state = apply_action(state, *a)
        assert is_empty_state(state), f"{algo} invalid on {grid}"
assert costs["UCS"] == costs["A* (sand)"] == costs["A* (column)"], costs
print("UCS ==", costs["UCS"])
print("A*s match UCS cost on all 12 random boards.")

# Smoke-check the GUI tween math headlessly (no Tk window opened):
from problem import unpack, FULL, HALF
grid = ((FULL, 0), (HALF, 0))
joined = apply_action(grid, 0, 0, "down")
g, j = unpack(joined)
assert (0, 0) in j
print("join still created ->", g, sorted(j))
