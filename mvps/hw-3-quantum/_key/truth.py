"""The chip's true parameters in calib.json form (key only), so the reference compiler can be checked against
an oracle. `stark` is the crosstalk table the shipped calibration format has no place for."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _sim import qpu  # noqa: E402


def calib(with_stark=True):
    p = qpu._P
    cal = {"amp": [round(1 / g, 6) for g in p["gain"]],
           "detune_rad_per_tick": list(p["det"]),
           "cz_phase": {f"{k[0]}-{k[1]}": list(v) for k, v in p["cz"].items()},
           "readout": [{"p1_given_0": r0, "p0_given_1": r1} for r0, r1 in p["ro"]]}
    if with_stark:
        cal["stark"] = [{"pulse_on": s, "shifts": d, "rad_per_x90": v} for s, d, v in p["stark"]]
    return cal


if __name__ == "__main__":
    print(json.dumps(calib(), indent=2))
