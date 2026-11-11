"""Proves the shipped code causes the ticket's symptom and the baseline doesn't.

    python _key/verify.py               # quick preset, seeds 1-5, ~2 min on 10+ cores
    python _key/verify.py --seeds 1 2 3 --preset full

Runs, in parallel subprocesses:
  baseline   _key/baseline (shipped code with only the cause fixed)
  shipped    the player's code as shipped
  shipped --norm-adv false   (the experiment a player might try)
and prints the final eval return (mean of the last 3 evals) per seed.
Exit 0 if every baseline seed beats every shipped seed by a clear margin.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RUNNER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from armrl.config import parse_args
from armrl.trainer import Trainer
cfg = parse_args(sys.argv[3:])
h = Trainer(cfg, out_dir=sys.argv[2]).train()
ev = [r["eval/return"] for r in h if "eval/return" in r]
print("RESULT", json.dumps({"final": sum(ev[-3:]) / len(ev[-3:]), "curve": ev}))
"""


def run(code_dir, args):
    out = tempfile.mkdtemp(prefix="verify_")
    p = subprocess.run([sys.executable, "-c", RUNNER, code_dir, out] + args + ["--verbose", "0"],
                       capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    raise RuntimeError(p.stderr[-3000:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--preset", default="quick")
    a = ap.parse_args()
    variants = {
        "baseline": (os.path.join(HERE, "baseline"), []),
        "shipped": (ROOT, []),
        "shipped --norm-adv false": (ROOT, ["--norm-adv", "false"]),
    }
    jobs = {}
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        for name, (d, extra) in variants.items():
            for s in a.seeds:
                jobs[(name, s)] = ex.submit(run, d, ["--preset", a.preset, "--seed", str(s)] + extra)
        res = {k: f.result()["final"] for k, f in jobs.items()}

    print(f"preset {a.preset}, final eval return (mean of last 3 evals)")
    print(f"{'variant':<28}" + "".join(f"{'s' + str(s):>8}" for s in a.seeds) + f"{'mean':>8}")
    means = {}
    for name in variants:
        vals = [res[(name, s)] for s in a.seeds]
        means[name] = sum(vals) / len(vals)
        print(f"{name:<28}" + "".join(f"{v:8.1f}" for v in vals) + f"{means[name]:8.1f}")
    worst_base = min(res[("baseline", s)] for s in a.seeds)
    best_ship = max(res[("shipped", s)] for s in a.seeds)
    drop = 1 - means["shipped"] / means["baseline"]
    print(f"shipped is {drop:.0%} below baseline; worst baseline seed {worst_base:.1f}, best shipped seed {best_ship:.1f}")
    ok = worst_base > best_ship + 5
    print("OK" if ok else "NOT SEPARATED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
