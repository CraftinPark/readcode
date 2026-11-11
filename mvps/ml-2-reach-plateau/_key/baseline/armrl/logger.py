"""Tiny CSV logger. We dropped tensorboard in the refactor (the cluster image
doesn't have it and nobody looked at it anyway).
"""
import csv
import json
import os


class CSVLogger:
    def __init__(self, path, fields=None):
        self.path = path
        self.fields = fields
        self._f = None
        self._w = None

    def log(self, row):
        if self._w is None:
            self.fields = self.fields or list(row.keys())
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            self._f = open(self.path, "w", newline="")
            self._w = csv.DictWriter(self._f, fieldnames=self.fields, extrasaction="ignore")
            self._w.writeheader()
        self._w.writerow({k: _fmt(row.get(k, "")) for k in self.fields})
        self._f.flush()

    def close(self):
        if self._f:
            self._f.close()


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4f}"
    return v


def dump_config(cfg, path):
    d = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(cfg).items()}
    with open(path, "w") as f:
        json.dump(d, f, indent=2)


class ConsoleLog:
    def __init__(self, verbose=1):
        self.verbose = verbose
        self._header_done = False

    def row(self, it, n_iters, steps, train_ret, eval_ret, stats, sps):
        if self.verbose < 1:
            return
        if not self._header_done:
            print(f"{'iter':>9} {'steps':>8} {'train_ret':>9} {'eval_ret':>8} "
                  f"{'v_loss':>8} {'expl_var':>8} {'kl':>7} {'sps':>6}")
            self._header_done = True
        ev = "" if eval_ret is None else f"{eval_ret:8.2f}"
        print(f"{it:>4}/{n_iters:<4} {steps:>8} {train_ret:9.2f} {ev:>8} "
              f"{stats.get('loss/value', 0):8.4f} {stats.get('explained_var', 0):8.3f} "
              f"{stats.get('approx_kl', 0):7.4f} {sps:6.0f}")
