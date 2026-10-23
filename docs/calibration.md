# Calibrating an exercise with real engineers

Before an exercise is used to judge anyone, we need to know what scores people
at each level actually get. This kit runs that check for `readcode-003` (it
works the same for any example).

## What exists already (no people needed)

`backend/tests/fixtures/calibration/` has written answers at three levels for
the full review and for tasks T1, T5 and T7. `backend/tests/test_calibration.py`
checks the grader ranks them. With the current FakeJudge (word overlap):

| Candidate | Full review | T1 incident | T5 PR review | T7 trace |
|---|---|---|---|---|
| strong | 98 | 100 | 100 | 100 |
| mid | 12.6 (should be 40-70: known FakeJudge gap) | 54 | 0 | 100 |
| weak | 3.6 | 0 | 0 | 0 |

These answers were written by us, so they only test the grader, not the
exercise. The exercise is calibrated only by people who have never seen it.

## Who to recruit

Five to eight engineers who have not seen the code, spread across levels:

| Level | How many | Rough profile |
|---|---|---|
| New grad / intern | 2 | under 1 year professional |
| Mid | 2-3 | 2-5 years, has shipped a backend service |
| Senior | 2-3 | 6+ years, has been on call for a payments or similar system |

Record level by what they do, not their title.

## Running a session (60-75 minutes)

1. Start the app (`cd frontend && npm run dev`) and open `#/exercises`. Give them a fresh browser profile so autosave is empty.
2. Tasks first, in this order, timed but not cut off: T1, T2, T3, T4 (incidents), T5, T6 (PR reviews), T7 (trace).
3. Then the full review of `readcode-003`, 50 minutes.
4. They may read the code and run `pytest` in a copy of `code/` (the smoke tests). No AI tools.
5. Ask them to think aloud. Write down when they first form a hypothesis and when they first touch the right file; this is the "narrate your hypothesis" signal Stripe and Meta score.
6. After each submission, copy the JSON from the submitted page into `calibration/readcode-003/<person>/<task>.json`.
7. Five minutes at the end: "Which part felt unfair or unclear? Which bug felt like a trick?" Note answers verbatim.

## Scoring and what to look for

```
cd backend
python -m grader ../examples/readcode-003 ../calibration/readcode-003/<person>/review.json
python -m grader ../examples/readcode-003 ../calibration/readcode-003/<person>/T1.json
```

Enter the results in `calibration/results-template.csv`, one row per person and task.

An exercise is ready for hiring use when:

- Median score rises with level (new grad < mid < senior) on the full review and on the incidents taken together.
- Every bug is found by at least one senior and missed by at least one new grad. A bug nobody finds is too hard or unfair; a bug everybody finds carries no signal.
- No red herring is flagged by most seniors. If it is, the code is misleading, not the candidate.
- Grader score and a human reviewer's score (read the submission blind, 1-4 scale) agree in rank order for at least 80% of pairs.
- Nobody describes a bug as "a trick" for reasons other than difficulty (for example, an ambiguous spec).

Record the outcome in the example's `manifest.json` under `review.notes` and
attach the CSV. Until then the exercise stays `review.status: pending`.
