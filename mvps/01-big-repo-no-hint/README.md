# MVP 01: Big repo, no hint (Tier 1.5, first half)

*Idea 5c: choosing where to look is exactly what AI does for you today, so remove the "start with tickets/worker.py" hint and bury the problem in a bigger codebase. Built from Danny's flash-sale oversell problem for John (branch `danny-problem-for-john`), not a new bug.*

```
python build.py                         # writes out/ (git-ignored)
python build.py --extra PATH/TO/REPO    # add a real permissive codebase as surrounding code
cd out && python simulate.py
```

`out/` holds the ticket, on-call's findings and the three questions (no code tour, no hint), the ticket service, and the marketplace backend from `examples/_sources/market` as surrounding code. The replay still oversells (e.g. capacity 150, confirmed 151).

## What we learned building it

- Our own code only reaches **1,316 lines**, far from the ~10,000 target. The surrounding code has to come from a real codebase (`--extra`, e.g. a Saleor checkout; BSD-3, ship its license) or stubs will be ruled out at a glance.
- Even without the hint, the ticket's own log lines name `tickets.inventory`, and the folder is called `tickets/`. Real incidents carry such clues, so this is fair, but it means the big repo adds less difficulty than the line count suggests. A harder variant would rename modules to the company's internal names.
- Pair it with MVP 02 (the no-copy-paste viewer), which logs which files the player opened and in what order: that log is the measurement of "where did you look".

Next: give this to John after his current attempt, and compare his time and knew-vs-guessed answers with and without the hint.
