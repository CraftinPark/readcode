"""Hidden replay, run AFTER the player says "resolved" (never shown to the player): weeks 1-12 of traffic through
the player's notify/ against simulated Textly (daily cap 10,000), minute by minute. Weeks 7-12 are scored:
every login code delivered exactly once within 5 minutes, and every campaign message delivered within 48 h.

    python _key/replay.py --code DIR
"""
import argparse
import collections
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world  # noqa: E402


def run(code_dir, verbose=True):
    out = os.path.join(tempfile.mkdtemp(), "out.json")
    r = subprocess.run([sys.executable, os.path.join(HERE, "runner.py"), os.path.abspath(code_dir),
                        str(world.REPLAY_WEEKS), out], capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return False, {}
    d = json.load(open(out))
    start = world.T0 + world.VISIBLE_WEEKS * world.WEEK
    got = collections.defaultdict(list)
    for t, to, body in d["delivered"]:
        got[(to, body)].append(t)
    stats = collections.Counter()
    for t, phone, code in d["otp"]:
        if t < start:
            continue
        times = got.get((phone, world_body(code)), [])
        stats["otp"] += 1
        if not times or min(times) - t > 300:
            stats["otp lost or late"] += 1
        elif len(times) > 1:
            stats["otp duplicated"] += 1
    for e in world.workload(world.REPLAY_WEEKS):
        if e[1] != "campaign" or e[0] < start:
            continue
        for p in e[3]:
            stats["campaign"] += 1
            times = got.get((p, e[4]), [])
            if not times or min(times) - e[0] > 2 * world.DAY:
                stats["campaign not delivered in 48 h"] += 1
    ok = all(stats[k] == 0 for k in ("otp lost or late", "otp duplicated", "campaign not delivered in 48 h"))
    if verbose:
        print(f"  login codes: {stats['otp']}, lost or late {stats['otp lost or late']}, "
              f"duplicated {stats['otp duplicated']}")
        print(f"  campaign messages: {stats['campaign']}, not delivered in 48 h "
              f"{stats['campaign not delivered in 48 h']}")
        print(f"replay: {'PASS' if ok else 'FAIL'}")
    return ok, stats


def world_body(code):
    return "Your Shopwell login code is {code}. It expires in 10 minutes.".format(code=code)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=os.path.dirname(HERE))
    sys.exit(0 if run(ap.parse_args().code)[0] else 1)
