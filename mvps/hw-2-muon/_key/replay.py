"""Hidden replay, run after the player says "resolved": the zenith-angle campaign runs for a year in the
unheated hut (-15 C in January, +30 C in July, +-3 C each day) with the player's board/config.json and
muon/analysis.py. 8,760 one-hour runs. For each quarter, I0 * cos^n is fitted; pass = every quarter has n within
2.0 +- 0.1 and I0 within 3% of the true vertical rate.

    python _key/replay.py --code DIR
"""
import argparse
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNNER = r'''
import json, math, sys
sys.path.insert(0, sys.argv[1]); sys.path.insert(1, sys.argv[2])
from _sim import telescope
from muon.analysis import muon_rate
config = json.load(open("board/config.json"))
out = []
for d in range(365):
    season = 7.5 - 22.5 * math.cos(2 * math.pi * (d - 15) / 365)
    for h in range(24):
        hut_c = season + 3.0 * math.sin(2 * math.pi * (h - 9) / 24)
        c = telescope.run(config, [0, 15, 30, 45, 60, 75][h % 6], 3600, temp_c=hut_c, seed=f"year-{d}-{h}")
        out.append((d, c["angle_deg"], c["seconds"], c["AB"], c["hut_c"], muon_rate(c, config)))
print(json.dumps({"truth": telescope.vertical_truth(), "runs": out}))
'''


def fit_cos_n(points):
    best = None
    for k in range(0, 4001):
        n = k / 1000
        c = [math.cos(math.radians(a)) ** n for a, _, _ in points]
        w = [1 / s ** 2 for _, _, s in points]
        den = sum(wi * ci * ci for wi, ci in zip(w, c))
        i0 = sum(wi * y * ci for wi, (_, y, _), ci in zip(w, points, c)) / den
        chi = sum(wi * (y - i0 * ci) ** 2 for wi, (_, y, _), ci in zip(w, points, c))
        if best is None or chi < best[0]:
            best = (chi, i0, n)
    return best[1], best[2]


def run(code_dir, verbose=True):
    """Returns (quarters passing, 4)."""
    r = subprocess.run([sys.executable, "-c", RUNNER, os.path.abspath(code_dir), ROOT], cwd=code_dir,
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return 0, 4
    res = json.loads(r.stdout.strip().splitlines()[-1])
    truth, ok = res["truth"], 0
    for q, name in enumerate(["Jan-Mar", "Apr-Jun", "Jul-Sep", "Oct-Dec"]):
        acc, temps = {}, []
        for d, ang, t, ab, hut_c, rate in res["runs"]:
            if q * 91 <= d < (q + 1) * 91 + (1 if q == 3 else 0):
                a = acc.setdefault(ang, [0.0, 0.0, 0.0])
                a[0] += rate * t
                a[1] += t
                a[2] += ab
                temps.append(hut_c)
        points = [(ang, s / t, math.sqrt(max(ab, 1)) / t) for ang, (s, t, ab) in sorted(acc.items())]
        i0, n = fit_cos_n(points)
        good = abs(n - 2.0) <= 0.1 and abs(i0 / truth - 1) <= 0.03
        ok += good
        if verbose:
            print(f"  {name} (hut {min(temps):5.1f} to {max(temps):4.1f} C): I0 {i0 / truth - 1:+6.1%}, n = {n:.3f}"
                  f"  {'ok' if good else 'FAIL'}")
    if verbose:
        print(f"replay: {ok}/4 quarters right")
    return ok, 4


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=ROOT)
    ok, total = run(ap.parse_args().code)
    sys.exit(0 if ok == total else 1)
