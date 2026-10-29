"""Shipped code and the tempting proportional fix fail the catalogue replay; the reference passes."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

bad = 0
for name, code, should_pass in [("shipped", os.path.dirname(HERE), False),
                                ("scale_fix (tempting hack)", os.path.join(HERE, "scale_fix"), False),
                                ("reference", os.path.join(HERE, "reference"), True)]:
    print(f"{name}:")
    ok, total = replay.run(code)
    bad += (ok == total) != should_pass
sys.exit(1 if bad else 0)
