"""Hidden replay, run after the player says "resolved": the station measures the whole catalogue, 300 LEDs
from 0.2 to 20,000 mcd (log-uniform), with the player's station code. Pass = every LED within 3% of truth.

    python _key/replay.py --code DIR
"""
import argparse
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNNER = r'''
import json, random, sys
sys.path.insert(0, sys.argv[1]); sys.path.insert(1, sys.argv[2])
from _sim.camera import Camera
from station.measure import measure
rng = random.Random("catalogue")
out = []
for i in range(300):
    mcd = 10 ** rng.uniform(-0.7, 4.3)
    out.append((mcd, measure(Camera(mcd, seed=i))))
print(json.dumps(out))
'''


def run(code_dir, verbose=True):
    """Returns (LEDs within 3%, 300)."""
    r = subprocess.run([sys.executable, "-c", RUNNER, os.path.abspath(code_dir), ROOT], cwd=code_dir,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return 0, 300
    import json
    res = json.loads(r.stdout.strip().splitlines()[-1])
    ok, worst = 0, []
    for mcd, got in res:
        err = (got - mcd) / mcd
        ok += abs(err) <= 0.03
        worst.append((abs(err), mcd, err))
    if verbose:
        for band, lo, hi in [("dim  0.2-2", 0.2, 2), ("mid  2-2000", 2, 2000), ("bright 2000-20000", 2000, 20001)]:
            errs = [e for a, m, e in worst if lo <= m < hi]
            n_ok = sum(abs(e) <= 0.03 for e in errs)
            print(f"  {band:18s} {n_ok}/{len(errs)} ok, worst {max(errs, key=abs):+.1%}")
        print(f"replay: {ok}/300 LEDs within 3%")
    return ok, 300


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=ROOT)
    ok, total = run(ap.parse_args().code)
    sys.exit(0 if ok == total else 1)
