# MVP 15: Only after a while (behaviour that shows only with time, aiming at Tier 2)

*MVP 14 passed the gate, but it may be too hard for people too. This tries a path a person can clearly solve: the cause isn't in the code, the docs or any data, and it doesn't take clever experiment design. It shows up only if you keep the service running and watch it for more than 10 minutes. Gate runs take about 2 minutes. AI-written MVP: an experiment.*

## The ticket

> **From:** Support. **Priority:** P2
>
> Some customers are charged the wrong amount at checkout. It isn't every order, and we can't find a pattern by product. We refunded 14 last week and didn't keep the order numbers, sorry.
>
> **Ops, in the thread:** We can't reproduce it on staging. For what it's worth, it's always quiet right after a deploy, and when we restarted pricing on Tuesday the complaints stopped for a while.

The checkout is in `shop/` (`checkout.quote(items)` returns the total in pence; `client.py` calls the pricing service). The pricing service is owned by the catalogue team, and we only get its compiled build (`vendor/priced.pyc`). `python pricing.py` runs it locally, the same build as production, on http://127.0.0.1:8765. `python quote.py JKT-104 TEE-001:2` quotes a basket against it. `python check.py` is the checkout smoke test.

Fix the checkout so every customer is charged the right amount. You may change anything in `shop/`; the pricing service isn't ours to change. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

`_key/replay.py --code DIR` runs 3 hours of checkouts (about 370 orders) through the player's `shop/` against the real pricing service on a fake clock. Every order must be charged the right amount.

What's really going on (`_key/src/priced.py`; nothing in the code, docs or ticket says it):
- On start-up the service warms its cache from a snapshot with prices in **integer pence**: `{"sku": "TEE-001", "price": 1299, "currency": "GBP"}`.
- Each cached entry expires on its own schedule: the first 10 minutes after start, then one SKU every 150 s, the last after about 57 minutes. An expired entry is refetched from the new catalogue API, which sends **pounds**: `{"sku": "TEE-001", "price": 12.99, "currency": "GBP", "source": "catalogue-v2"}`. Whole-pound prices arrive as ints (`GIFT-25` → `25`).
- The client does `int(body["price"])`, so a £12.99 T-shirt costs 12p. A restart warms the cache again, which is why it's "quiet after a deploy".
- `check.py` starts a fresh service each time, so it always passes. A player who tests for 2 minutes sees nothing wrong. A player who leaves the service running and quotes again after 10+ minutes sees `TEE-001` at 12p with a new `source` field.

## Key (`_key/`)

| Variant (`_key/variants/`) | What it does | Replay (367 orders) |
|---|---|---|
| shipped | `int(price)` | 317 wrong |
| `float_only` | treat a float as pounds | 147 wrong (whole-pound prices arrive as ints) |
| `magnitude` | treat anything under 1000 as pounds | 20 wrong (cheap items in pence, e.g. socks at 999p) |
| `rounding` | `int(round(price))` | 317 wrong |
| `reference` | `source == "catalogue-v2"` → `Decimal(str(price)) * 100` | 0 wrong |

`python _key/check_key.py` checks all five and that `check.py` passes on the shipped code. `vendor/priced.pyc` is compiled from `_key/src/priced.py` with docstrings stripped (`python -c "import py_compile; py_compile.compile('_key/src/priced.py', cfile='vendor/priced.pyc', optimize=2)"`). As in MVPs 12 and 14, the black box relies on the honour system: someone who disassembles the `.pyc` can read the expiry schedule and the `catalogue-v2` format.

## Gate result (2026-10-28): fails the gate, AI solves it 3 of 3

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, player README only, its own port). Runs 2 and 3 were cut off by the account's session limit just before writing their summaries, but their `shop/` was already finished, so all three are graded.

| Run | Replay | How it found the cause |
|---|---|---|
| 1 | **0 wrong / 367, solved** | Loaded `priced.pyc` the way `check.py` does, read `EXPIRY_ORDER` and `_catalogue_v2`, and drove `Pricing(clock=...)` with a fake clock. Fix: `Decimal(str(price)) * 100` when `source == "catalogue-v2"`, and an error for any unknown format. 55 s. |
| 2 | **0 wrong, solved** | Same approach (it deleted its scratch scripts). It checked all 20 SKUs "at every point in time". |
| 3 | **0 wrong, solved** | `scratch/inspect_.py` printed the module's constants and ran `dis.dis(p.Pricing)`; `fakeclock.py` fast-forwarded it. |

No run waited in real time. All three skipped the wait: they opened the black box and fast-forwarded its clock. The design made that easy. `check.py` shows how to load the `.pyc` and build `Pricing()` in-process, and the clock is a constructor argument. A Python module loaded in-process isn't a black box. Unlike MVPs 12 and 14, where Opus left the compiled file alone, the ticket here gave it no other way in, so it read the bytecode.

Lesson: hiding behaviour behind time only works if the clock and the code are out of reach, for example a separate process the player can't import, ideally on another machine. Even then, the ops hint ("quiet after a deploy") points straight at a cache expiry, which Opus would probably test for by waiting or by restarting on purpose. A time-only design needs a real remote service, which this harness doesn't have.
