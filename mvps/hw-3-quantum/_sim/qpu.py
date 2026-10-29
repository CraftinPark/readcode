"""The physical world (key side; the player gets only a compiled .pyc without docstrings). A 4-transmon chip,
qubits 0-1-2-3 in a line, after a thermal cycle of the fridge.

Native program: a list of instructions, run in order, then every qubit is measured.
  ("x90", q, amp)   drive pulse, 1 tick: Rx(pi/2 * amp * gain[q])
  ("rz", q, theta)  virtual frame change, perfect, 0 ticks
  ("cz", a, b)      coupler pulse on (0,1), (1,2) or (2,3), 3 ticks
  ("wait", n)       n ticks idle

The hidden truth:
- gain[q]: pulse amplitudes from before the cooldown now over/under-rotate by +0.8%, -3.1%, +5.5%, +1.2%.
- Each qubit picks up Rz(detune[q]) per tick (frequencies moved): 0.031, -0.022, 0.006, 0.047 rad/tick.
- CZ adds local phases (alpha_a, alpha_b) and a conditional-phase error kappa = 0.03 (not correctable).
- Readout flips: P(1|0), P(0|1) per qubit.
- AC Stark crosstalk, new since the cooldown (qubit 0 moved close to qubit 2's drive tone, qubit 2 close to
  qubit 1's): each x90 on q2 also applies Rz(+0.19 * amp^2) to q0; each x90 on q1 applies Rz(-0.14 * amp^2) to q2.
  It is invisible to every single-qubit calibration and to GHZ fidelity (it only moves the GHZ phase).
- Incoherent noise as white noise: fidelity (1-0.0015) per x90, (1-0.012) per cz, (1-0.0004) per tick.
"""
import base64
import cmath
import json
import math
import random

_P = json.loads(base64.b64decode(b"eyJnYWluIjogWzEuMDM0Mzc4LCAwLjkwMDgxMywgMS4xNDIzMTgsIDEuMDIyMTNdLCAiZGV0IjogWzAuMDMxLCAtMC4wMjIsIDAuMDA2LCAwLjA0N10sICJjeiI6IHsiMDEiOiBbMS4xMiwgLTAuMV0sICIxMiI6IFswLjE1LCAwLjk1XSwgIjIzIjogWy0wLjI3LCAwLjY1XX0sICJrYXBwYSI6IDAuMDMsICJybyI6IFtbMC4wMTUsIDAuMDQ1XSwgWzAuMDIyLCAwLjA2XSwgWzAuMDE4LCAwLjA1XSwgWzAuMDI1LCAwLjEyXV0sICJzdGFyayI6IFtbMiwgMCwgMC4xOV0sIFsxLCAyLCAtMC4xNF1dLCAiZTEiOiAwLjAwMTUsICJlMiI6IDAuMDEyLCAiZWkiOiAwLjAwMDR9"))
N = 4
COUPLERS = {(0, 1), (1, 2), (2, 3)}


def _apply1(psi, q, m):
    step = 1 << q
    for i in range(1 << N):
        if not i & step:
            j = i | step
            a, b = psi[i], psi[j]
            psi[i] = m[0][0] * a + m[0][1] * b
            psi[j] = m[1][0] * a + m[1][1] * b


def _rz(psi, q, th):
    e0, e1 = cmath.exp(-0.5j * th), cmath.exp(0.5j * th)
    for i in range(1 << N):
        psi[i] *= e1 if (i >> q) & 1 else e0


def _rx(psi, q, th):
    c, s = math.cos(th / 2), -1j * math.sin(th / 2)
    _apply1(psi, q, ((c, s), (s, c)))


def _cz(psi, a, b, al_a, al_b, kappa):
    for i in range(1 << N):
        xa, xb = (i >> a) & 1, (i >> b) & 1
        ph = al_a * xa + al_b * xb + (math.pi + kappa) * (xa & xb)
        if ph:
            psi[i] *= cmath.exp(1j * ph)


def _idle(psi, ticks):
    for q in range(N):
        _rz(psi, q, _P["det"][q] * ticks)


def _execute(program):
    psi = [0j] * (1 << N)
    psi[0] = 1.0
    nx = ncz = ticks = 0
    for ins in program:
        op = ins[0]
        if op == "x90":
            q, amp = int(ins[1]), float(ins[2])
            if not 0 <= q < N or abs(amp) > 2.0:
                raise ValueError(f"bad pulse {ins}")
            _rx(psi, q, math.pi / 2 * amp * _P["gain"][q])
            for src, dst, s in _P["stark"]:
                if src == q:
                    _rz(psi, dst, s * amp * amp)
            _idle(psi, 1)
            nx, ticks = nx + 1, ticks + 1
        elif op == "rz":
            _rz(psi, int(ins[1]), float(ins[2]))
        elif op == "cz":
            a, b = sorted((int(ins[1]), int(ins[2])))
            if (a, b) not in COUPLERS:
                raise ValueError(f"no coupler between {a} and {b}")
            al = _P["cz"][f"{a}{b}"]
            _cz(psi, a, b, al[0], al[1], _P["kappa"])
            _idle(psi, 3)
            ncz, ticks = ncz + 1, ticks + 3
        elif op == "wait":
            n = int(ins[1])
            if n < 0:
                raise ValueError("wait must be >= 0")
            _idle(psi, n)
            ticks += n
        else:
            raise ValueError(f"unknown instruction {ins}")
    f = (1 - _P["e1"]) ** nx * (1 - _P["e2"]) ** ncz * (1 - _P["ei"]) ** ticks
    p = [f * abs(a) ** 2 + (1 - f) / (1 << N) for a in psi]
    for q in range(N):  # readout assignment errors
        r0, r1 = _P["ro"][q]
        step = 1 << q
        for i in range(1 << N):
            if not i & step:
                j = i | step
                p0, p1 = p[i], p[j]
                p[i], p[j] = p0 * (1 - r0) + p1 * r1, p0 * r0 + p1 * (1 - r1)
    return p


def bitstring(i):
    """Outcome index -> bitstring, character k is qubit k."""
    return "".join("1" if (i >> k) & 1 else "0" for k in range(N))


def run(program, shots, seed=None):
    """Runs a native program `shots` times. Returns {bitstring: count}, character k of the key = qubit k."""
    shots = int(shots)
    if shots < 1:
        raise ValueError("shots must be >= 1")
    p = _execute(program)
    rng = random.Random(seed)
    counts, left, rest = {}, shots, 1.0
    for i in range(1 << N):
        if left == 0:
            break
        pi = min(max(p[i] / rest, 0.0), 1.0) if rest > 1e-15 else 1.0
        k = left if i == (1 << N) - 1 else rng.binomialvariate(left, pi)
        if k:
            counts[bitstring(i)] = k
        left -= k
        rest -= p[i]
    return counts
