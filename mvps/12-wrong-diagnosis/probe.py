"""Read-only SQL against PRODUCTION (snapshot taken this morning, 2026-10-28 00:00 UTC). You get 5 queries in
total; results are capped at 40 rows. Production data is not in this folder.

    python probe.py "select count(*) from subscriptions"
"""
import importlib.machinery
import importlib.util
import os
import sys

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prod", "link.pyc")
loader = importlib.machinery.SourcelessFileLoader("link", path)
spec = importlib.util.spec_from_loader("link", loader)
link = importlib.util.module_from_spec(spec)
loader.exec_module(link)
if len(sys.argv) != 2:
    sys.exit(__doc__)
print(link.query(sys.argv[1]))
