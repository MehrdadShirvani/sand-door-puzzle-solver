# Step-by-step implementation prompts — Genetic Algorithm for the Sand Door Puzzle

These prompts turn the professor's requirements into a staged implementation plan.
Give them to the assistant **one at a time, in order**; each step builds on the
previous one and ends with something runnable/verifiable.

## Professor's notes (translated and mapped to the design)

| Note | Design decision |
|------|-----------------|
| هر استیت یه دنباله از اکشن‌ها از اول تا اون لحظه است | Every state IS a sequence of actions from the start up to that moment — the GA does not search states, it searches **plans** |
| طول کروموزوم‌ها باید فیکس باشه | Chromosomes have a **fixed length** (padding/truncation handled explicitly) |
| goal test + cost باید دوباره نوشته بشن | Goal test and cost are **re-implemented** for the GA (plan-based, not state-based) |
| تابعی به اسم value function / fitness — عدد خروجی بده که اون دنباله از اکشن‌ها چقدر موفق هست | A `value function`/`fitness` function takes a plan and returns one number = how successful that plan is |
| به طور هیوریستیک هر استیت از گول استیت رو بسنجه | Fitness must **heuristically measure how close a state is to the goal state** (not only final cost) |
| Fitness(seq of actions) -> big constant − conflict − path cost | Fitness formula: `LARGE − conflict penalty − path cost` |
| crossover / mutation: on one DNA / cross-over 2 parents -> 2 children | Mutation acts on one chromosome; crossover takes 2 parents and produces 2 children |
| sequence of actions -> population size /100 -> 50 | Population is initialized from random sequences of actions, population size ~50–100 |
| Darwinian | Fitness is the only thing evaluated — no phenotype/simulation Lamarckian shortcut; only good **genotypes** (plans) survive |
| Selection: deterministic / stochastic | Implement **both** selection modes (e.g. rank/tournament = deterministic, roulette = stochastic) and make it switchable |

---

## Prompt 1 — Chromosome representation and fixed-length plans

> In `problem.py`'s sand-door puzzle, implement a chromosome model for a
> Genetic Algorithm. Reminder of the key fact: **each state is the sequence of
> actions applied from the initial board up to that moment.**
>
> 1. A chromosome (DNA) is a fixed-length tuple/list of actions. Use the
>    existing `Action = (row, col, direction)` encoding and the existing
>    `iter_actions(state)` to know which actions are legal at each point.
> 2. Define `MAX_LEN` = `2 * rows * cols` (justified: every sand cell needs at
>    most a few openings to leave the grid).
> 3. Implement:
>    - `random_chromosome(initial_state, rng)` — build a fixed-length plan by
>      repeatedly picking a **random valid** successor action
>      (`successors()`-style); if the board becomes empty early, keep filling
>      the rest with a filler gene (`NOOP = None`) so the length is FIXED.
>    - a repair/filler rule: genes that are illegal or no-op in the state
>      reached so far are treated as fillers (skipped, zero cost) — do NOT
>      crash on them.
> 4. Implement `state_after(initial_state, dna)` — the state reached by
>    applying the plan, stopping cleanly at the first illegal gene (fillers
>    consumed after that too).
> 5. Unit-test-able invariants: all chromosomes have exactly `MAX_LEN` genes;
>    `random_chromosome` never mutates the state in place; a chromosome of all
>    fillers scores as an incomplete plan (not an exception).

## Prompt 2 — Re-written goal test and cost (plan-based)

> As the professor required, **re-write the goal test and the cost** so they
> operate on a chromosome rather than on single search states:
>
> 1. `ga_goal_test(initial_state, dna) -> bool` — True iff applying the whole
>    plan reaches the empty-board goal. This is separate from the internal
>    `is_empty_state` used by the classical searchers, because it must handle
>    filler genes and truncated/illegal genes gracefully.
> 2. `ga_path_cost(initial_state, dna) -> int` — sum of the existing weighted
>    action costs (`action_cost`) over the *effective* prefix of the plan
>    (up to where the plan stops being legal or reaches the goal); fillers
>    contribute 0.
> 3. Both must reuse the puzzle's real physics (`apply_action`) so GA plans
>    are validated with exactly the same rules as UCS/A* plans.
> 4. Verify on the fixed special-case board: an empty DNA fails the goal test,
>    the UCS plan (padded to MAX_LEN with fillers) passes the goal test and its
>    `ga_path_cost` equals the known optimal cost 34.

## Prompt 3 — The value function (fitness)

> Implement the fitness / **value function** the professor specified. It takes
> a sequence of actions and returns ONE number: how successful that plan is.
>
> 1. Signature: `fitness(initial_state, dna) -> float`.
> 2. Formula (exactly as the professor wrote it):
>
>        fitness = LARGE_CONSTANT
>                - conflict_penalty(dna)
>                - path_cost_component
>
>    - `LARGE_CONSTANT` big enough that fitness is always positive (e.g.
>      `1000 * MAX_LEN + 1000`).
>    - `conflict_penalty` — penalizes illegal/no-op genes, i.e. every place
>      the plan conflicts with the puzzle rules: count of skipped/invalid
>      genes times a penalty weight (e.g. 50 each).
>    - `path_cost_component` — `ga_path_cost` **plus a heuristic term that
>      estimates how far the resulting state still is from the goal state**:
>      reuse the admissible `heuristic_column(state)` (N_above + C_sand)
>      multiplied by a weight (e.g. 10), so plans that end closer to the
>      empty board score higher even when incomplete.
> 3. A complete, valid, optimal plan must beat every incomplete plan — check
>    that ordering explicitly: `fitness(UCS plan) > fitness(random plan)` on
>    several seeded boards, and `fitness` never returns a negative number.
> 4. Document why the heuristic-to-goal term is needed: with only path cost,
>    two incomplete plans of the same cost are indistinguishable and the GA
>    gets no gradient toward the goal.

## Prompt 4 — Population initialization

> Initialize the GA population from random **sequences of actions**, with
> population size 100 (configurable; the professor mentioned "population size
> / 100 -> 50", so make it a parameter and default to 50 for speed).
>
> 1. `initialize_population(initial_state, size, rng)` — `size` independent
>    random chromosomes, each generated by Prompt 1's `random_chromosome`.
>    "Each tries to solve independently": diversity comes from independent
>    random walks, so re-use the seeded `rng` for reproducibility.
> 2. Seed a fraction (e.g. 2 of `size`, parameter `elitist_seeds`) with the
>    Greedy plan and a Greedy-derived shuffled plan — a big head start, while
>    keeping the population predominantly random for Darwinian selection.
> 3. Print/return a fitness histogram of generation 0 (min / max / mean /
>    best plan) so we can see the starting spread.

## Prompt 5 — Mutation and crossover (genetic operators)

> Implement the two genetic operators, following the professor's structure:
>
> 1. **Mutation — acts on ONE DNA** (`mutate(dna, rng, rate)`): with
>    probability `rate` per gene, replace a gene with another action valid at
>    that point (re-simulate from the start up to that gene using
>    `state_after`), or turn a gene into a filler, or swap two adjacent genes.
>    Fixed length is never changed.
> 2. **Crossover — 2 parents -> 2 children** (`crossover(parent_a, parent_b,
>    rng)`): single-point or two-point cut (random), producing exactly TWO
>    children; both children keep the fixed length. Explain why single-point
>    fits action sequences (prefix of parent A + suffix of parent B is itself
>    a plausible plan skeleton).
> 3. Because action-sequence genes are position-dependent (an action's
>    legality depends on everything before it), children may contain conflicts
>    — that is fine: they are handled by the fitness function's conflict
>    penalty (Prompt 3), NOT by rejecting children (Darwinian: let selection
>    do the work).
> 4. Sanity tests: mutated/crossover children still have length MAX_LEN;
>    `fitness` on 100 random children never throws.

## Prompt 6 — Selection: deterministic and stochastic

> Implement BOTH selection schemes the professor listed, behind one switch:
>
> 1. `select_parents(population, fitnesses, mode, rng, k)` where
>    `mode in {"deterministic", "stochastic"}`.
>    - **Deterministic**: rank-based / truncation — sort by fitness, take the
>      top individuals deterministically (elitism: the best E always survive
>      unchanged into the next generation).
>    - **Stochastic**: roulette-wheel (fitness-proportionate) and/or
>      tournament — probability driven by `rng`, still biased toward high
>      fitness.
> 2. Elitism parameter `elite_count` (default 2): best chromosomes are copied
>    to the next generation unmutated — guarantees the GA never regresses.
> 3. Keep the selection function pure (no simulation inside selection —
>    fitness values are precomputed for the whole population; this is the
>    Darwinian discipline: evaluate, then select).

## Prompt 7 — The GA loop, CLI and GUI integration

> Assemble the full Genetic Algorithm solver:
>
> 1. `solve_genetic(initial_state, population_size=50, generations=200,
>    mutation_rate=0.08, elite_count=2, selection="deterministic", seed=None)`
>    — generation loop: evaluate fitness of all chromosomes -> select ->
>    crossover (pairs -> 2 children) -> mutate -> elitism -> repeat.
>    Termination: goal reached (fitness hits the perfect-plan ceiling) or
>    `generations` exhausted; always return the BEST valid complete plan
>    found (re-validated with `path_score`).
> 2. Register it as `"Genetic"` in `ALGORITHMS`/`SOLVERS` so it appears in the
>    GUI dropdown and `--algo Genetic` works in the CLI (the Local Search
>    pattern — taking `rng`/parameters — is the template).
> 3. Add CLI flags `--ga-pop`, `--ga-generations`, `--ga-mutation`,
>    `--ga-selection {deterministic,stochastic}` (all with defaults), and
>    print per-generation progress lines (best/mean fitness, best cost,
>    conflicts) plus a final summary: openings, weighted cost, goal reached,
>    time, generations used.
> 4. Guarantee: if the GA fails to find a complete plan within the budget,
>    fall back to the Greedy plan (like Local Search does) instead of
>    returning an incomplete chromosome.

## Prompt 8 — Verification and benchmarking

> Verify the GA and add it to the project's measurement pipeline:
>
> 1. Extend `test_local_search.py` (or a new `test_genetic.py`) with: fixed
>    chromosome length invariant; goal test / cost correctness vs UCS on the
>    special case; fitness ordering (optimal > random); GA reaches cost
>    comparable to Greedy or better on the special case and seeded random
>    boards; determinism with a fixed seed; both selection modes run.
> 2. Run the existing suite (`python -m unittest test_local_search -v`) to
>    prove no regression in the classical solvers.
> 3. Add `"Genetic"` to `evaluate_boards.py`'s ALGOS so the benchmark CSV
>    gains GA rows (cost, actions, A/B counts, time; expanded nodes stays 0
>    or counts fitness evaluations as the node counter).
> 4. Report a short comparison table on the special case: UCS/A* (cost 34),
>    Greedy (48), Local Search (47), GA (whatever it reaches) — and note in
>    the README which selection mode worked better and why.

---

### Order of execution

1 → 2 → 3 are the foundation (representation, re-written goal/cost, fitness).
4 → 5 → 6 are the GA machinery (population, operators, selection).
7 integrates everything, 8 proves it. Each prompt lists its own acceptance
checks, so you can verify one step before asking for the next.
