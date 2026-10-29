"""Quote a basket against the running pricing service (staging, see README).

    python quote.py JKT-104 TEE-001:2      # sku or sku:qty
"""
import sys

from shop import checkout

items = []
for arg in sys.argv[1:]:
    sku, _, qty = arg.partition(":")
    items.append((sku, int(qty or 1)))
total = checkout.quote(items)
print(f"total: {total} pence (£{total / 100:.2f})")
