import json, sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from cards_spec import REJECTED
bugs = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
out = open(sys.argv[2], "w", encoding="utf-8")
w = lambda s="": out.write(s + "\n")
w("# Mined real bugs: report")
w()
w("Method: `docs/prompts/mine-bugs.md`, run on local `git clone --shallow-since=2021-10-01` copies (no GitHub API calls), commits from 2022-01-01 to 2026-10-24. "
  "`candidates.py` keeps commits whose subject looks like a fix and that change at most 30 non-test lines in at most 3 non-test files "
  "(migrations, schema dumps, docs and lock files excluded from the count). I then read the diff of each shortlisted candidate (`view.py`) and wrote the analysis in `cards_spec.py`; "
  "`build_cards.py` copies `buggy`/`fixed`, line ranges (pre-fix side), commits and the added regression test from git, so no code in `bugs.jsonl` is typed by hand.")
w()
reps = collections.Counter(b["repo"] for b in bugs)
w("| Repo | License (checked in LICENSE at HEAD) | Fix-like small commits found | Diffs read | Accepted |")
w("|---|---|---:|---:|---:|")
w(f"| saleor/saleor | BSD-3-Clause | 474 | ~40 | {reps['saleor/saleor']} |")
w(f"| killbill/killbill | Apache-2.0 | 141 | ~12 | {reps['killbill/killbill']} |")
w(f"| juspay/hyperswitch | Apache-2.0 | 902 | ~16 | {reps['juspay/hyperswitch']} |")
w(f"| django-oscar/django-oscar | BSD-3-Clause | 69 | ~9 | {reps['django-oscar/django-oscar']} |")
w(f"| **total** | | 1,586 | ~77 | **{len(bugs)}** |")
w()
w("medusajs/medusa was considered and skipped: its LICENSE is MIT except for Enterprise Edition material under a separate license, which would need path-by-path checking.")
w()
w("## Accepted bugs")
w()
w("| id | title | pattern | skills | elus. | distance | link |")
w("|---|---|---|---|---:|---|---|")
for b in bugs:
    w(f"| {b['id']} | {b['title']} | {b['pattern']} | {', '.join(b['skills']) or '(none fits)'} | {b['elusiveness']} | {b['distance']} | [{b['repo'].split('/')[1]}{' #'+str(b['pr']) if b['pr'] else ' '+b['merge_commit'][:9]}]({b['url']}) |")
w()
w(f"Distance: {dict(collections.Counter(b['distance'] for b in bugs))}. Regression test added by the fix: {sum(1 for b in bugs if b['regression_test'])} of {len(bugs)} "
  "(Hyperswitch fixes almost never add one). Skills used: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(s for b in bugs for s in b['skills']).most_common())
  + f"; {sum(1 for b in bugs if not b['skills'])} bugs fit no taxonomy skill.")
w()
w("## Clusters (bugs that share one root-cause sentence)")
w()
cl = collections.defaultdict(list)
for b in bugs:
    cl[b["field_guide_class"]].append(b)
SENT = {
 "money-calculation-order": "An amount is computed in the wrong order or from the wrong inputs (precedence, rounding step, clamping, unit/currency, float).",
 "double-apply": "The same adjustment (discount, surcharge, record, side effect) is applied by two layers or two handlers.",
 "state-transition-guard": "An action or event is allowed from a state that should not permit it, or a state is mis-grouped with terminal states.",
 "derived-state-not-recomputed": "A stored status/counter depends on inputs that change, but one write path does not recompute it.",
 "cache-stampede-key": "Reader and writer (or invalidator) of a cache/queue disagree on the key, or fill it too late.",
 "time-calendar": "A calendar computation uses the wrong time zone or the wrong anchor when stepping periods.",
 "concurrency-check-then-act": "A decision is made from data read outside the lock/transaction that the action relies on.",
 "aggregation-join-fanout": "A join multiplies rows, and a COUNT/SUM/DISTINCT on top gives the wrong number.",
 "pagination-cursor": "The cursor's comparison does not match the sort order exactly (direction, truncation, two implementations).",
 "stale-read-wrong-variable": "The code reads a stale or near-identically named value instead of the fresh one.",
 "missing-scope-filter": "A query that must be scoped (tenant, owner, not-deleted) is missing the filter on one path.",
 "write-scope-clobber": "A write meant for one record replaces or misses related records.",
 "lock-ordering-deadlock": "Two code paths take the same locks in different orders.",
 "retry-amplification": "Retries happen with no delay or no memory of recent failure.",
 "identity-vs-equality": "Objects are compared by identity or hash instead of value.",
 "later-event-overwrites": "A later, less authoritative event overwrites a value that should be kept.",
}
for k, v in sorted(cl.items(), key=lambda kv: -len(kv[1])):
    repos = sorted({b["repo"].split("/")[1] for b in v})
    w(f"- **{k}** ({len(v)}: {', '.join(b['id'] for b in v)}; repos: {', '.join(repos)}). {SENT.get(k, v[0]['root_cause'])}"
      + (" *Crosses repos: strongest evidence it is a general pattern.*" if len(repos) > 1 else ""))
w()
w("Known patterns from outside these repos: check-then-act and lock ordering are textbook concurrency bugs and match the Jepsen lost-update findings; "
  "cache key mismatch matches the GitHub/OpenAI cache incidents in danluu/post-mortems; the time-zone cluster matches ReadCode's own 008 (DST) problem; "
  "S27/S33 match Brandur's 'foreign state mutation' failure modes.")
w()
w("## Rejected candidates (read, then dropped)")
w()
for repo, sha, title, why in REJECTED:
    w(f"- {repo} `{sha}` {title}: {why}.")
w("- Plus ~1,500 fix-like commits not opened: dropped by subject (dependency, docs, CI, typo, connector-specific field mapping) or size; not individually recorded.")
w()
w("## The three I would turn into exercises first")
w()
w("1. **S19 search cursor tie-break reversed** (pagination, elus. 4). One swapped `gt`/`lt` inside half of an OR; the symptom (an empty or repeated page) is confirmed on the PR page; "
  "rebuilds in ~40 lines with SQLite and a deterministic test (equal ranks across a page boundary). Teaches keyset pagination, which no ReadCode problem covers yet.")
w("2. **S27 lock released before the work** (race + idempotency, elus. 5). The buggy code *has* a `SELECT ... FOR UPDATE` and a comment claiming exclusivity, so it looks safe; "
  "it is the payments-shaped version of the most common concurrency mistake. Needs a two-request interleaving in the playground (the 003 fault-injection pattern already exists).")
w("3. **H1 join not scoped by tenant** (tenant isolation, elus. 4). Cross-merchant data from a join whose key is only unique per merchant; high cost, a one-line fix, "
  "and a realistic 'two accounts' reproduction. Complements 005 (token read) with a different mechanism.")
w()
w("Runners-up: S2 (SUM DISTINCT on equal values, very distillable), K2/K3 (time zone at end of day; overlaps 008), S35 (ignored return value with several gift cards; good rung-1 warm-up).")
w()
w("## Caveats")
w()
w("- Symptoms are mostly paraphrased from PR titles and commit messages; only S19, S27 and H1 were checked against their PR pages. Linked issue threads were not read (no API budget spent).")
w("- No bug was searched on the web for fame; none has a CVE that I know of.")
w("- `ranges` are pre-fix line ranges of the changed hunks; a pure insertion is recorded as the single line before which it was inserted.")
w("- Hyperswitch is Rust with heavy generics; its distilled versions would be re-written in Python, as the prompt allows.")
w("- Kill Bill commits are not squash merges, so `merge_commit` is the fix commit itself.")
out.close()
print("ok")
