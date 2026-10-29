"""Shipped code fails the GHZ check and the replay; the tempting fix (re-measure every field calib.json has)
passes the GHZ check but fails the replay; the reference (plus the Stark crosstalk table) passes both.
The key variants only hold the files they change; they are overlaid on a copy of the shipped folder."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import replay  # noqa: E402


def overlay(variant):
    work = tempfile.mkdtemp()
    for n in ("qc", "_sim", "check_ghz.py"):
        src = os.path.join(ROOT, n)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(work, n))
    if variant:
        shutil.copytree(os.path.join(HERE, variant), work, dirs_exist_ok=True)
    return work


bad = 0
for name, variant, ghz_should, replay_should in [("shipped", None, False, False),
                                                 ("recal_only (tempting hack)", "recal_only", True, False),
                                                 ("reference", "reference", True, True)]:
    work = overlay(variant)
    g = subprocess.run([sys.executable, "check_ghz.py"], cwd=work, capture_output=True, text=True)
    print(f"{name}:\n  check_ghz: {g.stdout.strip().splitlines()[-1]}")
    ok, _ = replay.run(work)
    bad += ((g.returncode == 0) != ghz_should) + (ok != replay_should)
    shutil.rmtree(work)
sys.exit(1 if bad else 0)
