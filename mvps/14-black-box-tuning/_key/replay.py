"""Hidden check, run AFTER the player says "resolved": production with the player's config.json, today (12,000
events/s) and next quarter (13,000). Both must keep up with p99 <= 250 ms. No noise: this is the truth.

    python _key/replay.py --code DIR
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
from model import perf  # noqa: E402

SLO_P99 = 250


def run(code_dir, verbose=True):
    cfg = json.load(open(os.path.join(code_dir, "config.json")))
    w, b, p = int(cfg["workers"]), int(cfg["batch"]), int(cfg["prefetch"])
    ok = True
    for load in (12000, 13000):
        thr, p50, p99, util = perf(w, b, p, load)
        good = thr >= load and p99 <= SLO_P99
        ok &= good
        if verbose:
            print(f"  {load} events/s: capacity {thr:,.0f}, p99 {p99:,.0f} ms -> {'ok' if good else 'FAIL'}")
    if verbose:
        print(f"replay ({w} workers, batch {b}, prefetch {p}): {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=os.path.dirname(HERE))
    sys.exit(0 if run(ap.parse_args().code) else 1)
