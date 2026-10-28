"""Hidden replay, run AFTER the player declares the incident resolved (never shown to the player).
Every tap runs in its own pod process unless the scenario says otherwise; the provider may be slow.

    python replay.py --code DIR
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GOOD, GOOD2, BAD = "4242424242424242", "5555555555554444", "4000000000000002"

# (name, same_process, [(order_id, latency, card)], {order_id: captured charges expected}, orders that must end paid)
SCENARIOS = [
    ("re-tap, same pod", True, [(1, 0, GOOD), (1, 0, GOOD)], {1: 1}, [1]),
    ("re-tap on another pod", False, [(2, 0, GOOD), (2, 0, GOOD)], {2: 1}, [2]),
    ("charged but timed out, customer taps again", False, [(3, 3, GOOD), (3, 0, GOOD)], {3: 1}, [3]),
    ("two real orders", False, [(4, 0, GOOD), (5, 0, GOOD)], {4: 1, 5: 1}, [4, 5]),
    ("card declined, customer pays with another card", False, [(6, 0, BAD), (6, 0, GOOD2)], {6: 1}, [6]),
    ("declined, new card times out, taps again", False, [(7, 0, BAD), (7, 3, GOOD2), (7, 0, GOOD2)], {7: 1}, [7]),
    ("declined then another card, same pod", True, [(8, 0, BAD), (8, 0, GOOD2)], {8: 1}, [8]),
]


def run(code_dir, verbose=True):
    work = tempfile.mkdtemp()
    shutil.copytree(os.path.join(code_dir, "shop"), os.path.join(work, "shop"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.db"))
    shutil.copy(os.path.join(HERE, "pod.py"), work)
    env = dict(os.environ, SHOP_DB=os.path.join(work, "shop.db"), PROVIDER_DB=os.path.join(work, "provider.db"))
    shop = sqlite3.connect(env["SHOP_DB"])
    shop.execute("create table if not exists orders (id integer primary key, customer text not null, "
                 "amount_cents integer not null, status text not null default 'open')")
    for oid in range(1, 9):
        shop.execute("insert into orders (id, customer, amount_cents) values (?, 'ana', 4200)", (oid,))
    shop.commit()
    shop.close()

    held = 0
    tap = 0
    for name, same_process, taps, expected, must_pay in SCENARIOS:
        if same_process:
            calls = []
            for order_id, latency, card in taps:
                tap += 1
                calls.append(f"print(checkout.pay({order_id}, 'tap-{tap}', '{card}'))")
            code = "from shop import checkout\n" + "\n".join(calls)
            subprocess.run([sys.executable, "-c", code], cwd=work, env=env, capture_output=True, text=True)
        else:
            for order_id, latency, card in taps:
                tap += 1
                subprocess.run([sys.executable, "pod.py", "pay", str(order_id), f"tap-{tap}", card], cwd=work,
                               env=dict(env, PROVIDER_LATENCY=str(latency)), capture_output=True, text=True)
        ledger = sqlite3.connect(env["PROVIDER_DB"])
        shop = sqlite3.connect(env["SHOP_DB"])
        problems = []
        for order_id, want in expected.items():
            got = ledger.execute("select count(*) from charges where order_id = ? and result = 'captured'", (order_id,)).fetchone()[0]
            if got != want:
                problems.append(f"order {order_id} captured {got} time(s), expected {want}")
        for order_id in must_pay:
            st = shop.execute("select status from orders where id = ?", (order_id,)).fetchone()[0]
            if st != "paid":
                problems.append(f"order {order_id} is '{st}', customer could not pay")
        ledger.close()
        shop.close()
        held += not problems
        if verbose:
            print(f"  {'ok  ' if not problems else 'FAIL'} {name}" + ("" if not problems else ": " + "; ".join(problems)))
    if verbose:
        print(f"{held}/{len(SCENARIOS)} scenarios hold")
    return held == len(SCENARIOS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=HERE)
    sys.exit(0 if run(ap.parse_args().code) else 1)
