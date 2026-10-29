"""Builds what the player gets: everything except _key/, the README cut before "## After", and _sim/ shipped
only as sourceless .pyc (compiled with the running Python, so run the copy with the same version).

    python _key/make_player_copy.py DEST
"""
import os
import py_compile
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
dest = os.path.abspath(sys.argv[1])
if os.path.exists(dest):
    raise SystemExit(f"{dest} exists")
shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns("_key", "__pycache__", ".captures_used",
                                                           ".probes_used", ".shots_used", ".git*"))
for d, _, files in os.walk(os.path.join(dest, "_sim")):
    for n in files:
        if n.endswith(".py"):
            src = os.path.join(d, n)
            py_compile.compile(src, cfile=src + "c", doraise=True, optimize=2)  # no docstrings
            os.remove(src)
readme = os.path.join(dest, "README.md")
text = open(readme, encoding="utf-8").read()
open(readme, "w", encoding="utf-8").write(text.split("\n## After")[0].rstrip() + "\n")
print(f"player copy at {dest}")
