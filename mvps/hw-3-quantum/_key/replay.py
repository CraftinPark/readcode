"""Hidden replay, run after the player says "resolved": the queue reopens and runs 40 user circuits (random
one-qubit gates on all four qubits and CX/CZ on neighbours, 8 layers deep, 100,000 shots each) through the
player's qc/run.py. Each result is compared with the ideal distribution (total variation distance, TVD).

The same circuits also go through an oracle: the reference compiler fed the chip's true parameters. Its TVD is
what white noise, the CZ's conditional-phase error and shot noise leave; no calibration can beat it.
Pass = the player's mean TVD is within 0.04 of the oracle's and no circuit is more than 0.15 worse.

    python _key/replay.py --code DIR
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOTS = 100_000
RUNNER = r'''
import json, sys
sys.path.insert(0, sys.argv[1]); sys.path.insert(1, sys.argv[2])
from qc import backend
backend.FREE = True
from qc.run import run
circuits = json.load(open(sys.argv[3]))
print(json.dumps([run([tuple(g) for g in c], int(sys.argv[4])) for c in circuits]))
'''


def circuits(n=40, layers=8, seed="queue"):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        c = []
        for _ in range(layers):
            for q in range(4):
                g = rng.choice(["h", "sx", "t", "s", "rx", "ry", "u", "u"])
                if g in ("rx", "ry"):
                    c.append([g, q, rng.uniform(-math.pi, math.pi)])
                elif g == "u":
                    c.append([g, q, rng.uniform(0, math.pi), rng.uniform(-math.pi, math.pi),
                              rng.uniform(-math.pi, math.pi)])
                else:
                    c.append([g, q])
            pairs = rng.choice([[(0, 1), (2, 3)], [(1, 2)], [(0, 1)], [(2, 3)], [(1, 2)]])
            for a, b in pairs:
                if rng.random() < 0.5:
                    a, b = b, a
                c.append([rng.choice(["cx", "cx", "cz"]), a, b])
        out.append(c)
    return out


def _results(code_dir, path):
    r = subprocess.run([sys.executable, "-c", RUNNER, os.path.abspath(code_dir), ROOT, path, str(SHOTS)],
                       cwd=code_dir, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        return None, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1]), ""


def _tvd(p, q):
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


_oracle = {}


def oracle_tvds(path, cs):
    if "tvd" not in _oracle:
        sys.path.insert(0, ROOT)
        import tempfile
        import shutil
        import truth
        work = tempfile.mkdtemp()
        shutil.copytree(os.path.join(HERE, "reference", "qc"), os.path.join(work, "qc"))
        for n in ("ideal.py", "backend.py", "__init__.py", "run.py", "mitigate.py"):
            shutil.copy(os.path.join(ROOT, "qc", n), os.path.join(work, "qc", n))
        json.dump(truth.calib(True), open(os.path.join(work, "qc", "calib.json"), "w"))
        res, err = _results(work, path)
        if res is None:
            raise SystemExit("oracle crashed:\n" + err)
        _oracle["tvd"] = [_tvd(r, ideal(c)) for r, c in zip(res, cs)]
        shutil.rmtree(work)
    return _oracle["tvd"]


def ideal(c):
    sys.path.insert(0, ROOT)
    from qc.ideal import probabilities
    return probabilities([tuple(g) for g in c])


def run(code_dir, verbose=True):
    """Returns (passed: bool, mean TVD excess over the oracle)."""
    import tempfile
    cs = circuits()
    path = os.path.join(tempfile.mkdtemp(), "circuits.json")
    json.dump(cs, open(path, "w"))
    base = oracle_tvds(path, cs)
    res, err = _results(code_dir, path)
    if res is None:
        if verbose:
            print("replay crashed:\n" + err)
        return False, 1.0
    tv = [_tvd(r, ideal(c)) for r, c in zip(res, cs)]
    excess = [a - b for a, b in zip(tv, base)]
    mean_ex = sum(excess) / len(excess)
    ok = mean_ex <= 0.04 and max(excess) <= 0.15
    if verbose:
        print(f"  oracle mean TVD {sum(base) / len(base):.3f}; yours {sum(tv) / len(tv):.3f} "
              f"(excess mean {mean_ex:+.3f}, worst circuit {max(excess):+.3f}, "
              f"{sum(e > 0.15 for e in excess)}/40 circuits more than 0.15 worse)")
        print(f"replay: {'pass' if ok else 'FAIL'}")
    return ok, mean_ex


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=ROOT)
    ok, _ = run(ap.parse_args().code)
    sys.exit(0 if ok else 1)
