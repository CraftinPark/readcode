"""Builds what the player gets: everything except _key/, the README cut before "## After", and _sim/ shipped
only as sourceless .pyc without docstrings (compiled with the running Python, so run the copy with the same
version, 3.14).

    python _key/make_player_copy.py DEST
"""
import os
import py_compile
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
dest = os.path.abspath(sys.argv[1])
if os.path.exists(dest):
    raise SystemExit(f"{dest} exists")
shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns("_key", "__pycache__", ".robot_episodes_used",
                                                           "robot_logs", ".git*"))
# hardware stand-in: neutral names for the hidden constants and state, then sourceless .pyc
RENAME = ["COMPUTE_BASE", "COMPUTE_JIT", "BUS_JIT", "BUS", "BIAS", "GYRO_NOISE", "ACC_NOISE", "VIB_K", "VIB_TC",
          "OBS_LAG", "TRIP_RMS", "TRIP_TC", "D2_DB", "bias", "vib", "jit", "latched", "have", "heat", "tripped",
          "trip_now", "t_trip", "comp", "send", "arrive", "d2sum", "d2n", "d2", "u1", "u2", "over", "fbx", "fbz",
          "ax_w", "az_w", "enc_off", "push_dw", "push_t"]
for d, _, files in os.walk(os.path.join(dest, "_sim")):
    for n in files:
        if n.endswith(".py"):
            src = os.path.join(d, n)
            text = open(src, encoding="utf-8").read()
            for i, name in enumerate(RENAME):
                text = re.sub(rf"{name}", f"k{i:02d}", text)
            open(src, "w", encoding="utf-8").write(text)
            py_compile.compile(src, cfile=src + "c", doraise=True, optimize=2)  # no docstrings
            os.remove(src)
readme = os.path.join(dest, "README.md")
text = open(readme, encoding="utf-8").read()
open(readme, "w", encoding="utf-8").write(text.split("\n## After")[0].rstrip() + "\n")
print(f"player copy at {dest}")
