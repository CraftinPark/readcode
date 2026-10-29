"""The physical world (key side; the player gets only a compiled .pyc). A KX-219 sensor on LED test station 2,
looking at one LED through the fixture's lens. The station reads the mean of a 40x40-pixel spot.

The hidden truth, which a player can only learn by capturing:
- EXPOSURE is counted in sensor lines, not microseconds. One line = 29.63 us (HTS 2200 at 74.25 MHz).
- Integration also includes a fixed 11.5 us (the sensor's fine-integration offset), so time = lines*29.63 + 11.5.
- In the 1080p30 mode the frame is 1125 lines, so EXPOSURE above 1121 is silently clamped to 1121.
- GAIN is 1/16 steps as on the old module, but analog gain stops at 8x: GAIN above 128 acts as 128.
- Sensitivity: 0.001 ADU per (mcd * us) at 1x. Black level 64, 10-bit (saturates at 1023).
"""
import base64
import json
import random

_P = json.loads(base64.b64decode(
    b"eyJsdCI6IDI5LjYzLCAib2ZmIjogMTEuNSwgIm1heGwiOiAxMTIxLCAiZ21heCI6IDEyOCwgInMiOiAwLjAwMSwgImJsayI6IDY0fQ=="))
EXPOSURE, GAIN = 0x3500, 0x3508
REF_MCD = 100.0
ND = {0: 1.0, 1: 0.1, 2: 0.01, 3: 0.001}


class Camera:
    """One KX-219 looking at one LED (intensity in mcd, after any ND filter)."""

    def __init__(self, mcd, seed=0):
        self._mcd = float(mcd)
        self._regs = {EXPOSURE: 0x0100, GAIN: 0x10}
        self._rng = random.Random(f"{mcd}:{seed}")

    def write(self, reg, value):
        if reg not in self._regs:
            raise ValueError(f"no register 0x{reg:04X}")
        self._regs[reg] = int(value) & (0xFFFF if reg == EXPOSURE else 0xFF)

    def read(self, reg):
        return self._regs[reg]

    def capture(self):
        """Mean ADU of the LED spot (40x40 pixels), black level included."""
        lines = min(self._regs[EXPOSURE], _P["maxl"])
        t_us = lines * _P["lt"] + _P["off"]
        g = max(min(self._regs[GAIN], _P["gmax"]), 16) / 16.0
        sig = _P["s"] * self._mcd * t_us * g
        noise = self._rng.gauss(0, (0.6 * g + (sig * g * 0.3) ** 0.5) / 40.0)
        return round(min(_P["blk"] + sig + noise, 1023.0), 2)


def mount(led):
    """The station fixture: 'REF' (100.0 mcd reference LED), 'REF/ND1'..'REF/ND3' (with an ND filter), or a
    batch LED id from data/."""
    if led.startswith("REF"):
        nd = int(led[-1]) if "/ND" in led else 0
        return Camera(REF_MCD * ND[nd])
    return Camera(_batch()[led])


def _batch():
    rng = random.Random("batch-1027")
    return {f"B1027-{i:02d}": round(10 ** rng.uniform(0.7, 2.6), 2) for i in range(1, 13)}
