# MVP 07: Write the tests (graded by mutation testing)

*Tier 1 idea, copied from RepoGym's strongest feature and Jay's point that deciding which tests matter is a human job. AI-written MVP: an experiment, not shipped content.*

## The task (what the player sees)

> `promo.py` decides the discount for a promo code at checkout. It is correct today. Next sprint three people will touch it. Write the tests in `test_promo.py` that would catch the mistakes they are likely to make. Plain `assert`s in `test_*` functions; no packages needed.
>
> `python grade.py` checks your tests pass on the real code, then runs them against hidden variants of `promo.py`, each with one realistic slip. Score = slips caught.

## How it is graded

`_key/mutants.py` holds 8 one-line slips: minimum-subtotal boundary, the expiry day itself, max uses off by one, first-order rule, rounding, the cap at the subtotal, case sensitivity, trimming spaces. A test file that fails on correct code scores 0 (it would catch everything and mean nothing).

- Starter test: 0/8. `_key/strong_tests.py`: 8/8 (`python grade.py _key/strong_tests.py`).
- No AI grader, no free text: exact and automatic.

## Notes

- In the product the mutants live on the server; here `_key/` sits next to the problem, so don't read it.
- This is Tier 1 only: an AI asked to "write thorough tests for promo.py" would likely catch most slips. Worth measuring (gate it) before assuming anything.
- Not done: weight the slips by how often they happen in real code, a time limit, a second module with I/O (Jay's example: no tests for file I/O and downloads).
