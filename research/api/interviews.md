# Interview reports: debugging, "bug squash", code review and reliability design rounds

Gathered 2026-10-24 by web search. **Every source here is a self-reported candidate account or a third-party prep guide, not company material.** Formats change by team, level and year. Glassdoor and Blind pages were seen only as search snippets (both block direct fetching), so their details are marked *(snippet)*.

## What the rounds look like

| Company | Round | What candidates report | Sources | Confidence |
|---|---|---|---|---|
| **Stripe** | Bug Bash / "bug squash" (onsite, 45-60 min) | Unfamiliar repository with failing tests or an open issue; find root cause and fix; narrate hypotheses. A "clear, well-articulated diagnosis often carries more than a completed fix". Reported bugs: a missing directory check, a missing AST visitor, a race condition from an "unguarded read-modify-write sequence", leading whitespace in map keys, a language parser. Time sink: an unrelated failing test suite ate ~20 minutes. | [Aced/Exponent Stripe guide (2026)](https://www.aced.io/guides/stripe/swe-interview); [Blind: stripe bug squash](https://www.teamblind.com/post/stripe-bug-squash-interview-gyamarmf) *(snippet)*; [Glassdoor FR 2021 review](https://www.glassdoor.fr/Entretien/Stripe-Entretien-E671932-RVW45809795.htm) *(snippet)*; [Interview Query](https://www.interviewquery.com/guides/stripe-software-engineer) | High that the round exists and uses a real repo; medium on specific bugs |
| **Stripe** | Integration | Implement a small feature in an unfamiliar codebase against a provided API/SDK, with docs; "pure API work... lean heavy on error handling"; HTTP calls and JSON parsing. | Aced guide; [1point3acres onsite overview](https://www.1point3acres.com/interview/post/7298079) *(snippet)* | Medium |
| **Stripe** | System design | API-first; third-party guides stress idempotency keys, immutable ledgers, state machines safe under retries, webhook delivery to a hanging merchant server with backoff. | [Educative](https://www.educative.io/blog/stripe-system-design-interview-questions), [techinterview.org](https://www.techinterview.org/post/3233474171/system-design-payment-system-stripe-idempotency-double-charge-prevention-ledger-reconciliation-pci-compliance-webhooks/), [PracHub "just make it idempotent is half an answer"](https://prachub.com/resources/just-make-it-idempotent-is-half-an-answer-in-a-system-design-interview) | Low-medium: prep-site content, not candidate reports |
| **Retool** | Debugging (first round) | Clone a repo (or receive code by email) and debug it. | [Medium: debugging interview at Stripe and Retool](https://medium.com/tech-pulse/navigating-the-debugging-interview-insights-from-stripe-and-retool-697cead7c4db) *(snippet; page returned 403)* | Medium |
| **DoorDash** | Debugging + "Code Craft" | Debugging: code with 3-4 bugs, or buggy implementation *and* buggy tests that must all pass; sometimes a production-like service failure in a repo. Code Craft: build an API that calls several downstream services, handling **errors, parallel calls and retries**; graded on running code. | [Blind: doordash debugging code craft](https://www.teamblind.com/post/doordash-debugging-code-craft-dbj4pqt8) *(snippet)*; [LeetCode discuss](https://leetcode.com/discuss/interview-experience/7203153); [1point3acres](https://www.1point3acres.com/interview/thread/1104009) *(snippet)* | Medium-high |
| **Brex** | Debugging challenge | Listed as an onsite component (coding, design, debugging, values); candidates call it different from usual loops. Format details not found. | [jointaro Brex reports](https://www.jointaro.com/interviews/companies/brex/work-experiences/senior-software-engineer-may-18-2023-3-9d42db8e); [Blind](https://www.teamblind.com/post/brex-on-site-round-qzvyvlj7) *(snippet)* | Medium on existence, low on content |
| **Coinbase** | Staged debugging / pair programming | Staged exercise where later stages must not break earlier ones; one candidate rejected over "debugging/error handling" feedback (Mar 2026). | [PracHub Coinbase report](https://prachub.com/interview-experiences/coinbase-software-engineer-interview-experience-rejected-after-onsite-over-a-debugging-nitpick); [Exponent Coinbase guide](https://www.tryexponent.com/guides/coinbase-software-engineer-interview) | Medium |
| **Adyen** | Code review + bug-fix assessment | Timed Codility-style test incl. a bug-fixing task where only two lines may change, and a task whose description does not match its unit tests; a 60-minute code review panel (one author, two reviewers) probing Java depth, **concurrency** most often. | [Glassdoor UK](https://www.glassdoor.co.uk/Interview/Adyen-Interview-E684495-RVW32574332.htm) *(snippet)*; [Interview Query Adyen](https://www.interviewquery.com/guides/adyen-software-engineer) | Medium (2020-2024 reports) |
| **Spotify** | Debugging (backend) | Interviewer states a production problem and reveals system facts gradually as you ask; expected output is root cause plus fixes. | [Blind: spotify onsite backend](https://www.teamblind.com/post/spotify-onsite-backend-engineer-xj3tab1y) *(snippet)* | Low-medium |
| **Evernote** | Debugging | Small codebase (100-200 lines) with failing tests; find and fix. | [Blind: evernote onsite](https://www.teamblind.com/post/evernote-onsite-interview-uvt6g6e8) *(snippet)* | Low (old) |
| **Ramp** | OA + onsite | OA prompts reported: a **rate limiter**, a calendar with **overlapping events**; onsite: practical coding, product coding, system design. No debugging round reported. | [Interview Query Ramp](https://www.interviewquery.com/guides/ramp-software-engineer); [designgurus](https://www.designgurus.io/answers/detail/what-is-the-ramp-interview-process-like-round-by-round) | Low-medium |
| **Plaid** | Onsite | Build-and-extend coding, system design on bank integrations, **data sync and webhooks**, project deep dive. No debugging/code-review round found. | [designgurus Plaid](https://www.designgurus.io/answers/detail/what-is-the-plaid-interview-process-like-round-by-round); [Interview Query Plaid](https://www.interviewquery.com/interview-guides/plaid-software-engineer) | Low-medium |
| **Block / Square** | Pair programming | 3 pair-programming rounds on practical multi-part problems + system design (mostly 2015-2019 reviews); a 2025 SF review: hotel booking design. | [Glassdoor Block](https://www.glassdoor.fr/Entretien/Block-Entretien-E422050-RVW10065446.htm) *(snippet)* | Low (dated) |
| HashiCorp | Code pairing with a PR review | One candidate described a PR review component. | [jointaro HashiCorp](https://www.jointaro.com/interviews/companies/hashicorp/work-experiences/software-engineer-june-9-2022-5-6632b0d8) *(snippet)* | Low |

Not found: anything on Shopify, Affirm, Chime, Mercury or Marqeta debugging rounds; nothing from interviewing.io's own material on debugging rounds (searches returned other sites).

## What the rounds probe, counted across the table (companies, not reports)

| Failure / skill | Companies whose reports mention it | Which |
|---|---:|---|
| Reading unfamiliar code with failing tests | 6 | Stripe, Retool, DoorDash, Evernote, Coinbase, Adyen |
| Error handling / partial failure of a dependency | 4 | Stripe (integration), DoorDash (code craft), Coinbase, Spotify (root cause) |
| Concurrency / race / read-modify-write | 2 | Stripe (bug bash), Adyen |
| Retries | 2 | DoorDash, Stripe (webhook design, guides) |
| Idempotency / double charge | 1-2 | Stripe (design, from prep sites) |
| Webhooks / data sync | 2 | Stripe (design), Plaid (design) |
| Rate limiting | 1 | Ramp (OA) |
| Time / overlapping intervals | 1 | Ramp (OA) |
| Code review of someone else's change | 2 | Adyen, HashiCorp |
| Pagination, caching, tenant isolation, migrations | 0 | none found |

## Takeaways for ReadCode

1. The **format** ReadCode plans (real unfamiliar code, failing test or ticket, diagnosis valued over a finished fix) matches what Stripe, DoorDash, Retool and Coinbase run. The "diagnosis carries more than the fix" line supports grading *why* separately from *fix*.
2. Interviews probe **error handling around dependencies** and **concurrency** more than domain bugs. Payments-domain failures (idempotency, ledgers, webhooks) appear mostly in *design* rounds, i.e. as talk, not as code to debug. ReadCode can fill that gap: domain failures as code.
3. "A description that does not match its tests" (Adyen) and "unrelated failing tests eat your time" (Stripe) are both real; a problem can deliberately include a red-herring failure.
