import os
import random
import time

import numpy as np
import torch


def seed_everything(seed, deterministic=True):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = deterministic


def linear_schedule(start, it, n_iters):
    """lr for iteration `it` (1-based), decays to 0 at the last iteration"""
    frac = 1.0 - (it - 1.0) / n_iters
    return frac * start


def discount_cumsum(x, discount):
    """old helper from the spinning-up port. nothing calls it anymore?"""
    out = np.zeros_like(x)
    run = 0.0
    for i in reversed(range(len(x))):
        run = x[i] + discount * run
        out[i] = run
    return out


class Timer:
    def __init__(self):
        self.t0 = time.time()
        self.marks = {}

    def mark(self, name):
        self.marks[name] = time.time() - self.t0

    def elapsed(self):
        return time.time() - self.t0


def run_dir(base, exp_name, seed):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    d = os.path.join(base, f"{exp_name}__s{seed}__{stamp}")
    os.makedirs(d, exist_ok=True)
    return d
