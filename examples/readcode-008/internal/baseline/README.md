# Delivery marketplace backend

Customers order from restaurants; couriers deliver; restaurants are paid weekly.
Payments go through an external provider that reports results by webhook.

```
market/
  app.py         HTTP API (FastAPI): customers, provider webhooks, operations staff
  orders.py      order lifecycle: place, accept, pick up, deliver, cancel
  pricing.py     cart -> priced order: lines, promo discount, delivery fee, tax
  payments.py    payments, refunds and provider webhook events
  dispatch.py    assigning orders to couriers
  payouts.py     weekly restaurant payouts
  catalog.py     restaurants, menus, opening hours
  money.py       cents arithmetic
  providers.py   the payment provider interface + an in-memory stand-in
  db.py          SQLite schema and transactions
  seed.py        demo data
tests/
  test_smoke.py  happy paths
```

Run the tests:

```
pip install fastapi httpx pytest tzdata
pytest
```

Order statuses: `placed -> accepted -> assigned -> picked_up -> delivered`, or `cancelled`.
Payment statuses: `pending -> paid | failed`, then possibly `refunded`.
All money is in cents. Opening hours are the restaurant's local time.
