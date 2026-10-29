"""Checks the key: check.py passes on the shipped code; the replay fails the shipped code and every tempting fix,
and passes the reference.

    python _key/check_key.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import replay  # noqa: E402
import socket  # noqa: E402
import threading  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "src"))
import priced  # noqa: E402

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
srv = priced.make_server(port, priced.Pricing())
threading.Thread(target=srv.serve_forever, daemon=True).start()
env = dict(os.environ, PRICING_URL=f"http://127.0.0.1:{port}")

EXPECT = {"shipped": False, "float_only": False, "magnitude": False, "rounding": False, "reference": True}
ok = subprocess.run([sys.executable, os.path.join(ROOT, "check.py")], capture_output=True, cwd=ROOT, env=env).returncode == 0
print(f"check.py on shipped code: {'passes' if ok else 'FAILS'}")
good = ok
for name, want in EXPECT.items():
    d = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, "shop"), os.path.join(d, "shop"))
    if name != "shipped":
        shutil.copy(os.path.join(HERE, "variants", name + ".py"), os.path.join(d, "shop", "client.py"))
    print(f"[{name}]")
    got = replay.run(d)[0]
    good &= got == want
    print(f"  expected {'PASS' if want else 'FAIL'}: {'ok' if got == want else 'MISMATCH'}")
print("key ok" if good else "KEY BROKEN")
sys.exit(0 if good else 1)
