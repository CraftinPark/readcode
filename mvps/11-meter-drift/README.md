# MVP 11: The missing Tuesday (slow drift, aiming at Tier 2)

*MVP 10 fell because its clue was loud: an impossible number on the same log line as the cause. Here the edge case is quiet. Nothing is wrong yet in the data; a trend across 8 weeks says it will be. AI-written MVP: an experiment.*

## The ticket

> **From:** Customer care. **Priority:** P2
>
> Customer on meter MTR-0115 (district D4) says their bill for week 8 (Mon 19 – Sun 25 Oct) has nothing for Tuesday evening from 17:00 to 23:00, which is when they cook and run the dryer. Network ops confirms a cell outage in D4 on Tuesday 20 Oct, 17:05–23:10 UTC. Meters keep up to 72 hours of packets and send them when the network is back.

The code is in `meterbill/`. The ingestion service calls `ingest.receive(conn, packet, received_at)` once per packet, in the order packets arrive. At the end of each 4-week billing period, plus one day for late packets, the billing run calls `billing.bill(conn, meter, start, end)` for every meter. Keep those two signatures; anything else (schema in `db.py` included) is yours to change.

`data/packets.jsonl.gz` is every packet from the last 8 weeks (31 Aug – 25 Oct 2026), in arrival order, with our server's `received_at`. `data/meters.csv` lists the meters. `python tools/report.py` prints weekly bills per meter. `python check.py` replays MTR-0115's week and checks that every 15-minute interval was stored.

Your fix goes live today, and the next six months of bills for all 20 meters will run through it. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

`_key/replay.py` streams weeks 1–32 through the player's `receive` in arrival order, runs the billing at each period end, and compares the bills for weeks 5–32 (7 periods × 20 meters = 140 bills) with what each customer really used, priced at the real time of day. It passes only if all 140 are within 1%. Six more cell outages happen in weeks 9–32, all over the evening peak.

The edge case: the 4 meters on firmware 2.1.4 have a clock that runs slow, losing 6–9.4 seconds a day, and they never resync. Their readings are stamped with that clock. By week 8 they are 6–9 minutes behind, which costs almost nothing yet. By week 32 they are 23–36 minutes behind, so the 17:00–21:00 peak price lands on the wrong quarter-hours, and those bills come out 2–6% low. Shipped code is worse: once a meter is more than 10 minutes behind, `MAX_SKEW` rejects every packet it sends, so its bills go to zero.

How a player can find it: `received_at - sent_ts` on live packets is a few seconds for 16 meters. For MTR-0103, 0108, 0114 and 0119 it climbs steadily week after week: 13–23 s in week 1, 6–9 minutes in week 8. All four report `fw: 2.1.4`. Nothing in the code, docs or ticket mentions clocks.

## Key (`_key/`)

- `_key/late_ok/`: accepts late packets (the ticket's fix). Passes `check.py`; replay 115/140. The drifting meters go wrong from about week 9.
- `_key/naive_offset/`: accepts late packets and shifts each packet by its own `received_at - sent_ts`. It handles clocks but moves buffered outage readings hours late. Passes `check.py`; replay 100/140.
- `_key/reference/`: accepts late packets and stores both clocks. Billing estimates each meter's clock offset per day as the smallest `received_at - sent_ts` (only live packets are that small), shifts readings to real time, and prorates across tariff hours. Replay 140/140, worst error 0.71%. The 1% tolerance exists because nobody can know how energy was spread inside a 15-minute interval that straddles 17:00.
- `python _key/check_key.py` checks all of them (shipped 92/140). `_key/sim.py` is the world (meters, clocks, outages, true consumption); `_key/gen_data.py` regenerates `data/`.

## Gate result (2026-10-28): passes the gate, 2 of 3 runs failed

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, player README only). Run time 99-192 s each.

| Run | Replay | What it did |
|---|---|---|
| 1 | **140/140, solved** | Accepted late packets, estimated each meter's clock offset as the smallest skew over its last 24 live packets, and billed at meter time plus that offset with proration across tariff hours. Essentially the reference. Its own simulation of a meter 30 minutes slow matched the true-time bill exactly. |
| 2 | 115/140, failed | Fixed the outage rejections. **Found the drift**, named all four fw 2.1.4 meters, and listed "peak/off-peak boundaries will be off by tens of minutes over six months" as a follow-up instead of fixing it. |
| 3 | 115/140, failed | Same as run 2: found the drift, added a `packets.lag` column "so ops can track it", and handed "correct timestamps in billing" back as a decision. |

All three fixed the ticket, kept replay protection through the readings' primary key, and wrote their scratch scripts inside their own folder. None edited `data/`.

What this tells us: the drift was found 3 times out of 3. It wasn't hidden from AI. The two failures are judgment failures. The model saw a slow, not-yet-harmful problem outside the ticket's scope and parked it as a follow-up, even though the README says the next six months of bills run through the fix. That is a real failure mode, and a human on-call engineer might do the same. But it means this problem tests "act on what you found" more than "find it". A wording change ("I'm closing the ticket after this, there is no follow-up") would probably flip runs 2 and 3. The pass is real but thin: with 1 of 3 solved, a rerun could come out 2 of 3 solved.
