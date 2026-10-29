"""Runs the pricing service locally, the same build as production. It's owned by the catalogue team and we only
get the compiled build (vendor/priced.pyc).

    python pricing.py              # listens on http://127.0.0.1:8765, logs requests to pricing.log
    python pricing.py --port 8766

Endpoints: GET /price?sku=JKT-104 -> {"sku": ..., "price": ..., "currency": "GBP"};  GET /health
"""
import argparse
import importlib.machinery
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8765)
args = ap.parse_args()
loader = importlib.machinery.SourcelessFileLoader("priced", os.path.join(HERE, "vendor", "priced.pyc"))
spec = importlib.util.spec_from_loader("priced", loader)
priced = importlib.util.module_from_spec(spec)
loader.exec_module(priced)
priced.serve(args.port, os.path.join(HERE, "pricing.log"))
