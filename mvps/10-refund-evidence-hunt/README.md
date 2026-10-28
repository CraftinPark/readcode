# MVP 10: Refunds that don't add up (evidence hunt, aiming at Tier 2)

*After 05, 06 and 09 all fell to Opus because the trap was written somewhere in the code, this one hides the edge case only in production data. Nothing in the code, the docs or the ticket says it. AI-written MVP: an experiment.*

## The ticket

> **From:** Support. **Priority:** P1, finance closes the month on Friday.
>
> The bakery (acct_7Q) says our dashboard shows charge ch_7Q4kd82Lm as €13.00 refunded. The charge was €10.00 and they refunded €5.00, then €3.00. Their accountant is asking questions. Please fix the refund ledger.

The webhook receiver and the refund ledger are in `ledger/`. `docs/paylane_webhooks.md` is our copy of the card provider's webhook docs. `data/` is last week's production traffic: every webhook we stored (`events.jsonl`) and the gateway's access log (`gateway.log`). `python tools/ledger_report.py data [account]` prints what the dashboard shows. `python check.py` replays the bakery's two webhooks exactly as production received them.

Fix it so the ledger is right for every merchant, not only the bakery. Next week's real traffic goes through your code. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

`_key/replay.py` sends a fresh week of webhooks (8 charges, new merchants among them) through the player's `receiver.handle` into an empty store, runs `reconcile.refund_totals`, and compares every charge with Paylane's settlement report. It passes only at 8/8.

The edge case: Paylane changed what `amount_refunded` means in API version 2025-09. It used to be the amount of this refund; now it is the charge's cumulative refunded total. Each merchant account is pinned to a version, and the version arrives only in the `Paylane-Version` request header. The receiver doesn't store it, so only the gateway log has it. The docs copy predates the change. Last week: acct_7Q and acct_K2 were on 2025-09, acct_M9 upgraded on Thursday 22 Oct at 13:40, and the other five stayed on 2024-06.

How a player can find it: the ticket charge's events show 500 then 800 for refunds of 5 and 3. Other merchants' partial refunds add up the old way. To see why, join `events.jsonl` with `gateway.log` by request id and compare the headers. acct_M9's charges switch behaviour on the same day its header changes.

## Key (`_key/`)

- `_key/cumulative/`: treats `amount_refunded` as cumulative for everyone (the ticket's obvious fix). It passes `check.py`; replay 5/8.
- `_key/per_account/`: hard-codes the three accounts that looked cumulative last week. It passes `check.py`; replay 5/8 (new merchants, the upgrade).
- `_key/reference/`: the receiver stores `Paylane-Version` with each event; the reconciler adds amounts on 2024-06 and keeps the max on 2025-09. Replay 8/8.
- `python _key/check_key.py` checks all of them (shipped 4/8). `_key/gen_data.py` regenerates `data/` and `_key/truth_week.json`.

## Gate result (2026-10-28): fails the gate, AI solves it

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, player README only): **3 of 3 solved**, all 8/8 on the hidden replay. Run time 85-107 s each. Every run joined `events.jsonl` to `gateway.log` by request id, found `Paylane-Version`, saw acct_M9's mid-week switch and handled it. All three also read old records' versions back from `gateway.log`. Two runs raise an error on an unknown version instead of guessing. None edited `data/` or wrote outside its folder.

Grading note: run 3 first scored 7/8. The miss was a replay bug: the out-of-order scenario stamped `created` in delivery order, so a late event looked newer than it was. Once the replay was fixed so `created` follows when Paylane made the event, all three runs scored 8/8 and the key check still holds (shipped 4/8, both tempting fixes 5/8, reference 8/8).

Lesson: hiding the edge case in data isn't enough when the data shouts. "Refunded more than charged" is an obvious anomaly, and the header that explains it sits on the same log line as the request. Opus reads 3 MB of logs in seconds and joins them by request id without being asked. Evidence that might beat it: a signal that only shows up in aggregate or over time (a slow drift, a correlation across weeks), evidence the player has to ask for or pay to see (a probe budget, a provider support ticket with a delay), or an anomaly that looks normal unless you know the business (an amount that is plausible but wrong).
