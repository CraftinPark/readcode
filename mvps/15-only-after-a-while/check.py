"""Checkout smoke test: starts a fresh pricing service on a spare port and quotes five baskets.

    python check.py
"""
import importlib.machinery
import importlib.util
import os
import socket
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
loader = importlib.machinery.SourcelessFileLoader("priced", os.path.join(HERE, "vendor", "priced.pyc"))
spec = importlib.util.spec_from_loader("priced", loader)
priced = importlib.util.module_from_spec(spec)
loader.exec_module(priced)

s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
srv = priced.make_server(port, priced.Pricing())
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["PRICING_URL"] = f"http://127.0.0.1:{port}"

from shop import checkout  # noqa: E402

CASES = [
    ([("TEE-001", 2)], 2 * 1299 + 399),
    ([("JKT-104", 1)], 12999),
    ([("STKR-01", 3), ("PIN-03", 1)], 3 * 85 + 350 + 399),
    ([("GIFT-25", 2)], 5000),
    ([("HOOD-07", 1), ("SOCK-3P", 1)], 4599 + 999),
]
bad = 0
for items, want in CASES:
    got = checkout.quote(items)
    ok = got == want
    bad += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {items}: {got} (want {want})")
srv.shutdown()
print("all ok" if not bad else f"{bad} failed")
sys.exit(1 if bad else 0)
