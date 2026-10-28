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
| 11 | Slow drift (Tier 2) | Meter clocks lose seconds a day; only an 8-week trend shows it | late-packet fix 115/140, per-packet skew 100/140, reference 140/140. Gate: **passes**, Opus 1/3 solved (2 found the drift but deferred it)

`python 08-author-kit/validate_submission.py 03-story-hoverboard 04-body-balance 05-live-replay 06-gearmotor-keyhole 07-write-tests-mutation` reruns every key check.

Not done for any of them: gating against Claude (3 fresh runs), a human solve.
