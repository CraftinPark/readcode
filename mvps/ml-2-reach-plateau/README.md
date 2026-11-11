# ml-2: reach_v3 after the refactor

*Tier 1: no AI, no web search for this codebase. Reading the code and running it is the whole job. Suggested time: 60 minutes.*

## The ticket

> **#58 reach_v3 much worse since the refactor**
> **Opened by:** Priya. **Assigned to:** you
>
> Since Alex's refactor landed (CHANGELOG, 20-24 Oct) reach_v3 is a lot worse. Same config, same seed. My curve from 14 Oct for the group meeting (`runs/before_refactor_s1.csv`, tensorboard export) climbs to ~60 and stays there. Alex's rerun on the new code (`runs/after_refactor_s1/`) tops out around 20 and then sags. He tried seeds 2 and 3 on the quick preset as well, same story.
>
> Alex says the refactor was meant to be behaviour-preserving apart from the logging and the env API, and the tests pass. Could be something in the code, could be something else, I honestly don't know. Can you take a look before we burn more cluster time on it? If it's a real regression I want to know exactly where it is.

## What's here

- `armrl/`: the training package (PPO for a simulated 2-link arm reaching a target). `docs/layout.md` is Alex's map of it.
- `train.py`: entry point. `python train.py --preset quick --seed 1` runs about 40 s on one CPU core. Every field of `armrl/config.py` is a command-line flag (`--gamma 0.99`, `--norm-obs false`, ...).
- `CHANGELOG.md`: the git log since the start of October.
- `runs/`: the two curves from the ticket. Your own runs land in `runs/<name>__s<seed>__<time>/progress.csv`.
- `scripts/plot_curves.py`: terminal plot of any of these CSVs. `scripts/summarize_runs.py runs/` gives one line per run.
- `tests/`: `python tests/test_buffer.py` (also `test_env.py`, `test_normalize.py`; pytest works too if you have it).

Needs Python 3.10+ with numpy and torch (CPU is fine).

You can edit and run anything. Keep a clean copy if you change code, so your line numbers match the shipped files when you answer.

## What to hand in

**Step 1.** Decide whether the code has a defect that explains the ticket. It may not: the honest answer can be "the code is fine". If it does, find the lines that cause it: the code that is wrong, which you would change or replace to fix it. Write `answers.json` (copy `answers.template.json`):

```json
{
  "verdict": "bug",
  "file": "armrl/something.py",
  "start_line": 10,
  "end_line": 14,
  "q1": "", "q2": "", "q3": ""
}
```

`verdict` is `"bug"` or `"no_bug"` (with `"no_bug"` the file and lines are ignored). Line numbers are 1-based, as in your editor, in the files as shipped. Your range must be 15 lines or fewer and lands if it is within 3 lines of the cause.

**Step 2.** Only after step 1 is written down, open `QUESTIONS.md` and answer its three multiple-choice questions in the same file (`"q1": "b"` etc.).

Grading is exact, no judge: location, then the three answers.
