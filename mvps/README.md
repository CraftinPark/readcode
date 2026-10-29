# MVPs: one problem per idea (2026-10-27)

One small runnable problem per idea in the findings doc ("ReadCode: findings so far"). Python 3.10+, no packages. All AI-written: experiments to see which ideas hold up, not shipped content (John's CLAUDE.md rule: AI-made bad code needs his OK). Each folder's README says what the player sees, what we learned building it, and what's not done. `_key/` is never shown to the player; `_key/check_key.py` proves the problem discriminates.

| # | Idea (doc section) | Problem | Key check result |
|---|---|---|---|
| 01 | Big repo, no hint (5c) | Flash-sale oversell inside the marketplace backend, starting hint removed | Replay still oversells; only 1,316 lines, needs real surrounding code |
| 02 | No copy-paste (5c) | Static viewer: copy/paste blocked, trail of files opened and questions typed | Checked in a browser |
| 03 | Story world (5a) | Precinct 9 hoverboards flip on one axis (version compared as a string) | Shipped 4/7 boards flip, special-case hack 3/7, fix 0/7 |
| 04 | Systems balancing (5b) | Balance a body run as a backend: 6 knobs, infection + injury | Shipped 49.8, more capacity 76.3, reference 84.3 (target 80) |
| 05 | Live replay after "resolved" (Tier 2) | Double charge on re-tap; replay with pod restarts and a slow provider | Shipped 1/5, in-memory fix 2/5, durable fix 5/5 |
| 06 | Hardware keyhole (Tier 2) | Conveyor runs away after 25.6 s; 3 probes; 16-bit encoder wrap | Shipped e-stops, drift hack 17 deg off, fix 0.7 deg |
| 07 | Write the tests (Tier 1, RepoGym's strength) | Promo-code tests graded by 8 hidden mutants | Starter 0/8, reference 8/8 |
| 08 | Author kit (Kaggle pivot) | Submission validator + anonymiser | Accepts 03-07; caught 07's missing key and its own names-file leak |
| 09 | Live replay, v2 (Tier 2) | Double charge; per-order key replays declines | Order key 4/7, per-attempt key 7/7. Gate: Opus 3/3 solved
| 10 | Evidence hunt (Tier 2) | Refund ledger; meaning of a field depends on a header only the gateway log keeps | Shipped 4/8, tempting fixes 5/8, reference 8/8. Gate: Opus 3/3 solved
| 11 | Slow drift (Tier 2) | Meter clocks lose seconds a day; only an 8-week trend shows it | late-packet fix 115/140, per-packet skew 100/140, reference 140/140. Gate: **does not pass**: Opus solved 5 of 9 over three batches (1/3, 3/3, 1/3); all 9 found the drift, the 4 failures deferred it
| 12 | Wrong diagnosis (Tier 2) | Staff engineer blames late reseller webhooks; real cause is two statuses only production has; 5 prod queries | 24 h wait 4909/5000, allow-list 4940/5000, reference 5000/5000. Gate: Opus 2/3 solved (third missed 3 by a business-rule call)
| 13 | Latent harm, take two | Duplicate login SMS; the real threat is a shared 10k/day SMS quota the growing Tuesday campaign is about to exhaust | dedupe-only loses 7,086 codes, reference 0. Gate: Opus 3/3 solved
| 14 | Black-box tuning (Tier 2?) | Sourceless worker pool, 3 interacting knobs, 12 noisy benchmark runs; the answer exists only as measurements | shipped and 3 tempting configs fail, reference passes. Gate: **passes, Opus 0/3** (closest p99 279 vs 250). A planned 12-run strategy run against the noisy bench solves it 50/80; no human solve yet
| 15 | Only after a while | Wrong charges that appear only 10+ min after the pricing service starts (cache expiry switches pence to pounds); the service is a compiled module | 3 tempting fixes fail, reference passes. Gate: Opus 3/3 solved (it loaded the module, read its bytecode and fast-forwarded the clock) |
| 16 | Only after a while, remote | MVP 15 with the pricing service as a separate server process: no code, no restart, no fake clock; the bug shows only after 10+ min of uptime | Gate: Opus 3/3 solved (each ran a background poller for about 10 minutes and caught the switch) |
| hw-1 | Hardware keyhole: camera (easy) | LED station after a camera swap; register behaviour must be measured with a few captures | Gate: Opus 2/3 solved |
| hw-2 | Hardware keyhole: muon telescope (medium) | Coincidence counter in an unheated hut; timing, window and dead time must be measured before a year-long campaign | Gate: **passes, Opus 1/3** (with a 3% pass mark; a good measurement plan gets about ±1.5%); no human solve yet |
| hw-3 | Hardware keyhole: quantum chip (hard) | Behaviour after a cooldown that the calibration format can't describe; learn it inside a shot budget | Gate: Opus 3/3 solved (found the Stark crosstalk by validating on random circuits) |

`python 08-author-kit/validate_submission.py 03-story-hoverboard 04-body-balance 05-live-replay 06-gearmotor-keyhole 07-write-tests-mutation` reruns every key check.

Not done for any of them: gating against Claude (3 fresh runs), a human solve.
