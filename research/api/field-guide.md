# Field guide: real failures in API and payments backends

*ReadCode field research, API / payments-infrastructure track. 2026-10-24.*

**Short answer.** Across 2,678 backend job postings, 12 companies' interview reports, 10 failure studies and playbooks, and 59 bugs mined from four open-source commerce and payments repos, the failures that matter most are: **mishandled partial failures around external calls**, **concurrency (check-then-act, lost updates)**, **money arithmetic and double counting**, **retry and overload amplification**, and **lifecycle (state-machine) errors**. Pagination is the most "puzzle-like" class and has the weakest real-world signal. The best first new problems are listed in [section 3](#3-best-first-problems).

Inputs (all in this folder):
- [`jobs/summary.md`](jobs/summary.md): postings, counts, scripts.
- [`interviews.md`](interviews.md): debugging, code-review and design rounds.
- [`literature.md`](literature.md): studies and playbooks with numbers.
- [`bugs/report.md`](bugs/report.md) and [`bugs/bugs.jsonl`](bugs/bugs.jsonl): 59 bug cards.

## 1. Ranking

Each class gets 0-3 points per evidence source plus a 1-3 cost score. I fixed the rule before scoring, so the ranking is not just my taste:

- **Postings**: share of the 2,678 backend postings (or of the 139 payments-titled ones, whichever is higher) that use the class's keywords. ≥20% = 3, 8-20% = 2, 2-8% = 1, <2% = 0.
- **Interviews**: number of companies whose reports mention it. ≥3 = 3, 2 = 2, 1 = 1.
- **Literature**: 3 if two or more sources make it a central finding with numbers; 2 if one does, or three or more describe it; 1 if one or two describe it.
- **Mined**: bug cards in the class. ≥10 = 3, 5-9 = 2, 2-4 = 1, 0-1 = 0.
- **Cost**: 3 = money lost, data exposed or an outage; 2 = wrong numbers that can be repaired; 1 = an annoyance.

| # | Failure class | Post. | Int. | Lit. | Mined | Cost | **Score** | Covered by an existing ReadCode problem? |
|---|---|---|---|---|---|---|---|---|
| 1 | Partial failure around external calls (error handling, compensation) | 3 (fault tolerance 30%) | 3 | 3 | 0 (1 card) | 3 | **12** | partly: 003 B1 |
| 2 | Concurrency: check-then-act, lost update, lock ordering | 2 (16%) | 2 | 3 | 2 (6) | 3 | **12** | no |
| 3 | Money arithmetic and double counting | 3 (ledger 50%, correctness 45% in payments) | 1 | 1 | 3 (13) | 3 | **11** | 007 (rounding) |
| 4 | Retries, timeouts and overload amplification | 1 (3.4%) | 3 | 3 | 1 (2) | 3 | **11** | partly: 003 B3 |
| 5 | Lifecycle / state-machine errors | 1 (3.7%) | 1 | 2 | 3 (11) | 3 | **10** | 004, 009, 010, 011 |
| 6 | Idempotency and duplicate side effects | 1 (7.2% payments) | 1 | 2 | 2 (6 tagged) | 3 | **9** | 003 B1 |
| 7 | Config, deploy and schema-migration changes | 2 (9.7%) | 0 | 3 | 0 | 3 | **8** | no |
| 8 | Plain logic slips (wrong variable, inverted guard, identity vs equality, write scope) | 0 | 2 | 2 | 2 (8) | 2 | **8** | many injected bugs |
| 9 | Tenant / scope filter missing | 2 (8.5%) | 0 | 1 | 1 (4) | 3 | **7** | 005, 003 B4 |
| 10 | Caching: key mismatch, invalidation, stampede | 2 (19%) | 0 | 2 | 1 (4) | 2 | **7** | 003 B4 (keying) |
| 11 | Time, calendars and time zones | 2 (16.5% payments) | 1 | 1 | 1 (4) | 2 | **7** | 008 (DST) |
| 12 | Aggregation over fanned-out joins (wrong counts and sums) | 2 (data correctness) | 0 | 0 | 1 (3) | 2 | **5** | no |
| 13 | Pagination and ordering | 0 (0.3%) | 0 | 0 | 1 (4) | 2 | **3** | no |

Ties are broken by cost, then by literature. The mined-bug column is biased toward small logic fixes (the mining filter keeps fixes of 30 lines or fewer). That is why classes 1, 4 and 7, where real fixes tend to be large or live in configuration, score low there even though outages show them often.

## 2. The classes

For each class: what goes wrong, the evidence, real instances, and the **genuine question** someone asked while stuck. Every question is labelled: *quoted/paraphrased* means taken from the linked source; *reconstructed* means my wording of the symptom the fix addresses, not a quote.

### 1. Partial failure around external calls

**What goes wrong.** A call to another system (card network, payment provider, tax service, email) fails, times out, or succeeds without the reply arriving. The error path then leaves local state inconsistent with the outside world: charged with no order, order with no charge, or a handler that only logs the error.

**Evidence.**
- Yuan et al.: **92% of catastrophic failures** come from mishandling errors the software had already signalled; 35% are trivial handlers (empty, log-only, catch-all abort, TODO).
- CBS: error handling is 18% of cloud bugs, second only to logic.
- Brandur/Stripe: "success with lost response" and "foreign state mutation" are the reasons idempotency keys exist.
- Interviews: Stripe's integration round leans "heavy on error handling"; DoorDash Code Craft wants downstream failures handled; a Coinbase candidate was rejected over error handling.
- Postings: fault tolerance and failover appear in 30% of postings.

**Instances.**
- Saleor S33 ([PR #10952](https://github.com/saleor/saleor/pull/10952)): checkout validation fails after the charge, and nothing refunds it.
- Saleor S9 ([PR #18079](https://github.com/saleor/saleor/pull/18079)): a failing sync webhook is re-called by every request.
- danluu list: the Amazon EBS memory leak and continuous retries; CircleCI's RabbitMQ ack timeout.

**Genuine question.** "Did the charge go through, and is it safe to retry?" (*paraphrased*, [Stripe blog 2017](https://stripe.com/blog/idempotency)). "Why was the customer charged when no order exists?" (*reconstructed*, S33).

### 2. Concurrency: check-then-act, lost update, lock ordering

**What goes wrong.** Two requests read the same state, both decide, and both act. Or a lock is taken in the wrong place, released too early, or taken in different orders on different paths.

**Evidence.**
- TaxDC: order violations are 44% of distributed concurrency bugs and atomicity violations 20%; 47% fail silently.
- Jepsen, MySQL 8.0.34: the default Repeatable Read loses committed updates in read-modify-write code without any error.
- CBS: data races are 12% of cloud bugs.
- Interviews: Stripe's bug bash reports a race from an "unguarded read-modify-write sequence"; Adyen's code review digs into Java concurrency.
- Postings: 16% mention concurrency.

**Instances.**
- Saleor S1 ([#19891](https://github.com/saleor/saleor/pull/19891)): two concurrent adds create two lines.
- Saleor S14 ([#17641](https://github.com/saleor/saleor/pull/17641)): a concurrent sign-up crashes on the unique constraint.
- Saleor S27 ([#12657](https://github.com/saleor/saleor/pull/12657)): a lock is taken in its own transaction and released before the work.
- Saleor S5 ([#19001](https://github.com/saleor/saleor/pull/19001)) and Oscar O1 ([#4594](https://github.com/django-oscar/django-oscar/pull/4594)): deadlocks from inconsistent lock order.

**Genuine question.** "Why does one cart have two lines for the same product?" (*reconstructed* from the S1 commit message, which explains both requests seeing no line and both inserting). "Why did a committed update disappear with no error?" (*paraphrased*, Jepsen MySQL).

### 3. Money arithmetic and double counting

**What goes wrong.** An amount is computed in the wrong order or from the wrong inputs: the override is checked after a derived price, rounding happens at the wrong step, each term is clamped before summing, a value goes through a float, or two amounts in different units are compared. Or the same discount or surcharge is applied by two layers.

**Evidence.**
- Postings: in payments-titled roles, ledgers or money movement appear in 50% and data correctness or reconciliation in 45%.
- Mining: the largest class, 13 cards in all four repos.
- danluu list: Twilio's 2013 billing double charge (via retries).
- The literature says little. The studies cover infrastructure systems, and small money bugs rarely get public post-mortems.

**Instances.**
- Saleor S13 ([#17926](https://github.com/saleor/saleor/pull/17926)): a gift card drives the net total below zero.
- Saleor S30 ([#10366](https://github.com/saleor/saleor/pull/10366)): clamping each term before summing hides overselling.
- Saleor S21 ([#16814](https://github.com/saleor/saleor/pull/16814)) and S22 ([#16738](https://github.com/saleor/saleor/pull/16738)): a discount applied twice.
- Hyperswitch H5 ([#9073](https://github.com/juspay/hyperswitch/pull/9073)): surcharge double-counted on incremental authorization.
- Hyperswitch H8 ([#5873](https://github.com/juspay/hyperswitch/pull/5873)): the wrong amount field is used to detect partial payment.
- Kill Bill K9 ([d7526fb](https://github.com/killbill/killbill/commit/d7526fb64)): tier limits routed through double.
- Oscar O3 ([#4448](https://github.com/django-oscar/django-oscar/pull/4448)): rounding at the wrong step.
- Saleor S31 ([#10147](https://github.com/saleor/saleor/pull/10147)): a zero total makes an equality check vacuously true.

**Genuine question.** "Two warehouses with 1 each show 1 available, but 2 and 1 show 3. Why?" (*paraphrased* from the [S2 commit message](https://github.com/saleor/saleor/pull/19876); S2 sits in class 12 but surfaces as a money/stock number). "Why does the tax app see the shipping discount twice?" (*reconstructed*, S21).

### 4. Retries, timeouts and overload amplification

**What goes wrong.** A retry loop with no delay or budget, retries at several layers that multiply, no memory of recent failures, timeouts longer than the caller's deadline, or reconnect storms after a blip.

**Evidence.**
- SRE book ch. 21-22: at most 3 attempts per request, a 10% retry budget, retry at one layer only, propagate deadlines.
- danluu list: about 14% of entries mention overload, 15% cascading failure, 5% retries. Examples: Spotify (no backoff), Slack and Discord (reconnect storms), LaunchDarkly (SDK retries).
- COS: LOAD causes 9% of outages.
- Interviews: DoorDash Code Craft asks for retries; Stripe design rounds ask how to retry webhooks to a hanging server; Ramp's online assessment has a rate limiter.
- Postings: only 3.4% name retries and timeouts explicitly.

**Instances.**
- Hyperswitch H3 ([#9308](https://github.com/juspay/hyperswitch/pull/9308)): lock retries with no delay.
- Saleor S9 ([#18079](https://github.com/saleor/saleor/pull/18079)): failures not cached.

**Genuine question.** "Why do we get 'resource busy' when the lock is free a few milliseconds later?" (*reconstructed*, H3). "Why did a short blip become a long outage?" (*reconstructed* from the danluu entries for Spotify and Slack).

### 5. Lifecycle / state-machine errors

**What goes wrong.** An event or transition is allowed from a state that should forbid it (a draft order is charged or auto-confirmed). A non-terminal state is grouped with terminal ones. A derived status is not recomputed when one of its inputs changes. A later, less authoritative event overwrites a value that should stay.

**Evidence.**
- Mining: 11 cards, the second largest class.
- TaxDC: order violations; Brandur: recovery points (a request's position in its lifecycle).
- ReadCode already ships 004, 009, 010 and 011 in this class.
- Postings name it rarely (3.7%).

**Instances.**
- Saleor S8 ([#18457](https://github.com/saleor/saleor/pull/18457)) and S23 ([#16385](https://github.com/saleor/saleor/pull/16385)): draft orders.
- Saleor S11 ([#18019](https://github.com/saleor/saleor/pull/18019)): a zero-total checkout never becomes authorized.
- Saleor S15 ([#17632](https://github.com/saleor/saleor/pull/17632)): a fully refunded order shows refunded = 0.
- Saleor S25 ([#14538](https://github.com/saleor/saleor/pull/14538)): charge status stale after a granted refund.
- Hyperswitch H4 ([#4229](https://github.com/juspay/hyperswitch/pull/4229)): "processing" treated as terminal.
- Hyperswitch H10 ([#13853](https://github.com/juspay/hyperswitch/pull/13853)): a failed void blocks refunds.
- Hyperswitch H9 ([#13982](https://github.com/juspay/hyperswitch/pull/13982)) and H14 ([#4149](https://github.com/juspay/hyperswitch/pull/4149)): later events overwrite earlier ones.

**Genuine question.** "Why is totalRefunded 0 on a fully refunded order?" (*paraphrased* from the S15 PR title).

### 6. Idempotency and duplicate side effects

**What goes wrong.** The same logical request or event produces its effect twice: a client retry, a webhook redelivered, a handler subscribed to two events, a cache filled too late so concurrent callers all do the work, or a duplicate key treated as a replay without comparing the request.

**Evidence.**
- Brandur/Stripe (two pieces): the canonical treatment.
- danluu list: Twilio charging customers several times; Gmail sending the same mail more than 20 times.
- Postings: 2.5% overall but 7.2% in payments roles, at 39 companies including Stripe, Airwallex and Block.
- Interviews: probed mainly in Stripe-style design rounds (prep-site sources).

**Instances.**
- Hyperswitch H2 ([#5282](https://github.com/juspay/hyperswitch/pull/5282)): a duplicate refund_id silently returns the old refund.
- Saleor S37 ([#11509](https://github.com/saleor/saleor/pull/11509)): the tax provider is called twice.
- Saleor S26 ([#14323](https://github.com/saleor/saleor/pull/14323)): the auth plugin is called once per waiting promise.
- Saleor S1 and S27 (see class 2).

**Genuine question.** "Why were customers charged multiple times?" (*paraphrased*, Twilio 2013 via [danluu/post-mortems](https://github.com/danluu/post-mortems)).

### 7. Config, deploy and schema-migration changes

**What goes wrong.** A configuration push, rollout or schema change meets old data or old code: a column type changes while old rows remain, an ID column hits INT32, a rollback makes newer rows unreadable, a migration takes locks.

**Evidence.**
- COS: upgrades cause 16% of outages and configuration 10%.
- danluu list: Config Errors is the largest section (59 of 240 entries). Examples: CircleCI's column type change, GitHub's INT32 key, Basecamp, Strava, Mandrill's transaction-ID wraparound.
- CBS: configuration is 14% of cloud bugs.
- Postings: migrations appear in 9.7%.
- Mined: none, by construction (the filter drops migrations and configuration).

**Instances.** Kill Bill K7 ([dd5f515](https://github.com/killbill/killbill/commit/dd5f5157a)) is the nearest code-level cousin (integer arithmetic in a comparator).

**Genuine question.** "Why did rolling back make it worse?" (*paraphrased*, the CircleCI 2021 entry: rows written between the two deploys became unreadable).

**ReadCode fit.** This class fits the **incident-ticket** mode better than the bug hunt.

### 8. Plain logic slips

**What goes wrong.** A stale or near-identically named variable is read; a boolean guard is inverted; objects are compared by identity or hash instead of value; a set-style call replaces relations instead of adding to them; a symmetric relation is updated on one side only.

**Evidence.**
- CBS: logic is the largest bug type (29%).
- Interviews: Stripe bug bash reports a missing check and leading whitespace in map keys.
- Postings never name it.

**Instances.**
- Saleor S7 ([#18599](https://github.com/saleor/saleor/pull/18599)): the old record's rule is read instead of the new one.
- Saleor S35 ([#13724](https://github.com/saleor/saleor/pull/13724)): an ignored return value means every gift card pays the full total.
- Saleor S3 ([#19804](https://github.com/saleor/saleor/pull/19804)): `set()` used instead of `add()`.
- Kill Bill K5 ([015a775](https://github.com/killbill/killbill/commit/015a77523)): an inverted guard.
- Kill Bill K6 ([13e1dfb](https://github.com/killbill/killbill/commit/13e1dfb65)): UUIDs compared with `==`.
- Kill Bill K7: a hashCode tiebreak drops records.
- Oscar O5 ([#4102](https://github.com/django-oscar/django-oscar/pull/4102)) and O6 ([#4017](https://github.com/django-oscar/django-oscar/pull/4017)).

**Genuine question.** "Why does each gift card get charged the whole order?" (*reconstructed*, S35).

### 9. Tenant / scope filter missing

**What goes wrong.** A query or cache that must be scoped to a merchant, owner or "not deleted" misses the filter on one path. Often the cause is a join key that is unique only within a tenant, or an empty filter that matches everything.

**Evidence.**
- Postings: multi-tenancy 8.5%, authorization and permissions 26%.
- danluu list: the OpenAI Redis bug showed users other users' data; a GitHub failover routed 16 private repos to the wrong owners.
- Mining: 4 cards.
- No interview reports found.

**Instances.**
- Hyperswitch H1 ([#6917](https://github.com/juspay/hyperswitch/pull/6917), issue #6916): a join not scoped by merchant.
- Oscar O2 ([#4501](https://github.com/django-oscar/django-oscar/pull/4501)): an empty filter shows superusers the latest order.
- Kill Bill K4 ([85a45b0](https://github.com/killbill/killbill/commit/85a45b0ed)): the soft-delete filter missing from some queries.
- Hyperswitch H7 ([#4916](https://github.com/juspay/hyperswitch/pull/4916)): producer and consumer disagree on the stream name.

**Genuine question.** "Why does merchant B's payment list show merchant A's attempt?" (*reconstructed* from the H1 PR, whose author found it testing two merchants that shared an ID).

### 10. Caching: key mismatch, invalidation, stampede

**What goes wrong.** The invalidation uses a different key from the read, the key includes volatile fields so it never hits, the cache is filled only after the work so concurrent callers all miss, or a cold cache after failover floods the backend.

**Evidence.**
- Postings: caching 19% (but 6.5% in payments roles).
- SRE book: cold caches.
- COS: a failover cold-cache load spike.
- danluu list: GitHub's shortened cache TTL; Slack removing cache nodes.

**Instances.**
- Hyperswitch H6 ([#6907](https://github.com/juspay/hyperswitch/pull/6907)) and H13 ([#5918](https://github.com/juspay/hyperswitch/pull/5918)): invalidation key mismatch.
- Saleor S26: stampede.

**Genuine question.** "Why does my updated surcharge rule not apply?" (*reconstructed*, H6).

### 11. Time, calendars and time zones

**What goes wrong.** A local date is turned into an instant (or back) in the wrong time zone, months are stepped without re-aligning to the billing day, a loop step can be zero, or the clock jumps (leap second, DST).

**Evidence.**
- Postings: 6% overall, **16.5% in payments roles**.
- danluu list: a Time section (leap seconds; an Azure certificate-expiry date bug).
- Interviews: Ramp's assessment includes overlapping calendar events.
- Mining: all four cards come from the billing engine (Kill Bill).

**Instances.**
- Kill Bill K1 ([#2136](https://github.com/killbill/killbill/pull/2136), issue #2133): end-of-month billing day.
- Kill Bill K2 (issue #1981) and K3 (issue #1966): usage for PST accounts.
- Kill Bill K8 (issue #2091): an infinite loop on a no-period phase.

**Genuine question.** "Why are PST accounts missing usage from the end of the day?" (*reconstructed*, K2).

**Taxonomy gap.** `taxonomy.json` has no time skill. Problem 008 already had to use `input-validation`.

### 12. Aggregation over fanned-out joins

**What goes wrong.** A join multiplies rows; a COUNT or SUM on top counts duplicates; a DISTINCT added to fix that also merges legitimately equal values.

**Evidence.** Data correctness appears in 16% of postings (45% in payments roles). The studies are silent on it.

**Instances.**
- Saleor S2 ([#19876](https://github.com/saleor/saleor/pull/19876)): SUM(DISTINCT).
- Saleor S4 ([#19008](https://github.com/saleor/saleor/pull/19008)): an OR across two to-many joins.
- Oscar O4 ([#4107](https://github.com/django-oscar/django-oscar/pull/4107)): an inflated COUNT.

**Genuine question.** The S2 question under class 3 (*paraphrased*).

### 13. Pagination and ordering

**What goes wrong.** The keyset cursor compares in the wrong direction on ties, the sort key is truncated (datetime to date), two implementations of the page-info contract disagree, or the tie-breaker differs between the order shown and the order changed.

**Evidence.** The weakest outside signal: 8 of 2,678 postings, no interview reports, no study. Found only by mining (4 cards, all Saleor).

**Instances.**
- Saleor S19 ([#17222](https://github.com/saleor/saleor/pull/17222)).
- Saleor S32 ([#9741](https://github.com/saleor/saleor/pull/9741)).
- Saleor S6 ([#18810](https://github.com/saleor/saleor/pull/18810)).
- Saleor S18 ([#17276](https://github.com/saleor/saleor/pull/17276)).

**Genuine question.** "A cursor from the first item returns an empty list instead of the second item." (*paraphrased* from the [S19 PR page](https://github.com/saleor/saleor/pull/17222), checked.)

## 3. Best first problems

Pick from high-ranked classes that ReadCode does not cover yet, where a real bug distils to under 60 lines and a playground can show it.

1. **Concurrency check-then-act: S27 (lock released before the work) or S1 (duplicate cart line).** Rank 2, not covered by any problem, high cost. The buggy code *looks* protected: it has `SELECT ... FOR UPDATE` and a comment saying so. That is exactly the "wild, not tame" quality we want. It needs a two-request interleaving lever in the playground (one step beyond 003's fault injection).
2. **Partial failure: S33 (charged, validation fails, no refund).** Rank 1, the class interviews probe most, and only partly covered (003 B1 is about dedup, not compensation). It reproduces with the existing "charge then fail" fault lever. It works as an incident ticket ("customer charged, no order") and as a review-the-PR task (a PR that adds a refund on one path but not the other).
3. **Tenant join: H1 (join key unique only per merchant).** Rank 9 on frequency, but cost 3 and a different mechanism from 005. The reproduction needs two accounts with colliding merchant-supplied IDs, and the fix is one line. That makes a good multiple-choice "where" question, with distractors built from the filter that *is* present.

Cheap fillers (sharp, well verified, low rank): **S2** SUM(DISTINCT) on equal values (rung 1-2, needs only SQLite) and **S19** reversed cursor tie-break (confirmed symptom). Hold back on more state-machine problems: four already exist. Use class 7 (config and migrations) for incident tickets, not bug hunts.

## 4. Methods

- **Postings.** 282 company slugs probed on Greenhouse, Ashby and Lever public APIs; 164 boards (158 companies) answered with 17,418 postings. Kept 2,678 de-duplicated engineering postings whose titles look backend, API, platform or infrastructure (excluding sales, solutions, ML, frontend, mobile and hardware). Counted 28 keyword themes with regexes saved in `jobs/job-theme-counts.json`. Scripts: `jobs/probe.py`, `jobs/analyze.py`.
- **Interviews.** About 15 web searches and a few page fetches. Glassdoor and Blind were read only as search snippets (they block fetching). Each claim in `interviews.md` carries a link and a confidence level.
- **Literature.** Read the PDFs of Yuan (OSDI 2014), CBS (SoCC 2014), COS (SoCC 2016) and TaxDC (ASPLOS 2016), plus the SRE-book chapters, Cook, Brandur and two Jepsen analyses. Counted the danluu list by script (`literature/postmortems.py`).
- **Bugs.** `docs/prompts/mine-bugs.md` on four permissive repos (licenses checked at HEAD), mined from shallow git clones so that **no GitHub REST API calls were spent**. About 1,586 fix-like small commits were filtered automatically, about 77 diffs read, 59 accepted. Exact code comes from git via `bugs/build_cards.py`; the analysis is in `bugs/cards_spec.py`.
- **Merge.** Every class was scored with the fixed 0-3 rule in section 1, written down before scoring.

## 5. Limitations

- **The sources measure different things.** Postings measure what employers *say*; interviews measure what candidates *remember*; outage studies measure infrastructure systems (Hadoop, Cassandra, big web services), not payments code; mined bugs measure what small fixes in four repos look like. The scoring rule adds them up, which is a judgment call. The per-source columns are there so anyone can re-weight.
- **Mining bias.** The ≤30-line, logic-only filter excludes the large fixes typical of error handling, retries and migrations, and 32 of 59 cards come from Saleor. Kill Bill supplies all the time cards; Hyperswitch fixes rarely add tests (41 of 59 cards have a regression test).
- **Symptoms are mostly paraphrased** from PR titles and commit messages. Only S19, S27 and H1 were checked on their PR pages, and S27's page names no concrete symptom. No issue threads were read, and the "not famous" web check from the mining prompt was not run per bug.
- **Keyword counting** catches boilerplate and misses synonyms. Title filtering let through some non-backend roles. A few slugs may belong to a different company with the same name. Big employers (OpenAI, Databricks, Okta) weigh heavily. Several target companies (Marqeta, Checkout.com, Klarna, Revolut, Shopify, Uber, Square) are missing because their boards were not found under the tried slugs.
- **Interview evidence is thin and anecdotal:** 12 companies, mostly secondary sources, some years old. Nothing was found for Shopify, Affirm, Chime, Mercury or Marqeta.
- **Unverified items:**
  - The PostgreSQL 12.3 Jepsen finding (not read).
  - The exact Glassdoor and Blind wording (snippets only).
  - The intent behind H2 (whether identical replays should still succeed).
  - The H7 and H8 symptoms (inferred).
  - The K7 user impact (no linked report).
  - The original-issue numbers for most Saleor and Hyperswitch PRs.
- **Taxonomy gaps found.** Seven cards fit no `taxonomy.json` skill. The skills that would cover them: *time/calendar*, *aggregation/join fan-out*, *write scope* (a write that clobbers or misses related records), *error handling / compensation*.
