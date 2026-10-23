# Payments service

Charges, refunds and webhooks for merchant accounts. Several servers run the
same app against one database; a background worker delivers webhooks.

```
payments/
  app.py            HTTP API (FastAPI): charges, refunds, listing
  idempotency.py    Idempotency-Key handling for POST /charges
  card_network.py   card network interface + an in-memory fake
  webhooks.py       event outbox and delivery with retries
  db.py             SQLite schema, connections, transactions
tests/
  test_smoke.py     happy-path tests
```

Run the tests:

```
pip install fastapi httpx pytest
pytest
```

API summary:

| Endpoint | Notes |
|---|---|
| `POST /charges` | `amount` (minor units), `currency`, `payment_method`. Optional `Idempotency-Key` header, kept 24 hours. |
| `GET /charges/{id}` | |
| `GET /charges?limit&starting_after` | Newest first. |
| `POST /charges/{id}/refunds` | Optional `amount`; defaults to what is left. |

Webhooks: `charge.succeeded`, `charge.failed`, `charge.refunded`, signed with
the endpoint secret (`Signature: t=...,v1=...`). Any non-2xx response is
retried with backoff for up to 3 days.
