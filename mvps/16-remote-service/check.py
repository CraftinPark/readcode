"""Checkout smoke test: quotes five baskets against the staging pricing service.

    python check.py
"""
import sys

from shop import checkout

CASES = [
    ([("TEE-001", 2)], 2 * 1299 + 399),
    ([("JKT-104", 1)], 12999),
    ([("STKR-01", 3), ("PIN-03", 1)], 3 * 85 + 350 + 399),
    ([("GIFT-25", 2)], 5000),
    ([("HOOD-07", 1), ("SOCK-3P", 1)], 4599 + 999),
]
bad = 0
for items, want in CASES:
    got = checkout.quote(items)
    ok = got == want
    bad += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {items}: {got} (want {want})")
print("all ok" if not bad else f"{bad} failed")
sys.exit(1 if bad else 0)
