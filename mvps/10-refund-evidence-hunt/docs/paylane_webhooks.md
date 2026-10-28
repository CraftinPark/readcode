# Paylane webhooks (copied from the Paylane docs portal, last updated 2024-06)

Paylane POSTs a JSON event to your endpoint. Respond 2xx within 10 s or the delivery is retried
(up to 3 days, exponential backoff). A retried delivery carries the same `id`.

```json
{
  "id": "evt_...",
  "type": "charge.refunded",
  "created": 1718000000,
  "account": "acct_...",
  "data": { ... }
}
```

| type | data |
|---|---|
| `charge.succeeded` | `charge_id`, `amount` (minor units), `currency` |
| `charge.refunded` | `charge_id`, `refund_id`, `amount_refunded` (minor units), `currency` |
| `customer.updated` | `customer_id`, `fields` |
| `payout.paid` | `payout_id`, `amount`, `currency` |

A charge can be refunded in several parts; each partial refund sends its own `charge.refunded` event.
Events are not guaranteed to arrive in order.
