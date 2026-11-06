"""Render the canvas items into a PNG using PIL, straight from find_all().

No screen capture, no DPI issues: we read the exact items draw_board created
and re-draw them into an image. What you see is literally what Tk drew.
"""
import os
os.environ["SANDBOX_SCRIPTED"] = "1"
import tkinter as tk
from PIL import Image, ImageDraw
from problem import run_gui, apply_action, unpack, FULL, HALF

SS = 3  # supersample factor for crisp output

def render_canvas(canvas, name):
    w = int(canvas.winfo_width()); h = int(canvas.winfo_height())
    img = Image.new("RGB", (w * SS, h * SS), "white")
    dr = ImageDraw.Draw(img)
    for i in canvas.find_all():
        typ = canvas.type(i)
        xy = canvas.coords(i)
        fill = canvas.itemcget(i, "fill")
        width = int(float(canvas.itemcget(i, "width") or 1))
        xy = [v * SS for v in xy]
        if typ == "rectangle":
            dr.rectangle(xy, fill=fill, outline=fill if fill != "" else None)
        elif typ == "line":
            dr.line(xy, fill=fill, width=width * SS)
        elif typ == "text":
            dr.text((xy[0], xy[1]), canvas.itemcget(i, "text"),
                    fill=fill, anchor="mm")
    img = img.resize((w, h), Image.LANCZOS)
    img.save(name)
    print("rendered", name, flush=True)

root = tk.Tk(); root._scripted = True
app = run_gui(3, 2, None)
canvas = app.canvas
canvas.update()

# Case A: FULL joined over HALF -> pooled sand, 3/4 of the 2-cell run
grid = ((FULL, 0), (HALF, 0), (0, 0))
app.anim_from = None
app.state = apply_action(grid, 0, 0, "down")
app.draw_board()
canvas.update()
render_canvas(canvas, "renderA_pooled.png")

# Case B: FULL joined over FULL -> one full tank
grid_c = ((FULL, 0), (FULL, 0), (0, 0))
app.state = apply_action(grid_c, 0, 0, "down")
app.draw_board()
canvas.update()
render_canvas(canvas, "renderB_fullrun.png")

# Case C: mid-tween from unjoined to joined (t=0.5)
app.anim_from = grid
app.state = apply_action(grid, 0, 0, "down")
app.draw_board((0, 0, "down"), 0.5)
canvas.update()
render_canvas(canvas, "renderC_midtween.png")
app.anim_from = None

root.destroy()
print("DONE", flush=True)
