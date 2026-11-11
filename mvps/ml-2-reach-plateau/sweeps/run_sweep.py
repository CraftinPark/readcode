"""Random search over a few PPO knobs.

NOT PORTED to the new layout yet: still builds the old env API through
LegacyVecReach and passes overrides as argv. Works, but slow (one process
per trial, no parallelism). Priya ran reach_v3 with the pre-refactor
train_ppo.py, see best.json.

    python sweeps/run_sweep.py --trials 8 --steps 100000
"""
import argparse
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SPACE = {
    "lr": [3e-4, 5e-4, 1e-3, 2e-3],
    "gamma": [0.95, 0.97, 0.99],
    "gae-lambda": [0.9, 0.95, 0.98],
    "update-epochs": [4, 10],
    "n-minibatches": [4, 8],
    "ent-coef": [0.0, 0.001, 0.01],
}


def sample(rng):
    return {k: rng.choice(v) for k, v in SPACE.items()}


def run_trial(params, steps, seed):
    cmd = [sys.executable, os.path.join(ROOT, "train.py"),
           "--total-steps", str(steps), "--seed", str(seed), "--verbose", "1",
           "--exp-name", "sweep"]
    for k, v in params.items():
        cmd += ["--" + k, str(v)]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    score = None
    for line in out.stdout.splitlines():
        if line.startswith("final eval return"):
            score = float(line.rsplit(":", 1)[1])
    if score is None:
        print(out.stdout[-2000:])
        print(out.stderr[-2000:])
    return score


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=8)
    p.add_argument("--steps", type=int, default=100_000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", default=os.path.join(HERE, "results.jsonl"))
    a = p.parse_args()
    rng = random.Random(a.seed)
    best = None
    for i in range(a.trials):
        params = sample(rng)
        score = run_trial(params, a.steps, seed=1)
        print(i, params, score)
        with open(a.out, "a") as f:
            f.write(json.dumps({"params": params, "score": score}) + "\n")
        if score is not None and (best is None or score > best[1]):
            best = (params, score)
    print("best", best)


if __name__ == "__main__":
    main()
