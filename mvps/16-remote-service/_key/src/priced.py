"""Pricing service (key source; the player only gets vendor/priced.pyc).

Hidden truth: on start-up the service warms its cache from a snapshot whose prices are integer pence. Each entry
expires on its own schedule, 10 to ~57 minutes after start; an expired entry is refetched from the new catalogue
API, which sends prices in POUNDS (a float, or an int for whole-pound prices) and adds "source": "catalogue-v2".
Same field name, same currency code. The shop's client does int(body["price"]), so a £12.99 jacket costs 12p.
Nothing goes wrong in the first 10 minutes after a restart, which is why ops can't reproduce it on staging.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

CATALOGUE = {
    "JKT-104": 12999, "JKT-210": 8950, "TEE-001": 1299, "TEE-014": 1450, "HOOD-07": 4599, "SCRF-02": 2000,
    "HAT-11": 1875, "SOCK-3P": 999, "BELT-05": 2450, "BAG-20": 6000, "BOOT-09": 11950, "CAP-04": 1599,
    "GLV-08": 2275, "COAT-01": 24900, "STKR-01": 85, "PIN-03": 350, "GIFT-25": 2500, "GIFT-50": 5000,
    "WALL-06": 3499, "UMB-02": 1650,
}
# Order in which snapshot entries expire: one every 150 s, starting 600 s after start.
EXPIRY_ORDER = ["TEE-001", "GIFT-25", "SOCK-3P", "JKT-104", "STKR-01", "HOOD-07", "COAT-01", "CAP-04", "BAG-20",
                "TEE-014", "PIN-03", "JKT-210", "SCRF-02", "HAT-11", "GIFT-50", "BELT-05", "BOOT-09", "GLV-08",
                "WALL-06", "UMB-02"]
FIRST_EXPIRY = 600
STEP = 150
LIVE_TTL = 600


class Pricing:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.Lock()
        start = clock()
        self.cache = {}
        for i, sku in enumerate(EXPIRY_ORDER):
            self.cache[sku] = ({"sku": sku, "price": CATALOGUE[sku], "currency": "GBP"},
                               start + FIRST_EXPIRY + i * STEP)

    @staticmethod
    def _catalogue_v2(sku):
        p = CATALOGUE[sku]
        return {"sku": sku, "price": p // 100 if p % 100 == 0 else p / 100, "currency": "GBP",
                "source": "catalogue-v2"}

    def lookup(self, sku):
        if sku not in CATALOGUE:
            return None
        with self.lock:
            body, expires = self.cache[sku]
            now = self.clock()
            if now >= expires:
                body, expires = self._catalogue_v2(sku), now + LIVE_TTL
                self.cache[sku] = (body, expires)
            return dict(body)


def make_server(port, pricing, log=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/health":
                return self._send(200, {"ok": True})
            if u.path != "/price":
                return self._send(404, {"error": "not found"})
            sku = parse_qs(u.query).get("sku", [""])[0]
            body = pricing.lookup(sku)
            if body is None:
                return self._send(404, {"error": "unknown sku"})
            return self._send(200, body)

        def _send(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            if log:
                log.write(time.strftime("%H:%M:%S ") + (fmt % args) + "\n")
                log.flush()

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(port, log_path=None):
    log = open(log_path, "a", encoding="utf-8") if log_path else None
    srv = make_server(port, Pricing(), log)
    print(f"pricing listening on http://127.0.0.1:{port}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
