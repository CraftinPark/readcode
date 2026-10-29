"""Runs the pricing service as the player's "staging" (key only; the player never gets this file or priced.py).
Start one per gate run, right before the run, outside the player's folder.

    python _key/serve.py --port 8781 --log PATH
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
import priced  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, required=True)
ap.add_argument("--log")
a = ap.parse_args()
priced.serve(a.port, a.log)
