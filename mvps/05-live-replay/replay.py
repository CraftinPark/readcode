"""Live replay, run AFTER you declare the incident resolved. You don't get to read this file
during the problem; it replays last Friday's traffic against your fix, the way production behaves:
every tap may land on a different pod, pods restart, and the provider has a slow minute.

    python replay.py            # against shop/
    python replay.py --code DIR # against another copy (used by the key check)
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# (name, [(order_id, provider_latency_seconds)...] taps in order, expected charges per order)
SCENARIOS = [
    ("re-tap, same pod", [(1, 0), (1, 0)], {1: 1}),
    ("re-tap after the pod restarted", [(2, 0), (2, 0)], {2: 1}),
    ("provider slow: charged but timed out, customer taps again", [(3, 3), (3, 0)], {3: 1}),
    ("same customer, a second real order", [(4, 0), (5, 0)], {4: 1, 5: 1}),
    ("provider slow on every tap", [(6, 3), (6, 3), (6, 0)], {6: 1}),
]


def run(code_dir):
    work = tempfile.mkdtemp()
    shutil.copytree(os.path.join(code_dir, "shop"), os.path.join(work, "shop"))
    shutil.copy(os.path.join(HERE, "pod.py"), work)
    env = dict(os.environ, SHOP_DB=os.path.join(work, "shop.db"), PROVIDER_DB=os.path.join(work, "provider.db"))
    shop = sqlite3.connect(env["SHOP_DB"])
    shop.executescript("create table if not exists orders (id integer primary key, customer text not null, amount_cents integer not null, status text not null default 'open');")
    for oid in range(1, 7):
        shop.execute("insert into orders (id, customer, amount_cents) values (?, 'ana', 4200)", (oid,))
    shop.commit()

    failures = 0
    tap = 0
    for name, taps, expected in SCENARIOS:
        for i, (order_id, latency) in enumerate(taps):
            tap += 1
            pod_env = dict(env, PROVIDER_LATENCY=str(latency))
            if name == "re-tap, same pod":
                # both taps in one process
                code = f"from shop import checkout; print(checkout.pay({order_id}, 'tap-{tap}')); print(checkout.pay({order_id}, 'tap-{tap}b'))"
                subprocess.run([sys.executable, "-c", code], cwd=work, env=pod_env, capture_output=True, text=True)
                break
            subprocess.run([sys.executable, "pod.py", "pay", str(order_id), f"tap-{tap}"], cwd=work, env=pod_env, capture_output=True, text=True)
        ledger = sqlite3.connect(env["PROVIDER_DB"])
        ok = True
        for order_id, want in expected.items():
            got = ledger.execute("select count(*) from charges where order_id = ?", (order_id,)).fetchone()[0]
            if got != want:
                ok = False
                print(f"  FAIL {name}: order {order_id} charged {got} time(s), expected {want}")
        if ok:
            print(f"  ok   {name}")
        failures += not ok
    print(f"{len(SCENARIOS) - failures}/{len(SCENARIOS)} scenarios hold")
    return failures == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=HERE)
    sys.exit(0 if run(ap.parse_args().code) else 1)
