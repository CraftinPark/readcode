"""Hidden grader, run AFTER the player says "resolved" (never shown to the player): 3 hours of checkouts through
the player's shop/ against the real pricing service on a fake clock. Every order must be charged the right amount.

    python _key/replay.py --code DIR
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(code_dir, verbose=True):
    r = subprocess.run([sys.executable, os.path.join(HERE, "run_replay.py"), code_dir], capture_output=True,
                       text=True, timeout=600)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return False, {}
    d = json.loads(r.stdout.strip().splitlines()[-1])
    ok = d["wrong"] == 0
    if verbose:
        print(f"  orders {d['orders']}, wrong {d['wrong']} (errors {d['errors']})")
        for e in d["examples"]:
            print(f"    minute {e['minute']}: {e['items']} charged {e['charged']}, want {e['want']}")
        print(f"replay: {'PASS' if ok else 'FAIL'}")
    return ok, d


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=os.path.dirname(HERE))
    sys.exit(0 if run(os.path.abspath(ap.parse_args().code))[0] else 1)
