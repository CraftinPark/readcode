"""Grades your tests by mutation testing: your tests must pass on promo.py, then each hidden mutant (a copy of
promo.py with one realistic slip) is run against them. Score = mutants your tests catch.

    python grade.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_key"))
from mutants import MUTANTS  # noqa: E402


def run_tests(promo_src, tests_path):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "promo.py"), "w").write(promo_src)
    shutil.copy(tests_path, os.path.join(d, "test_promo.py"))
    runner = "import test_promo as t\nfor n in dir(t):\n    if n.startswith('test_'): getattr(t, n)()"
    r = subprocess.run([sys.executable, "-c", runner], cwd=d, capture_output=True, text=True)
    return r.returncode == 0


def grade(tests_path):
    src = open(os.path.join(HERE, "promo.py")).read()
    if not run_tests(src, tests_path):
        print("Your tests fail on the real promo.py. Fix them first (a test that fails on correct code catches nothing).")
        return 0
    caught = 0
    for mid, what, old, new in MUTANTS:
        assert src.count(old) == 1, mid
        killed = not run_tests(src.replace(old, new), tests_path)
        caught += killed
        print(f"  {mid} {'caught' if killed else 'missed'}")
    print(f"score: {caught}/{len(MUTANTS)} slips caught")
    return caught


if __name__ == "__main__":
    grade(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "test_promo.py"))
