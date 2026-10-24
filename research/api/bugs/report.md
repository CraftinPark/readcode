# Mined real bugs: report

Method: `docs/prompts/mine-bugs.md`, run on local `git clone --shallow-since=2021-10-01` copies (no GitHub API calls), commits from 2022-01-01 to 2026-10-24. `candidates.py` keeps commits whose subject looks like a fix and that change at most 30 non-test lines in at most 3 non-test files (migrations, schema dumps, docs and lock files excluded from the count). I then read the diff of each shortlisted candidate (`view.py`) and wrote the analysis in `cards_spec.py`; `build_cards.py` copies `buggy`/`fixed`, line ranges (pre-fix side), commits and the added regression test from git, so no code in `bugs.jsonl` is typed by hand.

| Repo | License (checked in LICENSE at HEAD) | Fix-like small commits found | Diffs read | Accepted |
|---|---|---:|---:|---:|
| saleor/saleor | BSD-3-Clause | 474 | ~40 | 32 |
| killbill/killbill | Apache-2.0 | 141 | ~12 | 9 |
| juspay/hyperswitch | Apache-2.0 | 902 | ~16 | 12 |
| django-oscar/django-oscar | BSD-3-Clause | 69 | ~9 | 6 |
| **total** | | 1,586 | ~77 | **59** |

medusajs/medusa was considered and skipped: its LICENSE is MIT except for Enterprise Edition material under a separate license, which would need path-by-path checking.

## Accepted bugs

| id | title | pattern | skills | elus. | distance | link |
|---|---|---|---|---:|---|---|
| S1 | Two concurrent 'add item' calls create two cart lines for one product | check-then-act: decision computed before the lock, acted on after it | race-condition, idempotency | 4 | other file | [saleor #19891](https://github.com/saleor/saleor/pull/19891) |
| S2 | Stock across warehouses undercounted when two warehouses hold the same quantity | DISTINCT inside an aggregate collapses equal values from different rows | money-invariants | 4 | same function | [saleor #19876](https://github.com/saleor/saleor/pull/19876) |
| S3 | Bulk-creating gift cards strips the tag from all earlier gift cards | replace-semantics call used where append was meant; write clobbers unrelated rows | (none fits) | 2 | same function | [saleor #19804](https://github.com/saleor/saleor/pull/19804) |
| S4 | Attribute filter returns the same attribute several times | OR across two to-many joins duplicates rows | pagination | 3 | same function | [saleor #19008](https://github.com/saleor/saleor/pull/19008) |
| S5 | Deadlocks between order/checkout updates and line deletes | inconsistent lock ordering across code paths | race-condition | 5 | other file | [saleor #19001](https://github.com/saleor/saleor/pull/19001) |
| S6 | Nested list pagination reports hasPreviousPage=false on page 2 | two implementations of one contract drift apart | pagination, backward-compat | 3 | other file | [saleor #18810](https://github.com/saleor/saleor/pull/18810) |
| S7 | Gift promotion recalculated with the old rule | reads the stale record instead of the new value (near-identical names) | money-invariants | 3 | same function | [saleor #18599](https://github.com/saleor/saleor/pull/18599) |
| S8 | 'Order charged' webhooks fire for draft orders | side effect emitted before the entity reaches the state that justifies it | state-machine | 3 | same function | [saleor #18457](https://github.com/saleor/saleor/pull/18457) |
| S9 | Every request re-calls a sync webhook that just failed | failures not remembered, so every caller re-hits a dead dependency | retries-timeouts, caching | 3 | same function | [saleor #18079](https://github.com/saleor/saleor/pull/18079) |
| S11 | Zero-total checkout never becomes 'fully authorized' | derived status recomputed only on change; an initial state that already qualifies never transitions | state-machine | 4 | same function | [saleor #18019](https://github.com/saleor/saleor/pull/18019) |
| S12 | Price override ignored when computing checkout discount | override checked after a derived/cached value | money-invariants | 3 | other file | [saleor #17979](https://github.com/saleor/saleor/pull/17979) |
| S13 | Gift cards can push checkout net total below zero | subtracting a gross amount from both net and gross | money-invariants | 4 | same function | [saleor #17926](https://github.com/saleor/saleor/pull/17926) |
| S14 | Concurrent sign-ups with the same email crash | check-then-insert without handling the unique-constraint loser | race-condition, idempotency | 3 | same function | [saleor #17641](https://github.com/saleor/saleor/pull/17641) |
| S15 | Fully refunded order shows totalRefunded = 0 | filter on an 'active' flag that the terminal state clears | state-machine, money-invariants | 3 | same function | [saleor #17632](https://github.com/saleor/saleor/pull/17632) |
| S16 | Gift card balances wrong after a card covers the whole order | total re-derived by hand from parts instead of the canonical function | money-invariants | 3 | same file | [saleor #17566](https://github.com/saleor/saleor/pull/17566) |
| S18 | Reordering collection products gives the wrong order when sort_order is NULL | tie-breaker differs between the order shown and the order mutated | pagination | 4 | other file | [saleor #17276](https://github.com/saleor/saleor/pull/17276) |
| S19 | Search results skip or repeat items across pages | keyset cursor tie-break compares in the wrong direction | pagination | 4 | same function | [saleor #17222](https://github.com/saleor/saleor/pull/17222) |
| S21 | Shipping voucher discount applied twice in tax payload | discount applied at two layers | money-invariants | 3 | other file | [saleor #16814](https://github.com/saleor/saleor/pull/16814) |
| S22 | Manual line discount stacks with a voucher | business rule enforced in one of two parallel paths | money-invariants | 3 | other file | [saleor #16738](https://github.com/saleor/saleor/pull/16738) |
| S23 | Fully paying a draft order confirms it automatically | transition fired from a state that should not allow it | state-machine | 3 | same function | [saleor #16385](https://github.com/saleor/saleor/pull/16385) |
| S24 | Pending amounts missing after async payment action | record written but flag that makes it count left unset | money-invariants, state-machine | 3 | same function | [saleor #14544](https://github.com/saleor/saleor/pull/14544) |
| S25 | Order charge status stale after granting a refund | derived status not recomputed after one of its inputs changes | state-machine, money-invariants | 3 | other file | [saleor #14538](https://github.com/saleor/saleor/pull/14538) |
| S26 | Authentication plugin called many times per request | cache populated after the work, so concurrent callers all miss (stampede) | caching, idempotency | 4 | other file | [saleor #14323](https://github.com/saleor/saleor/pull/14323) |
| S27 | Checkout completion and payment webhook both create the order | lock acquired and released in its own transaction protects nothing | race-condition, idempotency | 5 | same function | [saleor #12657](https://github.com/saleor/saleor/pull/12657) |
| S30 | Overselling hidden: negative stock clipped to zero before summing | clamping each term before summing changes the sum | integer-arithmetic, money-invariants | 3 | same function | [saleor #10366](https://github.com/saleor/saleor/pull/10366) |
| S31 | Free (zero-total) orders show as fully refunded / not charged | zero amount makes an equality check vacuously true | state-machine, money-invariants | 3 | same function | [saleor #10147](https://github.com/saleor/saleor/pull/10147) |
| S32 | Paging products sorted by publication date skips items | sort key truncated (datetime to date) so cursor and order disagree | pagination | 4 | same function | [saleor #9741](https://github.com/saleor/saleor/pull/9741) |
| S33 | Customer charged but no order and no refund | error path after an external side effect does not compensate | money-invariants, state-machine | 3 | same function | [saleor #10952](https://github.com/saleor/saleor/pull/10952) |
| S34 | Confirmed orders recorded twice in the tax provider | record emitted twice because one builder serves two purposes | money-invariants | 3 | same file | [saleor #9027](https://github.com/saleor/saleor/pull/9027) |
| S35 | Each gift card is charged the full order total | ignored return value of a function that 'updates' an immutable value | money-invariants | 2 | same file | [saleor #13724](https://github.com/saleor/saleor/pull/13724) |
| S36 | Ending a preorder leaves stock allocations uncounted | denormalised counter not updated on one branch | money-invariants | 3 | same function | [saleor #9308](https://github.com/saleor/saleor/pull/9308) |
| S37 | Tax provider called twice when an order is created | handler subscribed to two events that both fire for one action | idempotency | 3 | other file | [saleor #11509](https://github.com/saleor/saleor/pull/11509) |
| K1 | End-of-month billing date drifts after a short month | calendar arithmetic: month addition not re-aligned to the anchor day | (none fits) | 4 | same function | [killbill #2136](https://github.com/killbill/killbill/pull/2136) |
| K2 | Usage invoice misses usage recorded late in the day for non-UTC accounts | local date converted to an instant in the wrong time zone | (none fits) | 4 | same function | [killbill da0969d93](https://github.com/killbill/killbill/commit/da0969d93f4d3c5c2c153663df756fa4ed16d65f) |
| K3 | Usage invoice items carry the wrong date for PST accounts | instant converted to a calendar date in the wrong time zone | (none fits) | 3 | same function | [killbill ea7914942](https://github.com/killbill/killbill/commit/ea791494267c6bbdeca833533a08b05d41d1026e) |
| K4 | Deleted blocking states still block accounts | soft-delete filter missing from one of several queries | state-machine | 3 | same file | [killbill 85a45b0ed](https://github.com/killbill/killbill/commit/85a45b0ed7ac17fdfd77332ef99e08bf6b50f045) |
| K5 | Payment-method overwrite guard inverted | inverted boolean guard (De Morgan slip) | input-validation | 2 | same function | [killbill 015a77523](https://github.com/killbill/killbill/commit/015a7752366dfe0a4f76f274e77d3770965b45ea) |
| K6 | Consecutive events for the same subscription not paired | reference equality on value objects | (none fits) | 3 | same function | [killbill 13e1dfb65](https://github.com/killbill/killbill/commit/13e1dfb65c92b8ca922afe71f11af1e7cff6f783) |
| K7 | Usage records silently dropped by a sorted set | comparator ties broken by hashCode subtraction | integer-arithmetic | 5 | same function | [killbill dd5f5157a](https://github.com/killbill/killbill/commit/dd5f5157a66aefc41f71c453a9366e8eb8e2adf7) |
| K8 | Catalog change with a non-recurring phase hangs the subscription service | loop step can be zero | resource-management, state-machine | 4 | other file | [killbill 560ccbb79](https://github.com/killbill/killbill/commit/560ccbb79250d8ba499755970cf24604756025fb) |
| K9 | Tier limits lose precision through double conversion | exact decimal routed through binary floating point | money-invariants | 3 | other file | [killbill d7526fb64](https://github.com/killbill/killbill/commit/d7526fb64f6b3c08426728063be4f1d46422a497) |
| H1 | Payments list shows another merchant's attempt | join key unique only per tenant, join not scoped by tenant | tenant-isolation | 4 | same function | [hyperswitch #6917](https://github.com/juspay/hyperswitch/pull/6917) |
| H2 | Duplicate refund_id silently returns the earlier refund | idempotency key replay without comparing request fingerprints | idempotency | 3 | same function | [hyperswitch #5282](https://github.com/juspay/hyperswitch/pull/5282) |
| H3 | Lock retries give up instantly | retry loop without backoff | retries-timeouts | 3 | same function | [hyperswitch #9308](https://github.com/juspay/hyperswitch/pull/9308) |
| H4 | Capture still processing reports nothing left to capture | non-terminal state grouped with terminal states | state-machine, money-invariants | 3 | other file | [hyperswitch #4229](https://github.com/juspay/hyperswitch/pull/4229) |
| H5 | Incremental authorization double-counts surcharge | derived total fed back as a base amount (double count) | money-invariants | 4 | other file | [hyperswitch #9073](https://github.com/juspay/hyperswitch/pull/9073) |
| H6 | Surcharge rules stay stale after update | cache invalidated under a different key than it is read with | caching | 3 | same function | [hyperswitch #6907](https://github.com/juspay/hyperswitch/pull/6907) |
| H7 | Queued events never consumed in multi-tenant mode | producer and consumer disagree on a derived key name | tenant-isolation | 4 | other service | [hyperswitch #4916](https://github.com/juspay/hyperswitch/pull/4916) |
| H8 | Partial payments misdetected by comparing the wrong amount field | amount compared across units/currencies (wrong field) | money-invariants | 4 | same file | [hyperswitch #5873](https://github.com/juspay/hyperswitch/pull/5873) |
| H9 | Invoice billing start time overwritten by each retry attempt | parent-level field overwritten by child events | state-machine | 3 | same function | [hyperswitch #13982](https://github.com/juspay/hyperswitch/pull/13982) |
| H10 | A failed void blocks refunds forever | presence of a record treated as success | state-machine | 3 | other file | [hyperswitch #13853](https://github.com/juspay/hyperswitch/pull/13853) |
| H13 | Connector account changes not visible after update (v2) | cache invalidated under a different key than it is read with | caching | 3 | other file | [hyperswitch #5918](https://github.com/juspay/hyperswitch/pull/5918) |
| H14 | Saved card marked inactive by a later failed payment | status overwritten by a later, lower-priority event | state-machine | 2 | same function | [hyperswitch #4149](https://github.com/juspay/hyperswitch/pull/4149) |
| O1 | Concurrent order placements deadlock on stock rows | inconsistent lock ordering across transactions | race-condition | 4 | same function | [django-oscar #4594](https://github.com/django-oscar/django-oscar/pull/4594) |
| O2 | Thank-you page shows superusers someone else's latest order | empty filter matches everything | tenant-isolation | 3 | same function | [django-oscar #4501](https://github.com/django-oscar/django-oscar/pull/4501) |
| O3 | Tax totals off by a cent with discounts | rounding at the wrong step | money-invariants | 3 | same file | [django-oscar #4448](https://github.com/django-oscar/django-oscar/pull/4448) |
| O4 | Voucher list shows inflated offer counts | COUNT over a fanned-out join | (none fits) | 2 | same function | [django-oscar #4107](https://github.com/django-oscar/django-oscar/pull/4107) |
| O5 | Discount applied to a variant marked non-discountable | inherited setting overrides the child's own setting | money-invariants | 3 | other file | [django-oscar #4102](https://github.com/django-oscar/django-oscar/pull/4102) |
| O6 | Removed offer combination still applies | symmetric relation updated on one side | (none fits) | 2 | same function | [django-oscar #4017](https://github.com/django-oscar/django-oscar/pull/4017) |

Distance: {'other file': 17, 'same function': 35, 'same file': 6, 'other service': 1}. Regression test added by the fix: 41 of 59 (Hyperswitch fixes almost never add one). Skills used: money-invariants 22, state-machine 14, idempotency 6, race-condition 5, pagination 5, caching 4, tenant-isolation 3, retries-timeouts 2, integer-arithmetic 2, backward-compat 1, input-validation 1, resource-management 1; 7 bugs fit no taxonomy skill.

## Clusters (bugs that share one root-cause sentence)

- **money-calculation-order** (7: S12, S13, S16, S30, K9, H8, O3; repos: django-oscar, hyperswitch, killbill, saleor). An amount is computed in the wrong order or from the wrong inputs (precedence, rounding step, clamping, unit/currency, float). *Crosses repos: strongest evidence it is a general pattern.*
- **state-transition-guard** (5: S8, S15, S23, H4, H10; repos: hyperswitch, saleor). An action or event is allowed from a state that should not permit it, or a state is mis-grouped with terminal states. *Crosses repos: strongest evidence it is a general pattern.*
- **double-apply** (5: S21, S22, S34, S37, H5; repos: hyperswitch, saleor). The same adjustment (discount, surcharge, record, side effect) is applied by two layers or two handlers. *Crosses repos: strongest evidence it is a general pattern.*
- **derived-state-not-recomputed** (4: S11, S24, S25, S36; repos: saleor). A stored status/counter depends on inputs that change, but one write path does not recompute it.
- **cache-stampede-key** (4: S26, H6, H7, H13; repos: hyperswitch, saleor). Reader and writer (or invalidator) of a cache/queue disagree on the key, or fill it too late. *Crosses repos: strongest evidence it is a general pattern.*
- **time-calendar** (4: K1, K2, K3, K8; repos: killbill). A calendar computation uses the wrong time zone or the wrong anchor when stepping periods.
- **concurrency-check-then-act** (3: S1, S14, S27; repos: saleor). A decision is made from data read outside the lock/transaction that the action relies on.
- **aggregation-join-fanout** (3: S2, S4, O4; repos: django-oscar, saleor). A join multiplies rows, and a COUNT/SUM/DISTINCT on top gives the wrong number. *Crosses repos: strongest evidence it is a general pattern.*
- **pagination-cursor** (3: S6, S19, S32; repos: saleor). The cursor's comparison does not match the sort order exactly (direction, truncation, two implementations).
- **stale-read-wrong-variable** (3: S7, S35, O5; repos: django-oscar, saleor). The code reads a stale or near-identically named value instead of the fresh one. *Crosses repos: strongest evidence it is a general pattern.*
- **missing-scope-filter** (3: K4, H1, O2; repos: django-oscar, hyperswitch, killbill). A query that must be scoped (tenant, owner, not-deleted) is missing the filter on one path. *Crosses repos: strongest evidence it is a general pattern.*
- **write-scope-clobber** (2: S3, O6; repos: django-oscar, saleor). A write meant for one record replaces or misses related records. *Crosses repos: strongest evidence it is a general pattern.*
- **lock-ordering-deadlock** (2: S5, O1; repos: django-oscar, saleor). Two code paths take the same locks in different orders. *Crosses repos: strongest evidence it is a general pattern.*
- **retry-amplification** (2: S9, H3; repos: hyperswitch, saleor). Retries happen with no delay or no memory of recent failure. *Crosses repos: strongest evidence it is a general pattern.*
- **identity-vs-equality** (2: K6, K7; repos: killbill). Objects are compared by identity or hash instead of value.
- **later-event-overwrites** (2: H9, H14; repos: hyperswitch). A later, less authoritative event overwrites a value that should be kept.
- **ordering-tiebreak** (1: S18; repos: saleor). Rows with NULL sort_order are tie-broken by the join row id instead of the product order used for display.
- **zero-amount-edge** (1: S31; repos: saleor). Equality 'refunded == total' is vacuously true at 0, and 'no payment' is mapped to NOT_CHARGED even when nothing is owed.
- **external-side-effect-compensation** (1: S33; repos: saleor). A validation error raised after the external charge has no compensating refund/void on that path.
- **inverted-condition** (1: K5; repos: killbill). A refactor turned 'not allowed AND already set' into 'allowed OR already set'.
- **idempotency-key-semantics** (1: H2; repos: hyperswitch). A unique-violation is treated as an idempotent replay without checking that the request matches the stored one.

Known patterns from outside these repos: check-then-act and lock ordering are textbook concurrency bugs and match the Jepsen lost-update findings; cache key mismatch matches the GitHub/OpenAI cache incidents in danluu/post-mortems; the time-zone cluster matches ReadCode's own 008 (DST) problem; S27/S33 match Brandur's 'foreign state mutation' failure modes.

## Rejected candidates (read, then dropped)

- saleor `7b108c395` Do not allow payment if checkout has a transaction: validation/breaking change; no user-visible symptom stated.
- saleor `4acaaf075` Do not update EventAttempt for success delivery: performance-only (extra writes).
- saleor `709f3971e` VoucherCode.used negative: symptom patch: clamps and logs; root cause unknown per code comment.
- saleor `49c7fbe5c` Gift card decimal places in notification: presentation/formatting; trivial.
- saleor `1d62e6a45` Cache for shipping methods: mostly a TTL/config change.
- saleor `41ef02c57` Avatax JPY shipping: mechanism not fully understood from the diff; left out rather than guessed.
- saleor `b05633dae` External shipping methods with different currency: moves validation; symptom is an error message, borderline.
- saleor `11714/14380/5268` already used by examples 004-006: duplicate of existing ReadCode examples.
- killbill `38ad2b022` Wrong header information in pagination APIs: fix is indexes + DDL (performance/migration), >30 lines.
- killbill `many` spotbugs / UTF-8 / build fixes (2023-05): static-analysis or build fixes, no symptom.
- hyperswitch `b42052269` multitenancy prefix in routing cache: diff truncated across >3 files; not fully read.
- hyperswitch `07dc52559` Adyen manual capture partially captured: connector-specific field mapping.
- hyperswitch `most connector fixes` status/deserialization mapping per PSP: provider-specific mapping, not a reusable mechanism.
- django-oscar `0dfeaa797` Voucher set usage sorting: sort fields missing; minor.
- django-oscar `5bb9df347` AbsoluteDiscountBenefit: fix reverted; ends as a description change.
- Plus ~1,500 fix-like commits not opened: dropped by subject (dependency, docs, CI, typo, connector-specific field mapping) or size; not individually recorded.

## The three I would turn into exercises first

1. **S19 search cursor tie-break reversed** (pagination, elus. 4). One swapped `gt`/`lt` inside half of an OR; the symptom (an empty or repeated page) is confirmed on the PR page; rebuilds in ~40 lines with SQLite and a deterministic test (equal ranks across a page boundary). Teaches keyset pagination, which no ReadCode problem covers yet.
2. **S27 lock released before the work** (race + idempotency, elus. 5). The buggy code *has* a `SELECT ... FOR UPDATE` and a comment claiming exclusivity, so it looks safe; it is the payments-shaped version of the most common concurrency mistake. Needs a two-request interleaving in the playground (the 003 fault-injection pattern already exists).
3. **H1 join not scoped by tenant** (tenant isolation, elus. 4). Cross-merchant data from a join whose key is only unique per merchant; high cost, a one-line fix, and a realistic 'two accounts' reproduction. Complements 005 (token read) with a different mechanism.

Runners-up: S2 (SUM DISTINCT on equal values, very distillable), K2/K3 (time zone at end of day; overlaps 008), S35 (ignored return value with several gift cards; good rung-1 warm-up).

## Caveats

- Symptoms are mostly paraphrased from PR titles and commit messages; only S19, S27 and H1 were checked against their PR pages. Linked issue threads were not read (no API budget spent).
- No bug was searched on the web for fame; none has a CVE that I know of.
- `ranges` are pre-fix line ranges of the changed hunks; a pure insertion is recorded as the single line before which it was inserted.
- Hyperswitch is Rust with heavy generics; its distilled versions would be re-written in Python, as the prompt allows.
- Kill Bill commits are not squash merges, so `merge_commit` is the fix commit itself.
