# MVP 09: Double charges, v2 (aiming at Tier 2)

*A harder MVP 05. All three Opus 5.5 gate runs on 05 shipped one provider key per order. That stops double charges, but the provider replays the first result for a key, declines included, so a customer whose card was declined can never pay with another card. This version checks that. AI-written MVP: an experiment.*

## The ticket

> **From:** Support. **Priority:** P1
>
> Since Friday about 40 customers were charged twice for one order. Most say "the Pay button spun, so I tapped it again". Refund them, fine, but make it stop.

The code is in `shop/`: `checkout.py` is the Pay button, `provider.py` is the card provider client (read its notes on how the provider behaves), and `db.py` is the shared database. `pod.py` handles one request the way a production pod does. Run `python unit_check.py` for the quick check on-call wrote. Fix the code, then say "resolved".

## After "resolved" (hidden from the player)

`replay.py` runs 7 scenarios, each tap in its own pod process unless noted: re-taps, a timeout after capture, two real orders, a decline followed by another card (on separate pods and on one pod), and a decline followed by a new card that times out. It passes only if every order is captured exactly once and every order that should be paid is paid.

## Key (`_key/`)

- `_key/order_key/`: one key per order (what the 05 gate runs shipped). Replay 4/7: three declined customers can't pay.
- `_key/reference/`: one key per payment attempt. Declines go in the shared DB and start a new attempt. Replay 7/7.
- `python _key/check_key.py` checks shipped (3/7), order_key and reference.

## Gate result (2026-10-27): fails the gate, AI solves it

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, no `replay.py`): **3 of 3 solved**, all 7/7 on the hidden replay. Every run read the provider notes, saw that a key replays declines, and built a per-attempt key. Two runs went further than the reference: they claim the order atomically in the DB and check unsettled charges with `provider.lookup`. Run time 71-96 s each. One run broke the folder rule once: it wrote a test script one level up, then deleted it.

Lesson: a trap that is written down in the code (the provider docstring) is not a trap for AI. To pass the gate, the edge case has to come from knowledge the problem does not state, or from evidence the player must go and find.
