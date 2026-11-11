"""Compare eval curves in the terminal (no matplotlib on the cluster image).

    python scripts/plot_curves.py runs/before_refactor_s1.csv runs/after_refactor_s1.csv
    python scripts/plot_curves.py runs/reach__s1__*/progress.csv --col explained_var

Reads both our progress.csv and tensorboard's "Download CSV" export
(Wall time,Step,Value).
"""
import argparse
import csv
import glob
import os
import sys

WIDTH = 72
HEIGHT = 18
MARKS = "*o+x#@"


def load(path, col):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return [], []
    if "Step" in rows[0] and "Value" in rows[0]:   # tensorboard export
        xs = [float(r["Step"]) for r in rows]
        ys = [float(r["Value"]) for r in rows]
        return xs, ys
    xs, ys = [], []
    for r in rows:
        v = r.get(col, "")
        if v in ("", None):
            continue
        xs.append(float(r["steps"]))
        ys.append(float(v))
    return xs, ys


def smooth(ys, k):
    if k <= 1:
        return ys
    out = []
    for i in range(len(ys)):
        w = ys[max(0, i - k + 1):i + 1]
        out.append(sum(w) / len(w))
    return out


def plot(series, title=""):
    allx = [x for xs, _, _ in series for x in xs]
    ally = [y for _, ys, _ in series for y in ys]
    if not allx:
        print("nothing to plot")
        return
    x0, x1 = min(allx), max(allx)
    y0, y1 = min(ally), max(ally)
    if y1 == y0:
        y1 = y0 + 1
    grid = [[" "] * WIDTH for _ in range(HEIGHT)]
    for k, (xs, ys, _) in enumerate(series):
        m = MARKS[k % len(MARKS)]
        for x, y in zip(xs, ys):
            c = int((x - x0) / max(x1 - x0, 1) * (WIDTH - 1))
            r = HEIGHT - 1 - int((y - y0) / (y1 - y0) * (HEIGHT - 1))
            grid[r][c] = m
    print(title)
    for r, line in enumerate(grid):
        yv = y1 - (y1 - y0) * r / (HEIGHT - 1)
        print(f"{yv:8.2f} |" + "".join(line))
    print(" " * 9 + "+" + "-" * WIDTH)
    print(" " * 10 + f"{x0:<12.0f}" + " " * (WIDTH - 24) + f"{x1:>12.0f}")
    for k, (_, ys, name) in enumerate(series):
        tail = ys[-5:]
        print(f"  {MARKS[k % len(MARKS)]} {name}   last5 mean = {sum(tail) / len(tail):.2f}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("--col", default="eval/return")
    p.add_argument("--smooth", type=int, default=1)
    a = p.parse_args()
    files = []
    for f in a.files:
        files += sorted(glob.glob(f)) or [f]
    series = []
    for f in files:
        if not os.path.exists(f):
            print("missing", f, file=sys.stderr)
            continue
        xs, ys = load(f, a.col)
        series.append((xs, smooth(ys, a.smooth), os.path.relpath(f)))
    plot(series, title=a.col)


if __name__ == "__main__":
    main()
