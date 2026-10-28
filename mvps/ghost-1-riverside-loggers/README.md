# Ghost 1: Riverside's new loggers (ghost code, aiming at Tier 2)

*The scenario: a key module was written years ago by someone who left. Its names are cryptic or wrong, it has magic numbers and no docs, and production depends on it. Plain renaming won't beat Opus, so the meaning of one magic number is not in the code at all: only production data shows what it is for. AI-written MVP: an experiment.*

## The ticket

> **From:** Billing ops. **Priority:** P1, Riverside's first bills go out with the October run on Sun 1 Nov.
>
> The 8 Riverside connections (zone E) went live on Mon 5 Oct with the new BX loggers from our new vendor. Ingest rejects every BX packet (`ValueError: pkt`), so Riverside has no readings at all. Please make ingest accept them and get Riverside's October bills right from the packets the gateway has kept since 5 Oct.
>
> From the vendor's email: a BX packet body has `dev` (the device id, as in `meters.csv`), `ts` (reading time, UTC), `vol` (volume register) and `bat` (battery volts). One reading per hour, like the old loggers.

`wfl/` is ingest and billing. Piet wrote it in 2019 and left in 2021; there are no docs, no tests and nobody to ask. It has billed every customer since. The gateway calls `qn.receive(conn, packet)` once per packet, in arrival order. One day after each month ends, the billing run calls `bx.bill(conn, meter, start, end)` for every meter and sends `litres` and `eur` to invoicing. Keep those two signatures and the keys they return; anything else (the schema in `db.py` included) is yours to change.

`data/` holds the two zones we look after:

- `packets.jsonl.gz`: every packet the gateway received from Mon 1 Jun to Tue 27 Oct 2026, in arrival order. The old LX-2 loggers send a `hex` payload; the BX loggers send a JSON `body`.
- `meters.csv`: the meters, their zone and logger.
- `bulk.csv`: the water board's weekly readings of each zone's inlet main, in m³.

`python tools/report.py [meter ...]` prints the monthly bills. `python check.py` ingests everything in `data/` and checks that every meter has water billed on every day since 5 Oct.

Your change goes live for the October run and stays: the next six months of bills for every meter will run through it. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

`_key/replay.py` ingests every packet from 1 Jun 2026 to 2 May 2027 through the player's `qn.receive` into a fresh database (`data/` first, then six months of new traffic), runs the billing one day after each month ends, and compares the bills for October to April (7 months × 24 meters = 168 bills) with the litres each customer really used. It passes only if all 168 are within 1%.

What the module really does, which nothing in the code says:

- **`lf = 1.062` in `bx.py` is the LX-2 logger's calibration**: one LX-2 pulse is 1.062 litres. `rd.l` holds pulses, not litres, and billing turns them into litres. The BX register counts whole litres. Sending BX volumes through the same billing bills Riverside 6.2% too much. Dropping `lf` for everyone (it looks like a stray fudge factor) bills every old meter 5.8% too little.
- **`J = 65280` in `qn.py` is a 16-bit wrap guard**: LX-2 counters wrap at 65,536, so a drop from near the top is a wrap and anything else is a battery change (counter restarts at 0). The BX register is 32-bit and never wraps. Run through the same code, a BX battery change after the register has passed 65,280 litres is read as a wrap and produces a large negative bill. In `data/` this never happens: the one BX battery change (R-0303, 19 Oct) comes at about 6,000 litres. In the next six months it happens four times (launderette in January, cafe in February, two households in April).
- `(flag >> 6) & 1` skips the technician's test packets (counter 0xFFFF). It looks dead but three real ones arrive (two in `data/`).

How a player can find it:

- `lf`: the water board's inlet readings. With `lf` applied to BX, zone E bills about 104.4% of the water that came into the zone in each week since 5 Oct, which can't be. In every earlier week, and in zone W all along, bills come to 99.1-99.6% of the inlet (the rest is leakage). Without `lf` on BX, zone E stays at 99.2-99.6%.
- `J`: the launderette's BX register passes 65,535 in `data/` (about 88,000 litres by 27 Oct) and keeps counting, so BX is not 16-bit. LX-2 counters in `data/` never go above 65,535.

## Key (`_key/`)

- `_key/adapter/`: turns BX packets into the LX-2 shape and sends them through the same code (the ticket's obvious fix). Passes `check.py`; replay 112/168 (every BX bill 6.2% high, plus the battery changes).
- `_key/adapter_nolf/`: the same, but billing skips `lf` for BX meters. Passes `check.py`; replay 164/168 (the four BX battery changes).
- `_key/no_lf/`: handles BX correctly but drops `lf` for everyone. Replay 56/168.
- `_key/reference/`: LX-2 path untouched. BX readings go to their own table in litres, and a drop in a BX register always means a restart. Billing applies `lf` to LX-2 pulses only. Replay 168/168.
- `python _key/check_key.py` checks all of them (shipped 0/168: it rejects BX and the replay crashes). `_key/sim.py` is the world; `_key/gen_data.py` regenerates `data/`.

## Gate result (2026-10-28): fails the gate, AI solves it

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, player README only, title without "Tier 2"). **3 of 3 solved.** Run time 153-159 s each.

| Run | Replay | What it did |
|---|---|---|
| 1 | **168/168, solved** | New BX path with its own last-value table. Reconciled every week against `bulk.csv`: LX-2 raw counts are 1/1.069 of the inlet, so `lf` corrects LX-2 under-reading, and zone E only balances with BX at 1.0. Billing factor per logger (`{"LX-2": 1.062, "BX": 1.0}`). Noted R-0308's register passing 65,536, so no 16-bit wrap. |
| 2 | **168/168, solved** | Same finding from `bulk.csv` (zone E inlet minus LX-2 × 1.062 is 1.005-1.010 × raw BX). Tagged `rd` rows with a source column and applied `lf` per row, so a meter that changes logger mid-month still bills right. |
| 3 | **168/168, solved** | Same: raw LX-2 is about 0.935 of the inlet, × 1.062 about 0.993, raw BX already matches. Logger column on `mt`, `lf` only for LX-2. |

All three: wrote their own BX delta code (a drop means a restart from 0) instead of reusing Piet's, so the `J = 65280` trap never came into play. All kept the LX-2 path byte-for-byte and diffed `tools/report.py` before and after. All flagged `round_up` truncating and the two heavy Riverside users, and left both alone. None edited `data/`. Run 2 wrote three scratch files in the parent folder and deleted them.

Lesson: the magic number's meaning was not in the code, but it was one reconciliation away, and Opus reconciles unprompted. Listing `bulk.csv` in the README as "the water board's inlet readings" was enough: every run divided billed water by inlet water, per zone and per week, and read `lf` straight off the ratio. Ghost code (cryptic names, magic numbers, no docs) adds no difficulty for Opus. It treats unknown code with caution, keeps old behaviour exactly where it is not asked to change it, writes fresh code for the new case rather than reusing the old one, and checks results against any independent total the data offers. So a trap built on "reused old code it didn't understand" (`J`) doesn't fire, and a trap whose evidence is a conservation check (`lf`) gets found. What might still work: the meaning lives somewhere the README doesn't point (no independent total, only a slow pattern, as in MVP 11), or the fix requires *changing* old behaviour for existing customers. Opus flagged and left alone every old oddity it found here (`round_up`), the same "defer" judgment that made MVP 11 pass.
