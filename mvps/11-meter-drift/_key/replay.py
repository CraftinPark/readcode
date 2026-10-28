"""Hidden replay, run AFTER the player says "resolved" (never shown to the player): weeks 1-32 of traffic go
through the player's ingest.receive in arrival order; at each 4-week period end (+1 day for late packets) the
billing run calls billing.bill for every meter. Bills for weeks 5-32 must be within 1% of the truth
(what each customer actually used, priced at the real time of day).

    python _key/replay.py --code DIR
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sim  # noqa: E402

WEEKS = 32
TOLERANCE = 0.01
RUNNER = r'''
import json, sqlite3, sys
from meterbill import db, ingest, billing
conn = sqlite3.connect(":memory:")
db.init(conn)
runs = json.load(open(sys.argv[2]))
out, k = [], 0
for line in open(sys.argv[1]):
    received_at, packet = json.loads(line)
    while k < len(runs) and runs[k][0] <= received_at:
        out.append(billing.bill(conn, *runs[k][1:])); k += 1
    ingest.receive(conn, packet, received_at)
while k < len(runs):
    out.append(billing.bill(conn, *runs[k][1:])); k += 1
print(json.dumps(out))
'''
_cache = {}


def _world():
    if not _cache:
        meters, deliveries = sim.world(WEEKS)
        work = tempfile.mkdtemp()
        with open(os.path.join(work, "packets.jsonl"), "w") as f:
            for d in deliveries:
                f.write(json.dumps(d) + "\n")
        runs, truth = [], []
        for w in range(5, WEEKS + 1, 4):
            start, end = sim.week_start(w), sim.week_start(w + 4)
            for m in meters:
                runs.append([end + sim.DAY, m.id, start, end])
                truth.append((m.id, w, m.truth_bill(start, end)))
        with open(os.path.join(work, "runs.json"), "w") as f:
            json.dump(runs, f)
        _cache.update(work=work, truth=truth, fw={m.id: m.fw for m in meters})
    return _cache


def run(code_dir, verbose=True):
    """Returns (bills within tolerance, total bills)."""
    w = _world()
    r = subprocess.run([sys.executable, "-c", RUNNER, os.path.join(w["work"], "packets.jsonl"),
                        os.path.join(w["work"], "runs.json")], cwd=code_dir, capture_output=True, text=True,
                       timeout=900)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return 0, len(w["truth"])
    got = json.loads(r.stdout.strip().splitlines()[-1])
    ok, worst = 0, {}
    for (meter, week, want), g in zip(w["truth"], got):
        err = (g - want) / want
        ok += abs(err) <= TOLERANCE
        if abs(err) > abs(worst.get(meter, (0, 0))[1]):
            worst[meter] = (week, err)
    if verbose:
        for meter, (week, err) in sorted(worst.items()):
            if abs(err) > TOLERANCE:
                print(f"  FAIL {meter} (fw {w['fw'][meter]}): worst bill weeks {week}-{week + 3} off by {err:+.1%}")
        print(f"replay: {ok}/{len(w['truth'])} bills within {TOLERANCE:.1%} of what customers really used")
    return ok, len(w["truth"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=os.path.dirname(HERE))
    ok, total = run(ap.parse_args().code)
    sys.exit(0 if ok == total else 1)
