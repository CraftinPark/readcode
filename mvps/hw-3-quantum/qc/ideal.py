"""Gate set and an ideal (noise-free) simulator for user circuits on 4 qubits.

A circuit is a list of gates, e.g. [("h", 0), ("cx", 0, 1), ("ry", 2, 0.3)]. Every qubit is measured at the end.
Outcomes are bitstrings where character k is qubit k.
"""
import cmath
import math

N = 4
ONE_QUBIT = {"h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "rx", "ry", "rz", "u"}
TWO_QUBIT = {"cx", "cz"}


def matrix(g):
    """2x2 matrix of a one-qubit gate tuple."""
    name, a = g[0], g[2:]
    r2 = 1 / math.sqrt(2)
    if name == "h":
        return ((r2, r2), (r2, -r2))
    if name == "x":
        return ((0, 1), (1, 0))
    if name == "y":
        return ((0, -1j), (1j, 0))
    if name == "z":
        return ((1, 0), (0, -1))
    if name == "s":
        return ((1, 0), (0, 1j))
    if name == "sdg":
        return ((1, 0), (0, -1j))
    if name == "t":
        return ((1, 0), (0, cmath.exp(1j * math.pi / 4)))
    if name == "tdg":
        return ((1, 0), (0, cmath.exp(-1j * math.pi / 4)))
    if name == "sx":
        return ((0.5 + 0.5j, 0.5 - 0.5j), (0.5 - 0.5j, 0.5 + 0.5j))
    if name == "rx":
        c, s = math.cos(a[0] / 2), math.sin(a[0] / 2)
        return ((c, -1j * s), (-1j * s, c))
    if name == "ry":
        c, s = math.cos(a[0] / 2), math.sin(a[0] / 2)
        return ((c, -s), (s, c))
    if name == "rz":
        return ((cmath.exp(-0.5j * a[0]), 0), (0, cmath.exp(0.5j * a[0])))
    if name == "u":
        th, ph, la = a
        c, s = math.cos(th / 2), math.sin(th / 2)
        return ((c, -cmath.exp(1j * la) * s), (cmath.exp(1j * ph) * s, cmath.exp(1j * (ph + la)) * c))
    raise ValueError(f"unknown gate {g}")


def apply1(psi, q, m):
    step = 1 << q
    for i in range(1 << N):
        if not i & step:
            j = i | step
            a, b = psi[i], psi[j]
            psi[i] = m[0][0] * a + m[0][1] * b
            psi[j] = m[1][0] * a + m[1][1] * b


def statevector(circuit):
    psi = [0j] * (1 << N)
    psi[0] = 1.0
    for g in circuit:
        if g[0] in ONE_QUBIT:
            apply1(psi, g[1], matrix(g))
        elif g[0] == "cz":
            for i in range(1 << N):
                if (i >> g[1]) & 1 and (i >> g[2]) & 1:
                    psi[i] = -psi[i]
        elif g[0] == "cx":
            c, t = g[1], g[2]
            for i in range(1 << N):
                if (i >> c) & 1 and not (i >> t) & 1:
                    j = i | (1 << t)
                    psi[i], psi[j] = psi[j], psi[i]
        else:
            raise ValueError(f"unknown gate {g}")
    return psi


def bitstring(i):
    return "".join("1" if (i >> k) & 1 else "0" for k in range(N))


def probabilities(circuit):
    """{bitstring: probability} for the ideal circuit."""
    return {bitstring(i): abs(a) ** 2 for i, a in enumerate(statevector(circuit))}
