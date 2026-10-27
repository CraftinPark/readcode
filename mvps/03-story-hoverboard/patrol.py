"""Runs a 4-second patrol for every board in the fleet with a crosswind gust, and prints telemetry.

    python patrol.py                   # whole fleet, summary
    python patrol.py --unit P9-03 -v   # one board, every 10th tick
    python patrol.py --fleet other.json
"""
import argparse
import json

from _sim import physics as hardware
from hover.imu import IMU
from hover.stabilizer import Stabilizer


class HardwareIMU(IMU):
    """The physical unit: reports with the sign its real firmware uses."""

    def read(self, true_roll, true_pitch):
        return {"roll": true_roll, "raw_pitch": hardware.vendor_sign(self.firmware) * true_pitch}


def patrol(firmware, verbose=False):
    hw = HardwareIMU(firmware)
    driver = IMU(firmware)
    stab = Stabilizer(driver)
    roll = pitch = roll_rate = pitch_rate = 0.0
    lean = 0.0
    for tick in range(200):
        gust = (3.0, 3.0) if 50 <= tick < 60 else (0.0, 0.0)
        tr, tp = stab.torque(hw.read(roll, pitch))
        roll, pitch, roll_rate, pitch_rate = hardware.step(roll, pitch, roll_rate, pitch_rate, tr, tp, gust)
        if verbose and tick % 10 == 0:
            print(f"  t={tick:3d} roll={roll:8.2f} pitch={pitch:8.2f}")
        lean = max(lean, abs(roll), abs(pitch))
        if abs(roll) > 45 or abs(pitch) > 45:
            return f"FLIPPED at t={tick} (roll {roll:.0f}, pitch {pitch:.0f})"
    return f"stable (max lean {lean:.2f} deg)"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fleet", default="fleet.json")
    ap.add_argument("--unit")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    bad = 0
    for board in json.load(open(a.fleet)):
        if a.unit and board["unit"] != a.unit:
            continue
        result = patrol(board["imu_firmware"], a.verbose)
        bad += result.startswith("FLIPPED")
        print(f"{board['unit']} (IMU fw {board['imu_firmware']}): {result}")
    raise SystemExit(1 if bad else 0)
