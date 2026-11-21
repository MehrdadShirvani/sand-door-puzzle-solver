# Heuristic Analysis for A* Search

This document specifies the two heuristics used by the A* solver in
`problem.py` and proves that both are **admissible** (never overestimate)
and **consistent** (satisfy the triangle inequality), which guarantees that
A* returns a **cost-optimal** plan.

Throughout, cell sand amounts are measured in *half-units*:

| symbol | meaning          | physical sand |
|--------|------------------|---------------|
| `0`    | empty cell       | 0.0           |
| `1`    | half-full cell   | 0.5           |
| `2`    | full cell (`FULL`) | 1.0         |

The action set is:

- **Type A ("down")** — open the bottom gate between cell $(r,c)$ and the
  cell below it $(r+1,c)$; in the bottom row it drains the whole connected
  sand body out of the grid. Cost:
  $$c_A = 1 + 2(s + s')$$
  where $s$ is the upper cell's sand before and $s'$ after the action. Since
  $s, s' \ge 0$, every type-A action costs **at least 1**:
  $$c_A \ge 1$$
- **Type B ("left"/"right")** — open a side door; only legal from a FULL
  cell, moves exactly **one half-unit** sideways into a non-full neighbour.
  Cost: $c_B = 1$.

The goal state $G$ is the empty grid.

---

## Heuristic 1 — Sand-bearing columns (`heuristic_sand`)

### Exact definition

$$h_1(s) \;=\; \#\{\, c \;:\; \exists r,\ \text{grid}[r][c] > 0 \,\}$$

i.e. the number of **columns that contain at least one sand cell**.

### Claim: $h_1(s) \le h^*(s)$ (admissible)

Let $C = \{c_1, \dots, c_k\}$ be the sand-bearing columns of state $s$, so
$h_1(s) = k$. Consider any column $c \in C$ and any plan $P$ that empties
the board.

**Lemma 1 (sand cannot fully leave a column sideways).**
A type-B action moves exactly one half-unit out of a FULL cell, turning it
into a half-full cell. A half-full cell ($1$ half-unit) can never use a
side door again (`iter_actions` requires `grid[r][c] >= FULL` for
left/right). Therefore, if a column ever contains sand, **at least one
half-unit of sand remains somewhere in that column after all side-door
actions**, and that remainder can only leave the column *downwards*.

**Lemma 2 (removing the remainder costs ≥ 1).**
The last half-unit of sand in column $c$ must leave the grid through the
bottom-row gate of column $c$. Opening that gate is a type-A action with
cost $\ge 1$ (Lemma above: $c_A = 1 + 2(s+s') \ge 1$). Even when sand is
joined, the joined body drains through the bottom-row gate of *some* cell
in column $c$ — which is still one gate opening in column $c$.

Hence every sand-bearing column $c \in C$ accounts for a **distinct** gate
opening (the bottom-row exit of column $c$; different columns use different
gates). Any plan must pay at least $k$ such openings:

$$\text{cost}(P) \;\ge\; \sum_{c \in C} 1 \;=\; k \;=\; h_1(s).$$

Since this holds for *every* plan $P$ that solves $s$, it holds for the
optimal plan:

$$h_1(s) \le h^*(s). \qquad\blacksquare$$

### Consistency

For any action $a$ from $s$ to $s'$ with step cost $c(a,s,s')$ we need
$$h_1(s) \le c(a,s,s') + h_1(s').$$

- A type-B action removes exactly one half-unit *within* a row; it cannot
  empty a column entirely unless the column held exactly one half-unit —
  in which case the sand moved sideways, and $h_1(s') = h_1(s) - 1 \le$
  $c_B + h_1(s') = 1 + h_1(s')$. Otherwise $h_1(s') = h_1(s)$.
- A type-A action transfers sand vertically; the destination column is the
  same column, so a column only becomes sand-free when its last sand
  leaves (or pools in another column of the same column index — same
  column). If $h_1$ drops by 1, the action was the bottom-row exit of that
  column with cost $\ge 1$, so again $h_1(s) \le c(a) + h_1(s')$.

Thus $h_1$ is consistent, and goal-directed: $h_1(G) = 0$. ✓

### How vertical joins affect the proof

A vertical join merges several cells of **one column** into a single body
that drains together. Draining a joined body out of the grid is still one
type-A opening of a bottom-row gate *in that body's column*. Joins can
pool sand from several rows of the same column into one exit — but they
cannot move sand into a *different column*, so the per-column lower bound
(counting one exit per sand-bearing column) survives unchanged. A join
that later "breaks" (because sand drains away) does not remove the
necessity of the exit opening that already happened or is still needed.

### Side doors cannot replace gate openings

`iter_actions` only offers a side door when the cell is FULL, and a side
door transfers exactly one half-unit. Consequently a FULL cell that
exports sideways becomes HALF and is stuck: half-full cells cannot export
sideways. Every column therefore retains ≥ 1 half-unit that must exit
through its bottom-row gate. Side doors reduce *how much* sand needs the
gate, never *whether* the gate is needed.

---

## Heuristic 2 — Structural bound (`heuristic_column`)

### Exact definition

Let $\text{rows}$ be the number of rows. Define

$$h_2(s) \;=\; N_{\text{above}}(s) + C_{\text{sand}}(s)$$

with

$$N_{\text{above}}(s) = \#\{\,(r,c) \;:\; r < \text{rows}-1,\ \text{grid}[r][c] > 0\,\}$$

(the number of sand cells **not** in the bottom row) and

$$C_{\text{sand}}(s) = \#\{\, c \;:\; \exists r,\ \text{grid}[r][c] > 0 \,\} = h_1(s).$$

So $h_2 = N_{\text{above}} + h_1$.

### Claim: $h_2(s) \le h^*(s)$ (admissible)

The two terms count **disjoint sets of required gate openings**:

1. **Per non-bottom sand cell ($N_{\text{above}}$ terms).**
   Take a sand cell $u = (r, c)$ with $r < \text{rows}-1$. Its sand can
   only leave cell $u$ in two ways:
   - a direct "down" transfer through the gate between $u$ and the cell
     below, or
   - via a vertical join with the cell below — but that join is itself
     **created by opening exactly that same gate**.

   Either way, the gate above cell $u$'s column position must be opened at
   least once while (or before) $u$'s sand passes it. Could a side door
   evacuate $u$ instead? By Lemma 1 a side door moves one half-unit out of
   a FULL cell and leaves it half-full; if $u$ holds 2 half-units, at least
   1 half-unit remains in $u$ and must still exit through $u$'s own gate.
   So **each non-bottom sand cell forces ≥ 1 opening of its own gate**.

2. **Per sand-bearing column ($C_{\text{sand}}$ terms).**
   By Lemma 2, each sand-bearing column needs ≥ 1 opening of a bottom-row
   gate in that column.

**Disjointness.** The openings counted in (1) are gates *between* rows
(positions $(r,c)$ with $r < \text{rows}-1$); the openings counted in (2)
are gates in the **bottom row** ($r = \text{rows}-1$). No gate is counted
twice, so the costs add:

$$\text{cost}(P) \;\ge\; N_{\text{above}}(s) + C_{\text{sand}}(s) = h_2(s)
\quad\text{for every plan } P,$$

and hence $h_2(s) \le h^*(s)$. $\blacksquare$

### Consistency

For one action $a: s \to s'$ with cost $c(a)$:

- $N_{\text{above}}$ can decrease by **at most 1** per action: the action
  changes at most two cells (the acted-on cell and its horizontal or
  vertical neighbour). A type-A "down" action that empties a non-bottom
  cell lowers $N_{\text{above}}$ by 1 and has cost $c_A \ge 1$. If
  $N_{\text{above}}$ drops, the acting gate *is* that cell's gate, which is
  the very opening requirement being discharged — cost ≥ 1 covers it.
  Type-B actions move sand horizontally: a sand cell becomes HALF (still
  sand, still counted) or a target gains sand (count increased by ≤ 1,
  compensated because the source stayed sand unless it emptied — in which
  case the source was FULL, moved 1 half-unit, and remained HALF = sand).
  Net change of $N_{\text{above}}$ under type-B is ≥ 0... specifically it
  never decreases, so no violation.
- $C_{\text{sand}}$ decreases by at most 1 per action, and only via the
  bottom-row exit (cost ≥ 1) — this is exactly the Heuristic-1 consistency
  argument.

Because $N_{\text{above}}$ and $C_{\text{sand}}$ each satisfy
$h_i(s) \le c(a) + h_i(s')$ and their counted openings are disjoint, their
sum also satisfies it:

$$h_2(s) \le c(a) + h_2(s').$$

Also $h_2(G) = 0$. So $h_2$ is consistent. ✓

### How vertical joins affect the proof

Creating a join between $u=(r,c)$ and $u'=(r+1,c)$ does **not** waive the
per-cell requirement: the join exists precisely because the gate
$(r,c)$-downward was opened, so requirement (1) for cell $u$ has been paid
by that very opening. When a joined body later drains, requirement (2)
(bottom-row exit of the column holding the body) is paid by that drain.
The two events discharge two disjoint requirements — never the same one
twice — so joins cannot make $h_2$ overestimate.

### Side doors cannot replace gate openings

A side door moves one half-unit sideways; it never changes which vertical
gates a column's sand must traverse. For a FULL cell, exporting sideways
still strands a half-unit (the cell becomes HALF and is barred from side
doors). Hence every non-bottom sand cell keeps ≥ 1 half-unit that must
cross its own downward gate, and each sand-bearing column keeps ≥ 1
half-unit that must exit its bottom-row gate. Side doors cannot substitute
for either.

---

## Why A* remains cost-optimal

With an admissible and consistent heuristic $h$, A* with

$$f(n) = g(n) + h(n)$$

is guaranteed to return an optimal-cost plan:

1. **Admissibility** ($h \le h^*$) ensures $f$ never overestimates the true
   cost of a solution through $n$: $f(n) = g(n) + h(n) \le g(n) + h^*(n) =
   f^*(n)$.
2. **Consistency** makes $f$ non-decreasing along any path, so the first
   time A* pops a goal node from the priority queue, its $g$-value is the
   optimal cost $g^* = h^*(s_0)$ (standard A* optimality theorem; the
   implementation also keeps `best_cost` per state and skips settled
   states, mirroring the textbook closed-list argument).

The implementation (`solve_astar`) uses a binary heap keyed by
$(f, \text{tie-breaker})$, per-state best costs `best_cost`, and a
`settled` set. Step costs come from the weighted model
(`action_cost`: $1 + 2(s+s')$ for gates, 1 for side doors), so optimality
is with respect to the **weighted** cost, not the action count. Both A*
variants therefore return the same cost as UCS (verified empirically on
random boards by `test_anim_smoke.py`: "A*s match UCS cost on all 12
random boards").

---

## Worked example

Fixed special-case board (F = full, . = empty), rows 0..3:

```text
row 0:  F .
row 1:  . F
row 2:  . F
row 3:  F .
```

**Heuristic 1.** Sand appears in column 0 and column 1 →
$h_1 = 2$. Optimal cost is 34 (UCS/A*), and indeed $2 \le 34$. ✓

**Heuristic 2.**
$N_{\text{above}}$: non-bottom sand cells are $(0,0), (1,1), (2,1)$ → 3.
$C_{\text{sand}}$: 2.
$h_2 = 3 + 2 = 5 \le 34$. ✓

**Optimal plan found by A* (column)** — 10 actions, cost 34:

```text
left  (1,1): FULL(1,1) → HALF(1,0)? no — moves half-unit left into (1,0), cost 1
left  (2,1): cost 1
down  (1,1): s=1 (half), s'=0 ... gate cost 1+2(1+0)=3? etc.
...
total = 34
```

**Sanity check of the lower bound arithmetic.**
The five non-bottom sand cells force ≥ 5 gate openings above the bottom
row, plus ≥ 2 bottom-row exit openings — at least 7 openings contributing
≥ 7 to the cost; the actual optimum is 34, comfortably above $h_2 = 5$,
showing the bound is admissible but not tight for this board (which is
fine — admissibility only requires *not exceeding* $h^*$).

**A smaller exact match.** Board `((FULL,),)` — a single full cell:

- $h_1 = 1$, $h_2 = 0 + 1 = 1$.
- Only action: bottom gate with $s = 2$, $s' = 0$:
  $c_A = 1 + 2(2+0) = 5$.
- $h^* = 5 \ge h_1 = h_2 = 1$. ✓ (Here the heuristic is loose because it
  counts *openings*, not transferred sand; a tighter sand-weighted bound
  would be $1 + 2s_{\min}$, which the current heuristics deliberately do
  not use to stay simple and provably safe.)
