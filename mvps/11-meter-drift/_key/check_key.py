"""Shipped code and the tempting fixes fail the hidden replay; the reference (estimate each meter's clock
offset from its live packets) passes."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

bad = 0
for name, code, should_pass in [("shipped", os.path.dirname(HERE), False),
                                ("late_ok", os.path.join(HERE, "late_ok"), False),
                                ("naive_offset", os.path.join(HERE, "naive_offset"), False),
                                ("reference", os.path.join(HERE, "reference"), True)]:
    ok, total = replay.run(code, verbose=False)
    print(f"{name}: replay {ok}/{total} bills right (expected {'pass' if should_pass else 'fail'})")
    bad += (ok == total) != should_pass
sys.exit(1 if bad else 0)
