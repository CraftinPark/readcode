# Job postings: what backend / API / payments roles ask for

Pulled 2026-10-24 from public job-board APIs (Greenhouse, Ashby, Lever). No login, no LinkedIn.

## Numbers

| | count |
|---|---|
| company slugs probed (each on all three boards) | 282 |
| boards that answered with jobs | 164 (158 distinct companies) |
| postings downloaded | 17,418 |
| backend / API / platform engineering postings after title filter and de-duplication | **2,678** at **142 companies** |
| ...by company category | payments/fintech 688, developer/API platforms 799, commerce/marketplaces 295, infra 896 |
| postings whose *title* names payments/ledger/billing/money/card/treasury/banking/risk/fraud | 139 |

Biggest contributors after de-duplication: OpenAI 173, Databricks 156, Okta 123, Anthropic 115, Stripe 99, Cloudflare 89, MongoDB 79, Snowflake 75, Airwallex 71, Affirm 69. Slugs that returned nothing (e.g. Marqeta, Checkout.com, Klarna, Revolut, Shopify, Uber, DoorDash's `doordash`, Square) were skipped; their boards live elsewhere or under other names.

## Share of the 2,678 postings that mention each theme (keyword regex on the posting text)

| theme | postings | % | companies | % in payments-titled postings (n=139) |
|---|---:|---:|---:|---:|
| observability (monitoring, metrics, tracing, SLOs) | 1,589 | 59.3 | 128 | 58.3 |
| scalability / performance | 1,426 | 53.2 | 123 | 48.9 |
| distributed systems | 1,246 | 46.5 | 110 | 47.5 |
| debugging / troubleshooting | 860 | 32.1 | 106 | 25.2 |
| SQL / databases | 852 | 31.8 | 121 | 32.4 |
| availability / fault tolerance / failover | 813 | 30.4 | 104 | 28.1 |
| testing | 803 | 30.0 | 107 | 25.9 |
| queues / async / event-driven | 749 | 28.0 | 109 | 30.9 |
| code review | 735 | 27.4 | 95 | 27.3 |
| incidents / postmortems / outages / root cause | 730 | 27.3 | 107 | 22.3 |
| authz / authn / permissions | 701 | 26.2 | 98 | 26.6 |
| on-call | 625 | 23.3 | 102 | 28.8 |
| caching | 511 | 19.1 | 77 | 6.5 |
| API design / versioning / backward compatibility | 464 | 17.3 | 94 | 23.0 |
| concurrency / race conditions / locking | 436 | 16.3 | 69 | 10.8 |
| data correctness / integrity / reconciliation | 434 | 16.2 | 81 | **44.6** |
| migrations / backfills / zero-downtime | 261 | 9.7 | 78 | 5.0 |
| ledgers / settlement / payouts / money movement | 229 | 8.6 | 57 | **49.6** |
| multi-tenancy | 228 | 8.5 | 51 | 2.9 |
| time zones / clock skew / DST | 167 | 6.2 | 46 | **16.5** |
| PCI / SOX / KYC / AML / regulatory | 158 | 5.9 | 58 | 14.4 |
| consistency models / transactions / isolation | 123 | 4.6 | 40 | 10.1 |
| state machines / workflow orchestration | 100 | 3.7 | 39 | 3.6 |
| retries / timeouts / backoff / circuit breakers | 91 | 3.4 | 48 | 5.0 |
| rate limiting / throttling / load shedding | 85 | 3.2 | 37 | 1.4 |
| idempotency / exactly-once / dedup / double charge | 67 | 2.5 | 39 | 7.2 |
| webhooks | 36 | 1.3 | 27 | 2.2 |
| pagination | 8 | 0.3 | 8 | 0.0 |

## What this says

1. **Postings name areas, not failure mechanisms.** "Observability", "scale", "distributed systems" appear in half of all postings; the mechanisms a reader actually debugs (idempotency, retries, pagination, webhooks) appear in under 4%. Postings tell us *where* to set problems (money movement, data correctness, on-call), not *which bug* to plant. Use the other three sources for that.
2. **Payments roles are about correctness.** In payments-titled roles, "data correctness/reconciliation" jumps from 16% to 45%, ledgers from 9% to 50%, time zones from 6% to 17%, idempotency from 2.5% to 7%. Caching and multi-tenancy drop. That matches the mined bugs: most payments-repo bugs are money arithmetic and state, not performance.
3. **Operating the system is part of the job.** Incident response (27%), on-call (23%) and debugging (32%) are common requirements, which supports ReadCode's incident-ticket and review-the-PR modes as much as the bug hunt.

## Files

- `job-roles.csv`: one row per kept posting (company, board, category, title, location, URL, date, themes hit). No posting text is stored.
- `job-theme-counts.json`: all counts above, per-category shares, per-company counts and the exact regexes.
- `probe.py`, `analyze.py`: the scripts (re-runnable; results will drift as boards change).

## Caveats

- Title filter is regex-based. Spot checks found false positives (e.g. "Supply Chain Data Engineer & Integration Manager", "GTM Business Systems Engineer") and it excludes ML, frontend and mobile titles on purpose.
- Theme counts are keyword hits, so they include boilerplate and benefit text; a word in a posting is not a measure of how much the job depends on it. Datadog's own postings say "datadog" (counted as observability).
- A few slugs could belong to a different organisation with the same name (`current`, `unit`, `remote`, `bond`, `column`, `fly`, `lambda`); their totals are small and not checked one by one.
- Snapshot of one day; boards change daily.
