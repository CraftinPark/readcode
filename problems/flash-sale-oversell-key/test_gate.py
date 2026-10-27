"""Gate for the flash-sale problem: the shipped code oversells with several
worker processes, never with one, and the fixed inventory.py never oversells.

Runs the problem's own simulate.py in a copy of the problem folder, so what is
proven is exactly what the candidate can run. Each run takes a few seconds.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PROBLEM = HERE.parent / "flash-sale-oversell"
SALE = ["--buyers", "300", "--capacity", "150"]


def copy(tmp_path, fixed=False):
    dst = tmp_path / "problem"
    shutil.copytree(PROBLEM, dst, ignore=shutil.ignore_patterns("__pycache__"))
    if fixed:
        shutil.copy(HERE / "fixed" / "inventory.py", dst / "tickets" / "inventory.py")
    return dst


def confirmed(folder, workers, seed):
    out = subprocess.run([sys.executable, "simulate.py", "--workers", str(workers), "--seed", str(seed), *SALE],
                         cwd=folder, capture_output=True, text=True, timeout=300, check=True).stdout
    return int(re.search(r"confirmed seats (\d+)", out).group(1))


def test_one_worker_never_oversells(tmp_path):
    assert confirmed(copy(tmp_path), 1, seed=1) == 150


def test_shipped_code_oversells_with_several_workers(tmp_path):
    folder = copy(tmp_path)
    runs = [confirmed(folder, 8, seed) for seed in (1, 2, 3)]
    assert max(runs) > 150, runs


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_fixed_code_never_oversells(tmp_path, seed):
    assert confirmed(copy(tmp_path, fixed=True), 8, seed) == 150
