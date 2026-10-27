# MVP 08: Author kit (Kaggle-style pivot)

*Section 4 idea: make authoring part of the competition. Jay's two blockers were "authors need it to be quick" and "hide which company it came from". This kit is the smallest version of both, plus the quality gate that would become the product. AI-written MVP: an experiment.*

## The contract for a submitted problem

A folder with `README.md` (what the player sees) and `_key/check_key.py`, which exits 0 only if **the shipped code fails and the author's reference fix passes** (proof by test). Ideally the key also shows a tempting wrong fix failing. MVPs 03-07 follow this contract.

```
python validate_submission.py ../03-story-hoverboard ../04-body-balance ../05-live-replay ../06-gearmotor-keyhole ../07-write-tests-mutation
python anonymise.py example out --names example/names.txt
```

## What happened when we ran it

- **Validator:** accepted 03-06 (each with a tempting wrong fix checked) and **rejected 07 and 01** for missing a key check. 07 got one (starter tests 0/8, reference 8/8) and now passes; 01 is a rebuild of the flash-sale problem, whose key lives in `problems/flash-sale-oversell-key/`, so it stays out of this contract for now.
- **Anonymiser:** on `example/incident.md` it replaced the company, product, email, hostname, IP and internal dashboard URL, then flagged leftovers for a human or LLM check (`PayoutBatcher`, an internal class name). **It first leaked the names file itself into the output**; fixed, and now skips it.
- Authoring cost, from building these MVPs: about 5-10 minutes of model time each, most of it on the key (making the tempting fix fail for the right reason). A human author will need much longer; Jay's "if it takes 5 hours nobody will do it" is the number to measure in the Wednesday sprint.

## Not done

Rewards that follow solver data (attempts, solve rate, how well a problem separates levels), a submission page, the AI gate (3 fresh Claude runs) as part of validation, licence and liability terms.
