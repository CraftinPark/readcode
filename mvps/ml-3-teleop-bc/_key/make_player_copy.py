"""Build the player's copy: everything except _key/, runs/ and caches.

    python _key/make_player_copy.py DEST
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"_key", "runs", "__pycache__", ".pytest_cache"}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    dest = os.path.abspath(sys.argv[1])
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(ROOT, dest, ignore=lambda d, names: [n for n in names if n in SKIP])
    leaks = [os.path.join(dp, f) for dp, _, fs in os.walk(dest) for f in fs
             if f in ("answers.json", "SOLUTION.md", "gen_demos.py", "check_key.py")]
    if leaks:
        print("key files leaked:", leaks)
        return 1
    print(f"player copy at {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
