"""Shipped code and the per-order-key fix (what every MVP 05 gate run shipped) fail the replay; the
per-attempt key passes."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import replay  # noqa: E402

bad = 0
for name, code, should_pass in [("shipped", os.path.dirname(HERE), False),
                                ("order_key", os.path.join(HERE, "order_key"), False),
                                ("reference", os.path.join(HERE, "reference"), True)]:
    passed = replay.run(code, verbose=False)
    print(f"{name}: replay {'passes' if passed else 'fails'} (expected {'pass' if should_pass else 'fail'})")
    bad += passed != should_pass
sys.exit(1 if bad else 0)
