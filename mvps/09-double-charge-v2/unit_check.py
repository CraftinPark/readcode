"""The quick check on-call wrote: two taps in one process must charge once. Run: python unit_check.py"""
import os
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["SHOP_DB"] = os.path.join(tmp, "shop.db")
os.environ["PROVIDER_DB"] = os.path.join(tmp, "provider.db")

from shop import checkout, db, provider  # noqa: E402

conn = db.connect()
conn.execute("insert into orders (id, customer, amount_cents) values (1, 'ana', 4200)")
checkout.pay(1, "tap-1")
checkout.pay(1, "tap-2")
n = provider._ledger().execute("select count(*) from charges where order_id = 1 and result = 'captured'").fetchone()[0]
print(f"order 1 charged {n} time(s)")
sys.exit(0 if n == 1 else 1)
