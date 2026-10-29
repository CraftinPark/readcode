"""Compiles user circuits (qc/ideal.py gate set) to the chip's native program, using qc/calib.json.

Natives: ("x90", q, amp) a pi/2 X pulse (1 tick), ("rz", q, theta) a virtual frame change (free, exact),
("cz", a, b) on couplers (0,1), (1,2), (2,3) (3 ticks), ("wait", n) idle ticks. Every qubit is measured at the end.

One-qubit gates become U3(theta, phi, lam) = rz(lam), x90, rz(theta + pi), x90, rz(phi + pi). CX(c, t) is
H(t) CZ H(t). Z phases commute with CZ and with the final measurement, so they are tracked per qubit and only
emitted before the next pulse on that qubit: the frame drift (detune_rad_per_tick, every tick) and the CZ's
local phases (cz_phase).
"""
import cmath
import json
import math
import os

from qc.ideal import ONE_QUBIT, matrix

CALIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calib.json")
COUPLERS = {(0, 1), (1, 2), (2, 3)}
H = ("h",)


def u3_angles(m):
    """(theta, phi, lam) with m = U3(theta, phi, lam) up to a global phase."""
    a, b, c, d = m[0][0], m[0][1], m[1][0], m[1][1]
    theta = 2 * math.atan2(abs(c), abs(a))
    if abs(c) < 1e-9:
        return 0.0, cmath.phase(d) - cmath.phase(a), 0.0
    if abs(a) < 1e-9:
        return math.pi, cmath.phase(c) - cmath.phase(-b), 0.0
    return theta, cmath.phase(c) - cmath.phase(a), cmath.phase(-b) - cmath.phase(a)


class Compiler:
    def __init__(self, calib=None):
        self.cal = calib or json.load(open(CALIB))
        self.prog = []
        self.frame = [0.0] * 4

    def _tick(self, n):
        for q in range(4):
            self.frame[q] -= self.cal["detune_rad_per_tick"][q] * n

    def _rz(self, q, theta):
        self.frame[q] += theta

    def _x90(self, q):
        if abs(self.frame[q]) > 1e-12:
            self.prog.append(("rz", q, self.frame[q]))
            self.frame[q] = 0.0
        self.prog.append(("x90", q, self.cal["amp"][q]))
        self._tick(1)

    def one(self, q, m):
        theta, phi, lam = u3_angles(m)
        if abs(theta) < 1e-9:
            self._rz(q, phi + lam)
            return
        self._rz(q, lam)
        self._x90(q)
        self._rz(q, theta + math.pi)
        self._x90(q)
        self._rz(q, phi + math.pi)

    def cz(self, a, b):
        a, b = sorted((a, b))
        if (a, b) not in COUPLERS:
            raise ValueError(f"qubits {a} and {b} are not coupled")
        self.prog.append(("cz", a, b))
        self._tick(3)
        pa, pb = self.cal["cz_phase"][f"{a}-{b}"]
        self._rz(a, -pa)
        self._rz(b, -pb)

    def add(self, g):
        if g[0] in ONE_QUBIT:
            self.one(g[1], matrix(g))
        elif g[0] == "cz":
            self.cz(g[1], g[2])
        elif g[0] == "cx":
            self.one(g[2], matrix(H))
            self.cz(g[1], g[2])
            self.one(g[2], matrix(H))
        else:
            raise ValueError(f"unknown gate {g}")


def compile(circuit, calib=None):
    c = Compiler(calib)
    for g in circuit:
        c.add(g)
    return c.prog
