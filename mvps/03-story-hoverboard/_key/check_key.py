"""Shipped driver and the special-case hack both flip boards on the next firmware update (hidden fleet);
the numeric version compare keeps every board up."""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import patrol  # noqa: E402

fleet = json.load(open(os.path.join(HERE, "hidden_fleet.json")))
bad = 0
for name, path, should_pass in [("shipped", os.path.join(ROOT, "hover", "imu.py"), False),
                                ("hack", os.path.join(HERE, "hack", "imu.py"), False),
                                ("fixed", os.path.join(HERE, "fixed", "imu.py"), True)]:
    spec = importlib.util.spec_from_file_location(f"imu_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    patrol.IMU = mod.IMU
    flipped = [b["unit"] for b in fleet if patrol.patrol(b["imu_firmware"]).startswith("FLIPPED")]
    print(f"{name}: {len(flipped)} of {len(fleet)} boards flip {flipped}")
    bad += (not flipped) != should_pass
sys.exit(1 if bad else 0)
