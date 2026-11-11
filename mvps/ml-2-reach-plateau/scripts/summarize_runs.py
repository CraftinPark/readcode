"""One line per run dir: seed, steps, final eval, best eval, explained var.

    python scripts/summarize_runs.py runs/
"""
import csv
import json
import os
import sys


def summarize(run):
    prog = os.path.join(run, "progress.csv")
    if not os.path.exists(prog):
        return None
    with open(prog, newline="") as f:
        rows = list(csv.DictReader(f))
    evals = [float(r["eval/return"]) for r in rows if r.get("eval/return")]
    ev = [float(r["explained_var"]) for r in rows if r.get("explained_var") not in ("", "nan", None)]
    cfg = {}
    cp = os.path.join(run, "config.json")
    if os.path.exists(cp):
        with open(cp) as f:
            cfg = json.load(f)
    return {
        "run": os.path.basename(run),
        "seed": cfg.get("seed", "?"),
        "steps": rows[-1]["steps"] if rows else 0,
        "final": sum(evals[-3:]) / max(len(evals[-3:]), 1) if evals else float("nan"),
        "best": max(evals) if evals else float("nan"),
        "ev": ev[-1] if ev else float("nan"),
    }


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "runs"
    out = []
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if os.path.isdir(p):
            s = summarize(p)
            if s:
                out.append(s)
    if not out:
        print("no runs under", base)
        return
    print(f"{'run':<40} {'seed':>4} {'steps':>8} {'final':>7} {'best':>7} {'expl_var':>8}")
    for s in out:
        print(f"{s['run']:<40} {s['seed']:>4} {s['steps']:>8} {s['final']:7.2f} {s['best']:7.2f} {s['ev']:8.3f}")


if __name__ == "__main__":
    main()
