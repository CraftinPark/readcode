"""Shipped firmware and the 'ignore negative jumps' hack fail a 10-minute shift; unwrapping the 16-bit counter passes."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from _sim import plant  # noqa: E402

bad = 0
for name, path, should_pass in [("shipped", os.path.join(HERE, "..", "firmware", "drive.py"), False),
                                ("reset_hack", os.path.join(HERE, "reset_hack", "drive.py"), False),
                                ("fixed", os.path.join(HERE, "fixed", "drive.py"), True)]:
    spec = importlib.util.spec_from_file_location(f"drive_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    log = plant.run(mod.Drive, seconds=600)
    worst = max(abs(x) for x in log["shaft_angle_error_deg"])
    passed = "estop_at" not in log and worst <= 5
    print(f"{name}: {'e-stop at ' + str(log['estop_at']) + 's' if 'estop_at' in log else 'no e-stop'}, worst error {worst} deg -> {'pass' if passed else 'fail'}")
    bad += passed != should_pass
sys.exit(1 if bad else 0)
