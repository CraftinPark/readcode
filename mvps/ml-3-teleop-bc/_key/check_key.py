"""Grade a solver's folder (Code tab) and/or comprehension answers (key only).

    python _key/check_key.py                         # self-check: shipped fails, reference passes, key scores 100%
    python _key/check_key.py --solution DIR          # run the hidden tests on DIR
    python _key/check_key.py --answers FILE.json     # grade {"Q1": "B", ...}
    add --fast to skip the closed-loop test (train + bench eval, ~40 s)

Uses pytest when it is installed, otherwise a built-in runner (the hidden
tests are plain functions with asserts).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TESTS = os.path.join(HERE, "hidden_tests", "test_hidden.py")
SKIP = {"_key", "runs", "__pycache__", ".pytest_cache"}

RUNNER = r"""
import importlib.util, os, sys, time, traceback
path = sys.argv[1]
spec = importlib.util.spec_from_file_location("test_hidden", path)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
failed = 0
for name in sorted(n for n in dir(mod) if n.startswith("test_")):
    t = time.time()
    try:
        getattr(mod, name)()
        print(f"PASS {name} ({time.time() - t:.1f}s)")
    except Exception as e:
        failed += 1
        msg = str(e).splitlines()[0] if str(e) else type(e).__name__
        print(f"FAIL {name}: {msg}")
sys.exit(1 if failed else 0)
"""


def run_hidden(solution: str, fast: bool = False) -> tuple[int, int, str]:
    """Returns (passed, total, output)."""
    env = dict(os.environ, SOLUTION_DIR=os.path.abspath(solution), PYTHONDONTWRITEBYTECODE="1")
    if fast:
        env["SKIP_CLOSED_LOOP"] = "1"
    try:
        import pytest  # noqa: F401
        cmd = [sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider", TESTS]
    except ImportError:
        cmd = [sys.executable, "-c", RUNNER, TESTS]
    r = subprocess.run(cmd, cwd=os.path.abspath(solution), env=env, capture_output=True, text=True)
    out = r.stdout + r.stderr
    passed = sum(1 for ln in out.splitlines() if ln.startswith("PASS"))
    failed = sum(1 for ln in out.splitlines() if ln.startswith("FAIL"))
    if passed + failed == 0:        # pytest summary lines
        passed = sum(1 for ln in out.splitlines() if ln.startswith("PASSED"))
        failed = sum(1 for ln in out.splitlines() if ln.startswith("FAILED"))
    return passed, passed + failed, out


def grade_answers(path: str) -> tuple[int, int, list]:
    with open(os.path.join(HERE, "answers.json")) as f:
        key = json.load(f)
    with open(path) as f:
        given = json.load(f)
    rows, right = [], 0
    for qid, k in key.items():
        got = str(given.get(qid, "")).strip().upper()
        ok = got == k["answer"]
        right += ok
        rows.append((qid, got or "-", k["answer"], ok))
    return right, len(key), rows


def copy_project(dest: str, overlay: str | None = None) -> str:
    shutil.copytree(ROOT, dest, ignore=lambda d, names: [n for n in names if n in SKIP])
    if overlay:
        for dirpath, _, files in os.walk(overlay):
            for f in files:
                src = os.path.join(dirpath, f)
                rel = os.path.relpath(src, overlay)
                shutil.copy2(src, os.path.join(dest, rel))
    return dest


def self_check(fast: bool) -> int:
    bad = 0
    tmp = tempfile.mkdtemp(prefix="ml3_key_")
    try:
        shipped = copy_project(os.path.join(tmp, "shipped"))
        ref = copy_project(os.path.join(tmp, "reference"), os.path.join(HERE, "reference"))
        for name, d, want_all in [("shipped", shipped, False), ("reference", ref, True)]:
            p, n, out = run_hidden(d, fast)
            print(f"--- {name}: {p}/{n} hidden tests pass")
            print("\n".join("    " + ln for ln in out.splitlines() if ln.startswith(("PASS", "FAIL"))))
            if want_all and p != n:
                bad += 1
            if not want_all and p == n:
                bad += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    with open(os.path.join(ROOT, "comprehension.json")) as f:
        comp = json.load(f)
    with open(os.path.join(HERE, "answers.json")) as f:
        key = json.load(f)
    ids = [q["id"] for q in comp["questions"]]
    if ids != list(key):
        print(f"question ids differ: {ids} vs {list(key)}"); bad += 1
    for q in comp["questions"]:
        if set(q) - {"id", "prompt", "options"}:
            print(f"{q['id']}: unexpected fields {set(q) - {'id', 'prompt', 'options'}}"); bad += 1
        if key[q["id"]]["answer"] not in q["options"]:
            print(f"{q['id']}: key answer not among options"); bad += 1
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({k: v["answer"] for k, v in key.items()}, f)
    right, total, _ = grade_answers(f.name)
    os.unlink(f.name)
    print(f"--- comprehension key scores {right}/{total}")
    bad += right != total
    print("SELF-CHECK OK" if not bad else f"SELF-CHECK FAILED ({bad})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solution")
    ap.add_argument("--answers")
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    if not a.solution and not a.answers:
        return self_check(a.fast)
    code = 0
    if a.solution:
        p, n, out = run_hidden(a.solution, a.fast)
        print(out.strip())
        print(f"Code tab: {p}/{n} hidden tests pass -> {'PASS' if p == n else 'FAIL'}")
        code |= p != n
    if a.answers:
        right, total, rows = grade_answers(a.answers)
        for qid, got, want, ok in rows:
            print(f"  {qid}: {got} {'right' if ok else 'wrong (key ' + want + ')'}")
        print(f"Comprehension tab: {right}/{total}")
    return code


if __name__ == "__main__":
    sys.exit(main())
