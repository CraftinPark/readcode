# MVP 16: Only after a while, remote (time-revealed bug behind a real service, aiming at Tier 2)

*MVP 15 failed the gate because the "black box" was a `.pyc` the player could load and run on a fake clock. Here the same pricing service runs as a separate server process outside the player's folder: no code, no restart, no clock to fast-forward. The only way to see the bug is to keep watching the live service for 10+ minutes. AI-written MVP: an experiment.*

## The ticket

> **From:** Support. **Priority:** P2
>
> Some customers are charged the wrong amount at checkout. It isn't every order, and we can't find a pattern by product. We refunded 14 last week and didn't keep the order numbers, sorry.
>
> **Ops, in the thread:** We can't reproduce it on staging. For what it's worth, it's always quiet right after a deploy, and when we restarted pricing on Tuesday the complaints stopped for a while.

The checkout is in `shop/` (`checkout.quote(items)` returns the total in pence; `client.py` calls the pricing service). The pricing service is owned by the catalogue team and runs on their machines; we don't have its code and can't restart it. Staging pricing, the same build as production, is at http://127.0.0.1:8765 (the deploy pipeline restarted it when this ticket was opened). `python quote.py JKT-104 TEE-001:2` quotes a basket against it. `python check.py` is the checkout smoke test.

Fix the checkout so every customer is charged the right amount. You may change anything in `shop/`. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

Same hidden behaviour and grader as MVP 15 (`_key/src/priced.py` is a copy): for the first 10 minutes after start the service answers from a warm cache in integer pence; then entries expire one SKU every 150 s and come back from `catalogue-v2` in pounds (`12.99`, or `25` for whole-pound prices) with `"source": "catalogue-v2"`. The client's `int(price)` charges 12p for a £12.99 T-shirt. `_key/replay.py --code DIR` runs 3 hours of checkouts on a fake clock; every order must be charged right.

What changed from MVP 15: the player gets no `vendor/`, no `pricing.py`, and a `check.py` that talks to staging over HTTP. The harness starts one service per gate run with `python _key/serve.py --port P --log PATH`, right before the run, from outside the player's folder. The gate prompt tells the player to work only inside its folder. That's the honour system here: someone who searches the machine can find `_key/`.

## Key (`_key/`)

The same variants as MVP 15: shipped 317 wrong of 367, `float_only` 147, `magnitude` 20, `rounding` 317, `reference` 0. `python _key/check_key.py` checks them and that `check.py` passes against a freshly started service.

## Gate result (2026-10-28): fails the gate, AI solves it 3 of 3

Opus 5.5, 3 fresh runs, each in a clean copy with its own staging service started just before the run. Run time 10.5–11.5 min each, much longer than any earlier gate run.

| Run | Replay | What it did |
|---|---|---|
| 1 | **0 wrong / 367, solved** | Polled staging in a background loop (about 9,000 requests in 10 min) until TEE-001 came back as `12.99` with `source: catalogue-v2`. Fixed the client to choose the unit from `source`, parse with `Decimal`, and refuse any format it doesn't know. |
| 2 | **0 wrong, solved** | Polled every SKU for several minutes (about 9,400 requests); same fix. |
| 3 | **0 wrong, solved** | Ran a background watcher and a monitor (about 34,000 requests); same fix. It also noted that a whole-pound `25` from `catalogue-v2` still means £25. |

All three took the ops hint ("quiet right after a deploy") to mean "it depends on uptime", and started a background poller on their own. The service's request logs show only HTTP traffic. I can't fully rule out that a run read `_key/` on disk, but none of the reports mentions it, and the timing (each found the switch just after minute 10) fits watching.

Lesson: Opus will wait when the ticket points at time. A behaviour that needs 10 minutes of observation isn't a barrier. It runs a background poller and checks back. Waiting isn't a human advantage. Together with MVP 15, this closes the "only after a while" path. A time-based design could still work only if the wait were much longer than an agent run can last (hours or days), and then the gate would need different tooling.
