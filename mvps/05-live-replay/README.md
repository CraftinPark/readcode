# MVP 05: Live replay after "resolved" (Tier 2 idea)

*Idea: Tier 2 should test whether a fix lasts, not only whether you found the cause. After you say "resolved", a replay runs production-like traffic against your fix. AI-written MVP: an experiment, not shipped content (John's CLAUDE.md rule).*

## The ticket (what the player sees)

> **From:** Support. **Priority:** P1
>
> Since Friday about 40 customers were charged twice for one order. Most say "the Pay button spun, so I tapped it again". Refund them, fine, but make it stop.

The code is in `shop/` (`checkout.py` is the Pay button, `provider.py` the card provider client, `db.py` the shared database). In production every request can land on a different pod, and pods restart. Run `python unit_check.py` for the quick check on-call wrote. Fix the code, then say "resolved".

## What happens after "resolved"

`python replay.py` replays five scenarios: re-tap on the same pod, re-tap after a pod restart, a slow provider that charges but times out, a second real order from the same customer (must still be charged), and a provider that is slow on every tap. Score = scenarios that hold, read from the **provider's** ledger (what the card was really charged).

## Why it is built this way

The cause is easy (a new `request_id` per tap defeats the dedupe). The trap is the fix: remembering paid orders in the process passes `unit_check.py` but fails 3 of 5 replay scenarios, because the memory dies with the pod and a timeout leaves "unknown" behind. This is the "fix didn't last" failure (26.5% of failures in Incident-Arena) and the double charge our own gate agents got wrong.

## Key (`_key/`, never shown to the player)

- `_key/in_memory/`: the tempting fix. Passes `unit_check.py`; replay 2/5.
- `_key/durable/`: reference fix. Idempotency key per order, sent to the provider; replay 5/5.
- `python _key/check_key.py` proves the replay separates them (shipped and in-memory fail, durable passes).

Not done: gate it against Claude (3 fresh runs), a real Kubernetes replay (restarts and latency are simulated with subprocesses and an env var here).
