# research/api: field research for the API / payments track

Start with **[field-guide.md](field-guide.md)** (ranked failure classes, evidence, best first problems, methods, limitations).

| Path | What |
|---|---|
| `jobs/` | 2,678 backend postings from 158 companies (Greenhouse/Ashby/Lever APIs): `job-roles.csv`, `job-theme-counts.json`, `summary.md`, scripts |
| `interviews.md` | Debugging / bug-squash / code-review / design rounds at 12 companies, with links and confidence |
| `literature.md`, `literature/` | Yuan OSDI'14, Gunawi SoCC'14 and '16, TaxDC ASPLOS'16, SRE book ch. 21-22, Cook, Brandur/Stripe, Jepsen, danluu post-mortems (counted by script) |
| `bugs/bugs.jsonl` | 59 bug cards in the `docs/prompts/mine-bugs.md` format (+ `id`, `field_guide_class`, `url`, `commit_date`, `original_pr`) from saleor (BSD-3), killbill (Apache-2.0), hyperswitch (Apache-2.0), django-oscar (BSD-3) |
| `bugs/report.md` | Table, clusters, rejected candidates, top 3 |
| `bugs/*.py` | `candidates.py` (filter git log), `view.py` (read diffs), `cards_spec.py` (hand analysis), `build_cards.py` (exact code from git), `report.py` |

Re-running the bug scripts needs local clones: `git clone --single-branch --shallow-since=2021-10-01 https://github.com/<owner>/<repo>.git`, then `python bugs/build_cards.py <clones-dir> bugs/bugs.jsonl`.
