"""Screenshot probe v2 - DPI aware, window parked at (0,0)."""
import os
os.environ["SANDBOX_SCRIPTED"] = "1"
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
import time
import tkinter as tk
from PIL import ImageGrab
from problem import run_gui, apply_action, FULL, HALF

def grab(canvas_widget, name):
    win = canvas_widget.winfo_toplevel()
    win.attributes("-topmost", True)
    win.geometry("+0+0")
    win.lift(); win.focus_force()
    canvas_widget.yview_moveto(0); canvas_widget.xview_moveto(0)
    canvas_widget.update()
    time.sleep(0.6)
    canvas_widget.update()
    x = canvas_widget.winfo_rootx()
    y = canvas_widget.winfo_rooty()
    img = ImageGrab.grab((x, y, x + canvas_widget.winfo_width(), y + canvas_widget.winfo_height()))
    img.save(name)
    print("saved", name, img.size, flush=True)

root = tk.Tk(); root._scripted = True
app = run_gui(3, 2, None)
root.update()

grid = ((FULL, 0), (HALF, 0), (0, 0))
world = apply_action(grid, 0, 0, "down")
app.anim_from = None
app.state = world
app.draw_board()
root.update()
grab(app.canvas, "fixed_joined.png")

grid_c = ((FULL, 0), (FULL, 0), (0, 0))
app.state = apply_action(grid_c, 0, 0, "down")
app.draw_board()
root.update()
grab(app.canvas, "fixed_fullrun.png")

root.destroy()
print("DONE", flush=True)
