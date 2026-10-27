"""Packs a problem folder into bundle.js for viewer.html (so the page works from file://, no server).

    python build_bundle.py ../01-big-repo-no-hint/out    # default
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "01-big-repo-no-hint", "out"))
files = {}
for root, dirs, names in os.walk(src):
    dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git"))
    for n in sorted(names):
        if n.endswith((".py", ".md", ".toml", ".ini", ".json", ".txt", ".sql")):
            p = os.path.join(root, n)
            files[os.path.relpath(p, src).replace(os.sep, "/")] = open(p, encoding="utf-8", errors="replace").read()
with open(os.path.join(HERE, "bundle.js"), "w", encoding="utf-8") as f:
    f.write("window.BUNDLE = " + json.dumps({"name": os.path.basename(src), "files": files}) + ";\n")
print(f"bundle.js: {len(files)} files from {src}")
