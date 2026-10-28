"""Builds prod/snapshot.bin (production at 2026-10-28, encrypted) and prod/link.pyc (sourceless).

    python _key/gen_prod.py
"""
import importlib.util
import os
import py_compile
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world  # noqa: E402

spec = importlib.util.spec_from_file_location("link_src", os.path.join(HERE, "src", "link.py"))
link = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link)
PROD = os.path.join(os.path.dirname(HERE), "prod")
conn, _ = world.build()
data = conn.serialize()
os.makedirs(PROD, exist_ok=True)
with open(os.path.join(PROD, "snapshot.bin"), "wb") as f:
    f.write(bytes(a ^ b for a, b in zip(data, link._stream(len(data)))))
py_compile.compile(os.path.join(HERE, "src", "link.py"), cfile=os.path.join(PROD, "link.pyc"), optimize=2)
print(f"snapshot {len(data)} bytes")
