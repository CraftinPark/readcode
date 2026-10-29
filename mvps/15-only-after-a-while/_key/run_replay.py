"""Replays 3 hours of checkouts through a code dir's shop/ against the true pricing service on a fake clock (key
only). Prints JSON {"orders": n, "wrong": n, "errors": n, "examples": [...]}.

    python run_replay.py CODE_DIR
"""
import json
import os
import random
import socket
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import priced  # noqa: E402

code_dir = os.path.abspath(sys.argv[1])
sys.path.insert(0, code_dir)


class Clock:
    t = 1_793_000_000.0

    def __call__(self):
        return self.t


clock = Clock()
s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
srv = priced.make_server(port, priced.Pricing(clock))
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["PRICING_URL"] = f"http://127.0.0.1:{port}"

from shop import checkout  # noqa: E402

r = random.Random(15)
skus = list(priced.CATALOGUE)
start = clock.t
stats = {"orders": 0, "wrong": 0, "errors": 0, "examples": []}
while clock.t < start + 3 * 3600:
    clock.t += r.randint(10, 50)
    items = [(sku, r.randint(1, 3)) for sku in r.sample(skus, r.randint(1, 3))]
    sub = sum(q * priced.CATALOGUE[k] for k, q in items)
    want = sub + (0 if sub >= 5000 else 399)
    stats["orders"] += 1
    try:
        got = checkout.quote(items)
    except Exception as e:  # noqa: BLE001
        got = f"error: {type(e).__name__}"
        stats["errors"] += 1
    if got != want:
        stats["wrong"] += 1
        if len(stats["examples"]) < 3:
            stats["examples"].append({"minute": int((clock.t - start) // 60), "items": items, "charged": got,
                                      "want": want})
srv.shutdown()
print(json.dumps(stats))
