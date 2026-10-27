"""Proves the problem discriminates: shipped code and the in-memory fix fail the replay; the durable fix passes."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
want = {ROOT: False, os.path.join(HERE, "in_memory"): False, os.path.join(HERE, "durable"): True}
bad = 0
for code, should_pass in want.items():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "replay.py"), "--code", code], capture_output=True, text=True)
    passed = r.returncode == 0
    print(f"{os.path.relpath(code, ROOT) or 'shipped'}: replay {'passes' if passed else 'fails'} (expected {'pass' if should_pass else 'fail'})")
    bad += passed != should_pass
sys.exit(1 if bad else 0)
