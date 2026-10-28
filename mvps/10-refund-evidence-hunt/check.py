"""The on-call check for the ticket: replays the two refund webhooks Paylane sent for the bakery's charge
(exactly as they reached production: headers from data/gateway.log, bodies from data/events.jsonl) into a
fresh store, and checks the ledger says 8.00 EUR refunded.

    python check.py
"""
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ledger import receiver, reconcile  # noqa: E402
from ledger.store import Store  # noqa: E402

CHARGE = "ch_7Q4kd82Lm"

records = [json.loads(line) for line in open(os.path.join(HERE, "data", "events.jsonl"), encoding="utf-8")]
mine = [r for r in records if r["event"]["data"].get("charge_id") == CHARGE]
wanted = {r["request_id"] for r in mine}
headers = {}
for line in open(os.path.join(HERE, "data", "gateway.log"), encoding="utf-8"):
    m = re.search(r" req=(\S+) POST /webhooks/paylane \d+ headers=(.*)$", line)
    if m and m.group(1) in wanted:
        headers[m.group(1)] = json.loads(m.group(2))

store = Store(tempfile.mkdtemp())
for r in mine:
    receiver.handle(headers[r["request_id"]], json.dumps(r["event"]).encode(), store, now=r["received_at"])
got = reconcile.refund_totals(store).get(CHARGE, 0)
print(f"{CHARGE}: ledger says {got / 100:.2f} EUR refunded (merchant refunded 5.00 + 3.00 = 8.00)")
sys.exit(0 if got == 800 else 1)
