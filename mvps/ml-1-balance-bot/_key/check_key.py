"""Checks the key: shipped and tempting configs fail the acceptance replay, the reference passes.

    python _key/check_key.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

CASES = [("shipped", os.path.join(replay.ROOT, "deploy", "config.json"), False)]
for name, expect in (("rate_only", False), ("rate_and_tilt", False), ("smoothing_only", False),
                     ("max_rate", False), ("reference", True)):
    CASES.append((name, os.path.join(HERE, name, "config.json"), expect))

if __name__ == "__main__":
    bad = 0
    for name, path, expect in CASES:
        res = replay.evaluate(cfg=json.load(open(path)))
        ok = res["ok"] / res["n"] >= replay.PASS
        flag = "" if ok == expect else "   <-- UNEXPECTED"
        bad += ok != expect
        print(f"{name:15s} {replay.report(res)}{flag}", flush=True)
    print("key check:", "OK" if not bad else f"{bad} unexpected")
    sys.exit(1 if bad else 0)
