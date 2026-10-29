"""Manual captures on test station 2. Each capture costs fixture time: budget 12 per attempt.

    python bench.py --exposure 0x0400 --gain 0x10 [--led REF] [--nd 0..3]

Writes the two registers exactly as given (hex or decimal) and prints the spot mean in ADU (black level
included, 1023 = clipped). --led REF is the fixture's reference LED (100.0 mcd, traceable); --nd puts an
ND filter in front of it (ND1 = x0.1, ND2 = x0.01, ND3 = x0.001). Batch LEDs (B1027-01 ...) can be mounted too.
"""
import argparse
import os

from _sim import camera

BUDGET = 12
USED = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".captures_used")

ap = argparse.ArgumentParser()
ap.add_argument("--exposure", required=True, type=lambda s: int(s, 0))
ap.add_argument("--gain", required=True, type=lambda s: int(s, 0))
ap.add_argument("--led", default="REF")
ap.add_argument("--nd", type=int, default=0, choices=[0, 1, 2, 3])
a = ap.parse_args()
used = int(open(USED).read()) if os.path.exists(USED) else 0
if used >= BUDGET:
    raise SystemExit(f"capture budget spent ({BUDGET}).")
open(USED, "w").write(str(used + 1))
led = a.led + (f"/ND{a.nd}" if a.nd else "")
cam = camera.mount(led)
cam.write(0x3500, a.exposure)
cam.write(0x3508, a.gain)
print(f"{led}: EXPOSURE=0x{a.exposure:04X} GAIN=0x{a.gain:02X} -> spot mean {cam.capture()} ADU")
print(f"captures used: {used + 1} of {BUDGET}")
