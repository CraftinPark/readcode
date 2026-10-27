"""Accepts or rejects a submitted problem. The contract an author must meet (MVPs 03-07 all meet it):

- README.md: what the player sees (the ticket, how to run the code).
- _key/check_key.py: exits 0 only if the shipped code FAILS and the author's reference fix PASSES
  (proof by test: the problem has a real, checkable answer). Ideally also a tempting wrong fix that fails.
- Nothing that leaks: no "BUG"/"FIXME"/"the fix" hints in player files, no _key import from player code.

    python validate_submission.py DIR [DIR ...]
"""
import os
import re
import subprocess
import sys
import time

HINTS = re.compile(r"\b(BUG|FIXME|XXX|the fix is|seeded)\b")


def validate(d):
    problems = []
    if not os.path.isfile(os.path.join(d, "README.md")):
        problems.append("no README.md")
    key = os.path.join(d, "_key", "check_key.py")
    tempting = 0
    if not os.path.isfile(key):
        problems.append("no _key/check_key.py (proof by test)")
        took = 0.0
    else:
        t0 = time.time()
        r = subprocess.run([sys.executable, key], cwd=d, capture_output=True, text=True, timeout=600)
        took = time.time() - t0
        if r.returncode != 0:
            problems.append("check_key.py fails: shipped code must fail and the reference must pass\n" + r.stdout[-400:])
        tempting = sum(1 for line in r.stdout.splitlines() if re.search(r"hack|in_memory|more heart", line))
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in ("_key", "_sim", "out", "__pycache__")]
        for n in files:
            if n.endswith((".py", ".md", ".c", ".h", ".js")) and n != "README.md":
                text = open(os.path.join(root, n), encoding="utf-8", errors="replace").read()
                if HINTS.search(text):
                    problems.append(f"hint word in {os.path.relpath(os.path.join(root, n), d)}")
                if re.search(r"^\s*(from|import)\s+_key", text, re.M) and n != "grade.py":
                    problems.append(f"player file imports _key: {os.path.relpath(os.path.join(root, n), d)}")
    return problems, took, tempting


if __name__ == "__main__":
    bad = 0
    for d in sys.argv[1:]:
        problems, took, tempting = validate(d)
        name = os.path.basename(os.path.abspath(d))
        if problems:
            bad += 1
            print(f"REJECT {name}")
            for p in problems:
                print(f"  - {p}")
        else:
            extra = f", tempting wrong fix checked" if tempting else ", no tempting wrong fix (weaker)"
            print(f"ACCEPT {name} (key check {took:.1f}s{extra})")
    sys.exit(1 if bad else 0)
