"""The shipped config and the tempting ones fail the hidden check; the reference passes."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay  # noqa: E402

bad = 0
for name, should_pass in [("shipped", False), ("old_boxes", False), ("fewer_workers", False),
                          ("bigger_batch", False), ("reference", True)]:
    print(f"== {name} (expected {'pass' if should_pass else 'fail'})")
    bad += replay.run(os.path.dirname(HERE) if name == "shipped" else os.path.join(HERE, name)) != should_pass
sys.exit(1 if bad else 0)
