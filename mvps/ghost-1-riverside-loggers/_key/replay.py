"""Hidden replay, run AFTER the player says "resolved" (never shown to the player): a fresh database, then
every packet from 1 Jun 2026 to 2 May 2027 goes through the player's qn.receive in arrival order (data/ first,
exactly as the player saw it, then six months of new traffic). One day after each month ends, the billing run
calls bx.bill for every meter. Bills for October 2026 to April 2027 (7 months x 24 meters) must be within 1% of
the litres each customer really used.

    python _key/replay.py [--code DIR]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim  # noqa: E402

TOLERANCE = 0.01
MONTHS = ["2026-10-01", "2026-11-01", "2026-12-01", "2027-01-01", "2027-02-01", "2027-03-01", "2027-04-01",
          "2027-05-01"]
RUNNER = r'''
import json, sqlite3, sys
from wfl import db, qn, bx
conn = sqlite3.connect(":memory:")
db.init(conn)
runs = json.load(open(sys.argv[2]))
out, k = [], 0
for line in open(sys.argv[1]):
    p = json.loads(line)
    while k < len(runs) and runs[k][0] <= p["rx"]:
        out.append(bx.bill(conn, *runs[k][1:])["litres"]); k += 1
    qn.receive(conn, p)
while k < len(runs):
    out.append(bx.bill(conn, *runs[k][1:])["litres"]); k += 1
print(json.dumps(out))
'''
_cache = {}


def _world():
    if not _cache:
        ms, packets, truth, _ = sim.run()
        work = tempfile.mkdtemp()
        with open(os.path.join(work, "packets.jsonl"), "w") as f:
            for _, p in packets:
                f.write(json.dumps(p, separators=(",", ":")) + "\n")
        runs, want = [], []
        for a, b in zip(MONTHS, MONTHS[1:]):
            ta, tb = sim.ts(a), sim.ts(b)
            for m in ms:
                runs.append([tb + sim.DAY, m.id, ta, tb])
                want.append((m.id, a[:7], sim.truth_bill(truth, m.id, ta, tb)))
        with open(os.path.join(work, "runs.json"), "w") as f:
            json.dump(runs, f)
        _cache.update(work=work, want=want, logger={m.id: m.model for m in ms})
    return _cache


def run(code_dir, verbose=True):
    """Returns (bills within tolerance, total bills)."""
    w = _world()
    box = tempfile.mkdtemp()  # the player's wfl/ next to our own data/meters.csv
    shutil.copytree(os.path.join(code_dir, "wfl"), os.path.join(box, "wfl"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(os.path.join(box, "data"))
    shutil.copy(os.path.join(os.path.dirname(HERE), "data", "meters.csv"), os.path.join(box, "data"))
    r = subprocess.run([sys.executable, "-c", RUNNER, os.path.join(w["work"], "packets.jsonl"),
                        os.path.join(w["work"], "runs.json")], cwd=box, capture_output=True, text=True,
                       timeout=900)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return 0, len(w["want"])
    got = json.loads(r.stdout.strip().splitlines()[-1])
    ok, fails = 0, []
    for (meter, month, want), g in zip(w["want"], got):
        err = (g - want) / want
        ok += abs(err) <= TOLERANCE
        if abs(err) > TOLERANCE:
            fails.append(f"  FAIL {meter} ({w['logger'][meter]}) {month}: billed {g} L, used {want} L ({err:+.1%})")
    if verbose:
        print("\n".join(fails[:40]) + ("\n  ..." if len(fails) > 40 else ""))
        print(f"replay: {ok}/{len(w['want'])} monthly bills within {TOLERANCE:.0%} of what customers really used")
    return ok, len(w["want"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=os.path.dirname(HERE))
    ok, total = run(ap.parse_args().code)
    sys.exit(0 if ok == total else 1)
