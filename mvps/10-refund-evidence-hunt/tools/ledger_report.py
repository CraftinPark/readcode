"""What the merchant dashboard shows: charged and refunded per charge, from a store directory.

    python tools/ledger_report.py data              # every account
    python tools/ledger_report.py data acct_7Q      # one account
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ledger import reconcile  # noqa: E402
from ledger.store import Store  # noqa: E402

store = Store(sys.argv[1])
account = sys.argv[2] if len(sys.argv) > 2 else None
owner = {r["event"]["data"]["charge_id"]: r["event"]["account"] for r in store.records()
         if r["event"]["type"] == "charge.succeeded"}
charged = reconcile.charge_totals(store)
refunded = reconcile.refund_totals(store)
print(f"{'account':<9} {'charge':<14} {'charged':>9} {'refunded':>9}")
for charge_id in sorted(refunded, key=lambda c: (owner.get(c, ""), c)):
    if account and owner.get(charge_id) != account:
        continue
    print(f"{owner.get(charge_id, '?'):<9} {charge_id:<14} {charged.get(charge_id, 0) / 100:>9.2f} {refunded[charge_id] / 100:>9.2f}")
