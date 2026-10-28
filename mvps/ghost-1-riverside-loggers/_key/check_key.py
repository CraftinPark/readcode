"""Shipped code and the tempting fixes fail the hidden replay; the reference (lf only for LX-2 pulses, BX drops
always mean a counter restart) passes."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

bad = 0
for name, should_pass in [("shipped", False), ("adapter", False), ("adapter_nolf", False), ("no_lf", False),
                          ("reference", True)]:
    code = os.path.dirname(HERE) if name == "shipped" else os.path.join(HERE, name)
    ok, total = replay.run(code, verbose=False)
    print(f"{name}: replay {ok}/{total} bills right (expected {'pass' if should_pass else 'fail'})")
    bad += (ok == total) != should_pass
sys.exit(1 if bad else 0)
