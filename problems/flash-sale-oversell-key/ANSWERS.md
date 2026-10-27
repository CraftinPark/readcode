# Answer key: TIX-4182, the Hollow Coast presale oversold

Keep this off the problem branch. The candidate sees only `problems/flash-sale-oversell/`.

## Answers

| Q | Answer | Accept |
|---|---|---|
| Q1 Where | `tickets/inventory.py` 53-66: the `with _hold_lock:` block, from reading `seats_taken` to the `INSERT` | Any range in `inventory.py` overlapping 50-69 |
| Q2 Why | **C** | |
| Q3 Fix | **D** | |

Suggested scoring (as in our other tasks): where 40, why 40, fix 20.

## The mechanism

`_hold_lock` is a `threading.Lock`, so it only exists inside one Python process. The unit test that "proves" the lock works uses two threads in one process, so it passes. In production `deploy/worker.toml` runs 4 processes on each of 2 hosts. That's eight independent locks, so eight workers can be between "read the seat count" and "insert the hold" at the same time. The window is wide because `pricing.quote()`, a 20-45 ms network call, sits between the check and the insert, placed there to avoid pricing sold-out purchases. In the log, five holds read `seats_left=3` within 40 ms, four of them pass (6 seats for 3), and the next read is `-3`.

## Why the wrong options are wrong

- **Q2 A (cache):** the worker only uses the cache to reject early. A stale "seats left" value can only send a purchase on to `inventory.hold`, which checks the database. It explains the "3 left" the fans saw, which is a red herring.
- **Q2 B (queue):** `jobqueue.claim` is one `UPDATE ... RETURNING`, and on-call found no duplicate `request_id`.
- **Q2 D (payment retry):** retries happen inside `payments._with_retries` with the same idempotency key, and never touch `orders`.
- **Q3 A (`multiprocessing.Lock`):** it's shared only by processes on one host, and production has two hosts. It also only works for processes started from the same parent.
- **Q3 B (`processes = 1`):** two hosts still race, and it undoes the capacity added for the sale.
- **Q3 C (cache TTL 0):** the cache isn't the cause.

## Proof

`fixed/inventory.py` is the fix (option D). `test_gate.py` runs the problem's own `simulate.py`. With 1 worker it never oversells. With 8 workers the shipped code oversells in at least one of three seeded runs. With the fix it never oversells. Run it with:

```
python -m pytest problems/flash-sale-oversell-key/test_gate.py
```

On 2026-10-25 the result was 5 passed (about 30 s). Locally the oversell is small, typically 1-3 seats per run, because the race only matters around the last few seats. The ticket's 14 seats come from a 1,200-seat sale with 8 processes and real network latency.

## Where it comes from

Field guide (API track), class 2, "Concurrency: check-then-act, lost update, lock ordering": score 12, tied for first, and not covered by any earlier problem. It's a check-then-act race, with a lock that doesn't protect what it claims to. The closest mined instance is Saleor S27 ([#12657](https://github.com/saleor/saleor/pull/12657)), a lock taken in the wrong place that doesn't cover the work. The in-process lock under a multi-process deploy is a reconstruction of that pattern, not a specific public incident. Stripe's bug-bash reports describe an "unguarded read-modify-write" race (see `research/api/interviews.md`).

## What makes it "wild"

- **The "lock" looks correct, and its test passes.** The cause sits in a config file, not in the code diff.
- **Nothing was deployed except configuration**, which matches the field guide's class 7 evidence that config changes cause many incidents.
- **Red herrings with real explanations:** the stale "3 left" page, retries and a job queue.
- **It's runnable:** the candidate can reproduce it with 1 and 4 workers, open the database, and test a fix.
