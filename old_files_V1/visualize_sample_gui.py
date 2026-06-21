import ast
import math
import tkinter as tk
from tkinter import messagebox

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Circle, Rectangle, Ellipse



# Geometry definition
PLATE_SIZE = 60.0
HALF = PLATE_SIZE / 2.0
MIN_COORD = 0.0
MAX_COORD = PLATE_SIZE

r1 = 9.0
r2 = 6.0
a = 25.0 / 2.0   # semi-axis for the elongated/oval cutout
b = 7.5          # radius / semi-minor axis


def parse_sample(text):
    """
    Accepts either:
    {'x1': ..., 'y1': ..., ...}
    or:
    'x1': ..., 'y1': ..., ...
    """
    text = text.strip()

    if not text:
        raise ValueError("Input is empty.")

    if not text.startswith("{"):
        text = "{" + text + "}"

    sample = ast.literal_eval(text)

    required = ["x1", "y1", "x2", "y2", "x3", "y3", "angle"]
    missing = [k for k in required if k not in sample]
    if missing:
        raise ValueError(f"Missing keys: {missing}")

    return {k: float(sample[k]) for k in required}


def quick_checks(sample):
    """
    Simple geometry checks.
    The circle-slot checks are conservative/simplified because the plotted oval is simplified too.
    """
    x1, y1 = sample["x1"], sample["y1"]
    x2, y2 = sample["x2"], sample["y2"]
    x3, y3 = sample["x3"], sample["y3"]
    angle_deg = sample["angle"]

    edge_margin = 2.0
    clearance = 1.0

    messages = []

    # Circle-edge checks
    if not (MIN_COORD + edge_margin + r1 <= x1 <= MAX_COORD - edge_margin - r1 and MIN_COORD + edge_margin + r1 <= y1 <= MAX_COORD - edge_margin - r1):
        messages.append("circle 1 too close to edge")

    if not (MIN_COORD + edge_margin + r2 <= x2 <= MAX_COORD - edge_margin - r2 and
            MIN_COORD + edge_margin + r2 <= y2 <= MAX_COORD - edge_margin - r2):
        messages.append("circle 2 too close to edge")

    # Rotated ellipse/oval bounding box against plate edge
    theta = math.radians(angle_deg)
    extent_x = abs(a * math.cos(theta)) + abs(b * math.sin(theta))
    extent_y = abs(a * math.sin(theta)) + abs(b * math.cos(theta))

    if not (MIN_COORD + edge_margin + extent_x <= x3 <= MAX_COORD - edge_margin - extent_x and
            MIN_COORD + edge_margin + extent_y <= y3 <= MAX_COORD - edge_margin - extent_y):
        messages.append("oval/slot too close to edge")

    # Circle-circle overlap
    d12 = math.hypot(x1 - x2, y1 - y2)
    if d12 < r1 + r2 + clearance:
        messages.append(f"circle 1 and circle 2 overlap / too close: d={d12:.2f}")

    return messages


def plot_sample(sample, ax):
    ax.clear()

    x1, y1 = sample["x1"], sample["y1"]
    x2, y2 = sample["x2"], sample["y2"]
    x3, y3 = sample["x3"], sample["y3"]
    angle = sample["angle"]

    # Plate
    plate = Rectangle((MIN_COORD, MIN_COORD), PLATE_SIZE, PLATE_SIZE,
                      fill=False, linewidth=2)
    ax.add_patch(plate)

    # 2 mm edge safety area, just as visual guide
    safe = Rectangle((MIN_COORD + 2, MIN_COORD + 2), PLATE_SIZE - 4, PLATE_SIZE - 4,
                     fill=False, linestyle="--", linewidth=1)
    ax.add_patch(safe)

    # Circular cutouts
    c1 = Circle((x1, y1), r1, fill=False, linewidth=2)
    c2 = Circle((x2, y2), r2, fill=False, linewidth=2)
    ax.add_patch(c1)
    ax.add_patch(c2)

    # Elongated cutout shown as rotated ellipse/oval for now
    oval = Ellipse((x3, y3), width=2 * a, height=2 * b,
                   angle=angle, fill=False, linewidth=2)
    ax.add_patch(oval)

    # Centers
    ax.plot([x1, x2, x3], [y1, y2, y3], marker="x", linestyle="None")

    ax.text(x1, y1, "  c1", va="center")
    ax.text(x2, y2, "  c2", va="center")
    ax.text(x3, y3, "  slot", va="center")

    checks = quick_checks(sample)
    if checks:
        title = "Possible invalid geometry: " + "; ".join(checks)
    else:
        title = "No obvious violation in simple checks"

    ax.set_title(title)
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")
    ax.set_xlim(MIN_COORD - 5, MAX_COORD + 5)
    ax.set_ylim(MIN_COORD - 5, MAX_COORD + 5)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True)


def main():
    root = tk.Tk()
    root.title("OptML Sample Visualizer")

    top = tk.Frame(root)
    top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

    label = tk.Label(
        top,
        text="Paste sample dict or entries, then click Plot:"
    )
    label.pack(anchor="w")

    text = tk.Text(top, height=5, width=110)
    text.pack(fill=tk.X)

    example = "'x1': -20.00773025417133, 'y1': -1.0596613552893146, 'x2': -9.092743782354484, 'y2': 14.664200020582072, 'x3': 6.273580420581212, 'y3': -11.871746868044388, 'angle': 37.13405656167496"
    text.insert("1.0", example)

    fig, ax = plt.subplots(figsize=(7, 7))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def on_plot():
        try:
            sample = parse_sample(text.get("1.0", tk.END))
            plot_sample(sample, ax)
            canvas.draw()
        except Exception as e:
            messagebox.showerror("Could not parse/plot sample", str(e))

    button = tk.Button(top, text="Plot", command=on_plot)
    button.pack(anchor="w", pady=5)

    # Plot example immediately
    on_plot()

    root.mainloop()


if __name__ == "__main__":
    main()
