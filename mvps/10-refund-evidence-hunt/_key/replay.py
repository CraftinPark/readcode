"""Hidden replay, run AFTER the player says "resolved" (never shown to the player): next week's webhook
traffic, delivered through the player's receiver into a fresh store, then reconciled. Each scenario's
refund totals are checked against Paylane's settlement report.

    python _key/replay.py --code DIR
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OLD, NEW = "2024-06", "2025-09"

# (name, account, charge amount, [(event id, api version, amount_refunded as sent)], true refunded total)
SCENARIOS = [
    ("the bakery again: two partial refunds", "acct_7Q", 2400, [("a1", NEW, 900), ("a2", NEW, 1500)], 1500),
    ("2024-06 merchant: two partial refunds", "acct_P5", 1000, [("b1", OLD, 200), ("b2", OLD, 500)], 700),
    ("2024-06 merchant: a refund delivered twice", "acct_P5", 900, [("c1", OLD, 300), ("c1", OLD, 300), ("c2", OLD, 100)], 400),
    ("2025-09 merchant: refunds arrive out of order", "acct_R7", 1200, [("d2", NEW, 600), ("d1", NEW, 250)], 600),
    ("merchant upgrades between two refunds", "acct_S2", 800, [("e1", OLD, 200), ("e2", NEW, 500)], 500),
    ("2024-06 merchant: two equal partial refunds", "acct_T4", 600, [("f1", OLD, 150), ("f2", OLD, 150)], 300),
    ("new 2025-09 merchant: three partial refunds", "acct_V8", 1000, [("g1", NEW, 400), ("g2", NEW, 900), ("g3", NEW, 1000)], 1000),
    ("2025-09 merchant: a refund delivered twice", "acct_R7", 1500, [("h1", NEW, 700), ("h1", NEW, 700)], 700),
]

RUNNER = r'''
import json, sys, tempfile
from ledger import receiver, reconcile
from ledger.store import Store
out = []
for i, (name, acct, amount, refunds, _) in enumerate(json.loads(sys.argv[1])):
    store = Store(tempfile.mkdtemp())
    charge = f"ch_rp{i}"
    deliveries = [("ch%d" % i, refunds[0][1], {"type": "charge.succeeded", "data": {"charge_id": charge, "amount": amount, "currency": "usd"}})]
    for n, (eid, version, sent) in enumerate(refunds):
        deliveries.append((eid, version, {"type": "charge.refunded", "data": {"charge_id": charge, "refund_id": "re_" + eid,
                                                                             "amount_refunded": sent, "currency": "usd"}}))
    for k, (eid, version, ev) in enumerate(deliveries):
        # created follows when Paylane made the event (event ids sort in that order), not when it arrived
        made = 0 if k == 0 else 1 + sorted({r[0] for r in refunds}).index(eid)
        body = dict(ev, id="evt_rp%d_%s" % (i, eid), created=1793000000 + 60 * made, account=acct)
        raw = json.dumps(body).encode()
        headers = {"Host": "hooks.ledgerline.internal", "User-Agent": "Paylane-Webhooks/2.4 (+https://paylane.example/webhooks)",
                   "Content-Type": "application/json", "Content-Length": str(len(raw)), "X-Forwarded-For": "34.90.1.2",
                   "X-Request-Id": "r_rp%d_%d" % (i, k), "Paylane-Account": acct, "Paylane-Signature": "t=1793000000,v1=00",
                   "Paylane-Version": version, "Traceparent": "00-%032x-%016x-01" % (i, k)}
        receiver.handle(headers, raw, store, now="2026-11-0%dT10:%02d:00.000Z" % (2 + i % 5, k))
    out.append(reconcile.refund_totals(store).get(charge, 0))
print(json.dumps(out))
'''


def run(code_dir, verbose=True):
    r = subprocess.run([sys.executable, "-c", RUNNER, json.dumps(SCENARIOS)], cwd=code_dir,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        if verbose:
            print("replay crashed:\n" + r.stderr[-2000:])
        return 0
    got = json.loads(r.stdout.strip().splitlines()[-1])
    ok = 0
    for (name, *_, want), g in zip(SCENARIOS, got):
        ok += g == want
        if verbose:
            print(f"  {'ok  ' if g == want else 'FAIL'} {name}: ledger {g / 100:.2f}, settlement {want / 100:.2f}")
    if verbose:
        print(f"replay: {ok}/{len(SCENARIOS)} charges match the settlement report")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=os.path.dirname(HERE))
    score = run(ap.parse_args().code)
    sys.exit(0 if score == len(SCENARIOS) else 1)
