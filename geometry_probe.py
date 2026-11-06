"""Headless verification of draw_board geometry via canvas item inspection.

No screen capture involved: we draw known worlds and check the actual canvas
items (rectangles/lines/texts) so the assertions can't be fooled by window
management, DPI scaling, or overlapping windows.
"""
import os
os.environ["SANDBOX_SCRIPTED"] = "1"
import tkinter as tk
from problem import run_gui, apply_action, unpack, FULL, HALF

root = tk.Tk(); root._scripted = True
app = run_gui(3, 2, None)
canvas = app.canvas
CELL = 76
MARGIN = 6

def items():
    out = []
    for i in canvas.find_all():
        out.append((canvas.type(i), canvas.coords(i), canvas.itemcget(i, "fill")))
    return out

def sand_rects():
    return [(c, xy) for t, xy, c in items()
            if t == "rectangle" and c in ("#eab308", "#b45309") and len(xy) == 4]

def failures(msgs):
    for m in msgs:
        print("FAIL:", m)
    return not msgs

# ---------------------------------------------------------------- case A
# FULL over HALF, joined: pooled sand = 3 half-units in capacity 4 -> 75%
grid = ((FULL, 0), (HALF, 0), (0, 0))
world = apply_action(grid, 0, 0, "down")     # upper keeps HALF, lower FULL, joined
app.anim_from = None
app.state = world
app.draw_board()
canvas.update()

g, joins = unpack(world)
assert joins == {(0, 0)}, joins

rects = sand_rects()
msgs = []
if len(rects) != 1:
    msgs.append(f"expected exactly 1 pooled sand rect, got {len(rects)}")
else:
    (_c, (x1, y1, x2, y2)) = rects[0]
    # run spans rows 0..1: cy1 = 6, cy2 = 2*76-6 = 146
    run_top, run_bot = 6, 146
    # 75% of inner height (144-8=136) = 102 -> top = 144-102 = 42
    expected_h = (run_bot - 2 - (run_top + 2)) * 0.75
    if abs((y2 - y1) - expected_h) > 3:
        msgs.append(f"sand height {y2 - y1:.0f} != expected {expected_h:.0f}")
    if abs(y1 - (run_bot - 2 - expected_h)) > 3:
        msgs.append(f"sand top {y1} != {run_bot - 2 - expected_h:.0f} (pooled height wrong)")
    # sand must stay INSIDE the tank horizontally
    if x1 < 8 or x2 > 2 * CELL - 8:
        msgs.append(f"sand rect {(x1, y1, x2, y2)} exceeds tank horizontally")
print("case A (pooled 3/4 run):", "OK" if failures(msgs) else "FAILED")

# blue connector line at the join boundary (y = 76 - 6 = 70)
lines = [(xy, c) for t, xy, c in items() if t == "line" and c == "#0ea5e9"]
join_lines = [xy for xy, c in lines if abs(xy[1] - 70) < 2 and abs(xy[3] - 70) < 2]
assert join_lines, f"no blue connector at join boundary y=70: {lines}"
print("case A join connector at y=70: OK")

# ---------------------------------------------------------------- case B
# FULL over FULL joined: pooled sand fills the whole run, sand <= tank
grid = ((FULL, 0), (FULL, 0), (0, 0))
world = apply_action(grid, 0, 0, "down")
app.anim_from = None
app.state = world
app.draw_board()
canvas.update()

rects = sand_rects()
msgs = []
if len(rects) != 1:
    msgs.append(f"expected 1 pooled rect, got {len(rects)}")
else:
    (_c, (x1, y1, x2, y2)) = rects[0]
    run_top, run_bot = 6, 146
    if y1 < run_top + 1:
        msgs.append(f"sand overflows tank top: y1={y1} < {run_top}")
    if abs(y2 - (run_bot - 2)) > 2:
        msgs.append(f"sand bottom {y2} wrong")
print("case B (full 4/4 run):", "OK" if failures(msgs) else "FAILED")

# ---------------------------------------------------------------- case C
# mid-tween: from unjoined FULL-over-HALF to joined HALF-over-FULL, t=0.5
grid_from = ((FULL, 0), (HALF, 0), (0, 0))
world_to = apply_action(grid_from, 0, 0, "down")
app.anim_from = grid_from
app.state = world_to
app.draw_board((0, 0, "down"), 0.5)
canvas.update()

# interpolated levels: cell0: 2 -> 1 => 1.5 ; cell1: 1 -> 2 => 1.5 ; total 3.0
rects = sand_rects()
msgs = []
if len(rects) != 1:
    msgs.append(f"mid-tween should still pool into 1 rect, got {len(rects)}")
else:
    (_c, (x1, y1, x2, y2)) = rects[0]
    run_top, run_bot = 6, 146
    # run during tween considered joined (prev join at t<0.5? t=0.5 uses current joins)
    expected_h = (run_bot - 2 - (run_top + 2)) * 0.75
    if abs((y2 - y1) - expected_h) > 4:
        msgs.append(f"mid-tween sand height {y2 - y1:.0f} != {expected_h:.0f}")
    if y1 < run_top:
        msgs.append(f"mid-tween sand overflows top: {y1}")
print("case C (mid-tween pooled):", "OK" if failures(msgs) else "FAILED")

# ---------------------------------------------------------------- case D
# no joins: each cell is its own tank; HALF cell fill = 50% of its tank
grid = ((HALF, 0), (0, 0), (0, 0))
app.anim_from = None
app.state = grid
app.draw_board()
canvas.update()
rects = sand_rects()
msgs = []
if len(rects) != 1:
    msgs.append(f"expected 1 sand rect, got {len(rects)}")
else:
    (_c, (x1, y1, x2, y2)) = rects[0]
    # single cell row 0: cy1=6, cy2=76-6=70; inner 8..68, 50% -> h=30, y1=38
    if abs((y2 - y1) - 30) > 2:
        msgs.append(f"half cell fill height {y2 - y1:.0f} != 30")
    if abs(y2 - 68) > 2:
        msgs.append(f"half cell fill bottom {y2} != 68")
print("case D (single half cell):", "OK" if failures(msgs) else "FAILED")

root.destroy()
print("ALL GEOMETRY CHECKS PASSED", flush=True)
