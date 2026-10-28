"""Generates data/events.jsonl and data/gateway.log: one week of production traffic (deterministic).

The hidden truth: accounts on Paylane API version 2025-09 get `amount_refunded` as the charge's CUMULATIVE
refunded total; accounts on 2024-06 get the amount of this refund. The version is only in the
Paylane-Version request header, which only the gateway log keeps. acct_M9 upgrades mid-week.

    python _key/gen_data.py
"""
import datetime as dt
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data")
R = random.Random(20261026)
START = dt.datetime(2026, 10, 19, tzinfo=dt.timezone.utc)
END = START + dt.timedelta(days=7)
UPGRADE_M9 = dt.datetime(2026, 10, 22, 13, 40, tzinfo=dt.timezone.utc)
ACCOUNTS = {  # account: (currency, version or None = upgrades mid-week, charges this week)
    "acct_7Q": ("eur", "2025-09", 190), "acct_K2": ("usd", "2025-09", 260), "acct_M9": ("usd", None, 240),
    "acct_A1": ("usd", "2024-06", 300), "acct_B4": ("usd", "2024-06", 210), "acct_C8": ("gbp", "2024-06", 170),
    "acct_D3": ("usd", "2024-06", 280), "acct_F6": ("eur", "2024-06", 150),
}
ALNUM = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def rid(prefix, n=10):
    return prefix + "".join(R.choice(ALNUM) for _ in range(n))


def iso(t):
    return t.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def version(acct, t):
    v = ACCOUNTS[acct][1]
    return v or ("2025-09" if t >= UPGRADE_M9 else "2024-06")


def rand_time(lo=START, hi=END):
    return lo + dt.timedelta(seconds=R.uniform(0, (hi - lo).total_seconds()))


events = []  # [created, acct, type, data]


def add_refunds(acct, cur, charge_id, created, parts):
    t = created
    total = 0
    for p in parts:
        t = t + dt.timedelta(minutes=R.uniform(20, 60 * 30))
        if t >= END:
            return
        total += p
        events.append([t, acct, "charge.refunded", {"charge_id": charge_id, "refund_id": rid("re_"),
                                                    "amount_refunded": p, "currency": cur, "_total": total}])


for acct, (cur, _, n) in ACCOUNTS.items():
    for _ in range(n):
        created = rand_time(hi=END - dt.timedelta(hours=2))
        amount = R.choice([R.randint(3, 40) * 50, R.randint(300, 12000)])
        charge_id = "ch_" + acct[-2:] + rid("", 9)
        events.append([created, acct, "charge.succeeded", {"charge_id": charge_id, "amount": amount, "currency": cur}])
        roll = R.random()
        if roll < 0.08:
            add_refunds(acct, cur, charge_id, created, [amount])
        elif roll < 0.13 and amount >= 200:
            k = R.choice([2, 2, 2, 3])
            cuts = sorted(R.sample(range(1, amount // 50), min(k - 1, amount // 50 - 1)))
            edges = [0] + [c * 50 for c in cuts] + [amount]
            parts = [b - a for a, b in zip(edges, edges[1:])]
            if R.random() < 0.6 and len(parts) > 1:
                parts = parts[:-1]  # partly refunded, not all of it
            add_refunds(acct, cur, charge_id, created, parts)
    for _ in range(n // 3):
        events.append([rand_time(), acct, "customer.updated",
                       {"customer_id": rid("cus_"), "fields": R.sample(["email", "address", "phone", "name"], 2)}])
    for d in range(7):
        events.append([START + dt.timedelta(days=d, hours=2, minutes=R.randint(0, 50)), acct, "payout.paid",
                       {"payout_id": rid("po_"), "amount": R.randint(20000, 900000), "currency": cur}])

# The ticket's charge: bakery, 10.00 EUR, refunded 5.00 then 3.00.
t0 = dt.datetime(2026, 10, 23, 9, 2, 41, tzinfo=dt.timezone.utc)
events.append([t0, "acct_7Q", "charge.succeeded", {"charge_id": "ch_7Q4kd82Lm", "amount": 1000, "currency": "eur"}])
events.append([t0 + dt.timedelta(hours=1, minutes=10), "acct_7Q", "charge.refunded",
               {"charge_id": "ch_7Q4kd82Lm", "refund_id": "re_Hq72mXs0", "amount_refunded": 500, "currency": "eur",
                "_total": 500}])
events.append([t0 + dt.timedelta(hours=7, minutes=45), "acct_7Q", "charge.refunded",
               {"charge_id": "ch_7Q4kd82Lm", "refund_id": "re_Lp39vNe4", "amount_refunded": 300, "currency": "eur",
                "_total": 800}])

truth = {}
deliveries = []  # (received, request_id, headers, raw body)
UA = ["Paylane-Webhooks/2.3 (+https://paylane.example/webhooks)", "Paylane-Webhooks/2.4 (+https://paylane.example/webhooks)"]
for created, acct, typ, data in sorted(events, key=lambda e: e[0]):
    v = version(acct, created)
    if typ == "charge.refunded":
        total = data.pop("_total")
        truth[data["charge_id"]] = total
        if v == "2025-09":
            data["amount_refunded"] = total
    body = {"id": rid("evt_", 14), "type": typ, "created": int(created.timestamp()), "account": acct, "data": data}
    raw = json.dumps(body)
    delay = R.uniform(0.3, 9)
    if R.random() < 0.02:
        delay += R.uniform(600, 5400)  # stuck in Paylane's retry queue: arrives after later events
    tries = 2 if R.random() < 0.025 else 1  # our 10 s timeout tripped; Paylane redelivers the same event
    for i in range(tries):
        recv = created + dt.timedelta(seconds=delay + i * R.uniform(30, 300))
        req = "r_" + "".join(R.choice("0123456789abcdef") for _ in range(12))
        headers = {"Host": "hooks.ledgerline.internal", "User-Agent": UA[created > START + dt.timedelta(days=3)],
                   "Content-Type": "application/json", "Content-Length": str(len(raw)),
                   "X-Forwarded-For": f"34.{R.randint(80, 99)}.{R.randint(0, 255)}.{R.randint(1, 254)}",
                   "X-Request-Id": req, "Paylane-Account": acct,
                   "Paylane-Signature": f"t={int(created.timestamp())},v1={R.getrandbits(128):032x}",
                   "Paylane-Version": v, "Traceparent": f"00-{R.getrandbits(128):032x}-{R.getrandbits(64):016x}-01"}
        deliveries.append((recv, req, headers, raw))

os.makedirs(OUT, exist_ok=True)
lines = []
with open(os.path.join(OUT, "events.jsonl"), "w", encoding="utf-8", newline="\n") as f:
    for recv, req, headers, raw in sorted(deliveries, key=lambda d: d[0]):
        f.write(json.dumps({"request_id": req, "received_at": iso(recv), "event": json.loads(raw)}) + "\n")
        lines.append((recv, f"{iso(recv)} INFO gw req={req} POST /webhooks/paylane 200 headers={json.dumps(headers)}"))

# Everything else the gateway logs.
t = START
while t < END:
    lines.append((t, f"{iso(t)} INFO gw req=- GET /healthz 200 ua=kube-probe/1.29"))
    t += dt.timedelta(seconds=120)
paths = ["GET /api/dashboard/refunds?account={a}", "GET /api/dashboard/charges?account={a}&page={p}",
         "POST /api/exports/month-end?account={a}", "GET /api/merchants/{a}", "POST /api/sessions"]
for _ in range(4200):
    t = rand_time()
    a = R.choice(list(ACCOUNTS))
    p = R.choice(paths).format(a=a, p=R.randint(1, 30))
    st = R.choice([200, 200, 200, 304, 401, 404, 499, 502])
    lines.append((t, f'{iso(t)} INFO gw req=r_{R.getrandbits(48):012x} {p} {st} ua="Mozilla/5.0" ms={R.randint(4, 900)}'))
for _ in range(160):
    t = rand_time()
    lines.append((t, R.choice([
        f"{iso(t)} WARN gw upstream ledger-api slow: p99={R.randint(800, 4000)}ms",
        f"{iso(t)} WARN gw db pool: {R.randint(18, 20)}/20 in use, waited {R.randint(50, 900)}ms",
        f"{iso(t)} ERROR gw upstream reset by peer (ledger-api), retrying",
        f"{iso(t)} INFO gw config reloaded (routes=14)"])))
with open(os.path.join(OUT, "gateway.log"), "w", encoding="utf-8", newline="\n") as f:
    for _, line in sorted(lines, key=lambda x: x[0]):
        f.write(line + "\n")
with open(os.path.join(HERE, "truth_week.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(truth, f, indent=0, sort_keys=True)
print(f"{len(deliveries)} deliveries, {len(lines)} gateway lines, {len(truth)} refunded charges")
