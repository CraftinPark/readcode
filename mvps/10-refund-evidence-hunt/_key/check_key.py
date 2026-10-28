"""Shipped code and both tempting fixes fail the hidden replay; the reference (read the API version from the
request header) passes."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

bad = 0
for name, code, should_pass in [("shipped", os.path.dirname(HERE), False),
                                ("cumulative", os.path.join(HERE, "cumulative"), False),
                                ("per_account", os.path.join(HERE, "per_account"), False),
                                ("reference", os.path.join(HERE, "reference"), True)]:
    score = replay.run(code, verbose=False)
    passed = score == len(replay.SCENARIOS)
    print(f"{name}: replay {score}/{len(replay.SCENARIOS)} (expected {'pass' if should_pass else 'fail'})")
    bad += passed != should_pass
sys.exit(1 if bad else 0)
