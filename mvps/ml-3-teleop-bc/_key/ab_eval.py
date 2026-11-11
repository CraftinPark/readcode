"""Train + evaluate the shipped code and the reference fix side by side (key only).

    python _key/ab_eval.py [--steps 3000] [--episodes 50]

Copies the project twice into a temp folder (one with `_key/reference/`
overlaid), trains both in parallel and prints both bench results.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKIP = {"_key", "runs", "__pycache__", ".pytest_cache"}


def copy_project(dest: str, overlay: str | None = None) -> str:
    shutil.copytree(ROOT, dest, ignore=lambda d, names: [n for n in names if n in SKIP])
    if overlay:
        for dirpath, _, files in os.walk(overlay):
            for f in files:
                src = os.path.join(dirpath, f)
                rel = os.path.relpath(src, overlay)
                os.makedirs(os.path.dirname(os.path.join(dest, rel)), exist_ok=True)
                shutil.copy2(src, os.path.join(dest, rel))
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--episodes", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="ab_")
    env = dict(os.environ, OMP_NUM_THREADS="3", MKL_NUM_THREADS="3")
    dirs = {"shipped": copy_project(os.path.join(tmp, "shipped")),
            "reference": copy_project(os.path.join(tmp, "reference"), os.path.join(HERE, "reference"))}
    procs = {k: subprocess.Popen([sys.executable, "train.py", "--steps", str(a.steps), "--seed", str(a.seed)],
                                 cwd=d, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
             for k, d in dirs.items()}
    for k, p in procs.items():
        out = p.communicate()[0]
        print(f"[{k}] " + "\n[{k}] ".join(out.strip().splitlines()[-3:]).replace("{k}", k))
    procs = {k: subprocess.Popen([sys.executable, "evaluate.py", "--episodes", str(a.episodes)],
                                 cwd=d, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
             for k, d in dirs.items()}
    for k, p in procs.items():
        print(f"[{k}] {p.communicate()[0].strip()}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
