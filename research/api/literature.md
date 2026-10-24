# Expert playbooks and failure literature

Each entry: what it is, whether I checked the citation (✔ = title/venue/year confirmed from the paper PDF or the publisher page this session), and the failure classes it describes. Numbers are quoted from the source text I read; anything else is marked.

## Empirical studies (counted failures)

### Yuan et al., "Simple Testing Can Prevent Most Critical Failures: An Analysis of Production Failures in Distributed Data-Intensive Systems", OSDI 2014 ✔
[PDF](https://www.eecg.utoronto.ca/~stumm/Papers/Yuan-OSDI-14.pdf) · Cassandra, HBase, HDFS, Hadoop MapReduce, Redis.
- 198 user-reported failures, 48 catastrophic. **92% of catastrophic failures come from incorrect handling of non-fatal errors that the software explicitly signalled.**
- 58% of catastrophic failures could have been caught by simple tests of the error-handling code; **35% fall into three trivial patterns**: the handler is empty or only logs, the handler aborts on an overly general exception, or the handler contains TODO/FIXME.
- 74% of failures are deterministic; 77% can be reproduced by a unit test; most need ≤3 nodes; 76% print explicit failure messages. Top input events: starting a service 58%, a client write 32%, an unreachable node 24%, a config change 23%.
- Classes: **error-handling / partial failure**, config change, node loss.

### Gunawi et al., "What Bugs Live in the Cloud? A Study of 3000+ Issues in Cloud Systems", SoCC 2014 ✔
[PDF](https://ucare.cs.uchicago.edu/pdf/socc14-cbs.pdf) · 21,399 issues (2011-2014) from Hadoop MapReduce, HDFS, HBase, Cassandra, ZooKeeper, Flume; 3,655 "vital" issues classified (CBSDB).
- Aspects: reliability 45%, performance 22%, availability 16%, data consistency 5%, scalability 2%, topology 1%.
- Software bug types: **logic 29%, error handling 18%, optimization 15%, configuration 14%, data race 12%**, hang 4%, space 4%, load 4%. Hardware faults 13% of issues.
- Data-consistency bugs come mainly from logic bugs in operational protocols (43%), data races (29%) and failure handling (10%). Distributed data races are over half of data races; they often co-occur with failures.
- Load issues: the paper argues systems should know their limits and reject requests when overloaded.
- Classes: logic, **error handling**, config, **race**, overload.

### Gunawi et al., "Why Does the Cloud Stop Computing? Lessons from Hundreds of Service Outages", SoCC 2016 ✔
[PDF](https://ucare.cs.uchicago.edu/pdf/socc16-cos.pdf) · 1,247 news/post-mortem reports, 597 unplanned outages, 32 services, 2009-2015. (The task brief's "Gunawi outage study" is this paper; it is 2016, not 2014.)
- Root causes among known causes: **UPGRADE 16%, NETWORK 15%, BUGS 15%, CONFIG 10%, LOAD 9%, CROSS (other service) 8%**, POWER 6%, SECURITY 5%, HUMAN 4%, STORAGE 4%, SERVER 3%, natural disaster 3%, hardware 1%. 355 outages had an unknown cause.
- "Failover that fails": redundancy only helps if detection, failover code and backups all work; they record buggy failover and a **failover cold-cache** load spike.
- More than half of human errors relate to upgrades and configuration.
- Classes: **deploy/upgrade, config**, overload, dependency failure, failed failover.

### Leesatapornwongsa, Lukman, Lu, Gunawi, "TaxDC: A Taxonomy of Non-Deterministic Concurrency Bugs in Datacenter Distributed Systems", ASPLOS 2016 ✔
[PDF](https://ucare.cs.uchicago.edu/pdf/asplos16-TaxDC.pdf) · 104 distributed-concurrency bugs from Cassandra, Hadoop MapReduce, HBase, ZooKeeper.
- Triggering timing: **order violation 44%, atomicity violation 20%, fault/reboot timing 32%**, mixed 4%. Untimely messages cause 64%; two-thirds of those are order violations.
- 63% need a hardware fault (crash, reboot, timeout); >60% are triggered by a single untimely event; most involve 1-3 messages, nodes and protocols.
- **47% fail silently** (no explicit error); 53% produce explicit errors. Fixes: 30% prevent the bad timing, 40% delay or ignore the untimely message.
- Classes: **message/event ordering**, crash-recovery races, silent state corruption.

### Dan Luu, `danluu/post-mortems` (GitHub list, read 2026-10-24) ✔
[README](https://github.com/danluu/post-mortems). Counted by script (`literature/postmortems.py`, results in `literature/danluu-postmortems-counts.json`): **240 incident entries**; sections: Config Errors 59, Hardware/Power 15, Conflicts 11, Time 5, Database 12, Uncategorized 138.
- Keyword classes over entry text (one entry can hit several): DNS/cert/network 48 (20%), deploy/upgrade 45 (19%), config 40 (17%), cascading/dependency 35 (15%), overload/capacity 33 (14%), data loss/corruption 30 (13%), failover/recovery 28 (12%), race/locking 28 (12%), schema/migration 17 (7%), error handling 16, monitoring gap 15, queue backlog 13, retries 12, cache 11, time/clock 11, integer limits 10, timeouts 9, billing/money 5, duplicate side effects 3.
- Examples that match API/payments work: **Twilio (2013) billing Redis partition → retries charged customers multiple times**; Google Gmail cron non-atomic batch sent mail >20 times; CircleCI (2021) column type change broke the job distributor on mixed old/new rows; GitHub (2021) INT32 foreign key overflow; Basecamp and Strava integer-limit outages; Mandrill and Sentry Postgres transaction-ID wraparound; Spotify missing exponential backoff → cascading failure; Discord/Slack reconnect storms; OpenAI Redis cache bug exposing other users' data; GitHub failover that routed 16 private repos to the wrong owners; Knight Capital reused flag ($460M).
- Note: incident write-ups are about *large* outages at infra companies; small money bugs rarely get public post-mortems, so billing/money is under-represented here by construction.

## Playbooks and essays

### Google, *Site Reliability Engineering* (O'Reilly 2016) ✔ (chapter pages on sre.google)
- **Ch. 22 "Addressing Cascading Failures"** (Mike Ulrich): overload of remaining servers after capacity loss; resource exhaustion (CPU, memory → smaller caches → more backend load, threads, file descriptors); crash loops; **retry amplification** across layers; work done for requests that already timed out; slow startup and **cold caches**; triggers: process death, updates, organic growth, drains. Defences: load shedding, graceful degradation, short queues, retry budgets with jittered backoff, retry at one layer only, don't retry permanent errors, **propagate deadlines and cancellation**, fail fast, avoid request cycles, separate liveness from health.
- **Ch. 21 "Handling Overload"** (Alejandro Forero Cuervo): per-customer quotas; client-side adaptive throttling (reject locally once requests exceed K × accepts, K=2); criticality levels propagated downstream; **at most 3 attempts per request and a 10% per-client retry budget** (limits growth to ~1.1× instead of ~3×); retry only at the layer above the rejecting one.

### Richard I. Cook, "How Complex Systems Fail" (1998-2000) ✔ ([how.complexsystems.fail](https://how.complexsystems.fail/))
18 points. Most useful for ReadCode: catastrophe needs **multiple** failures; systems always contain latent flaws and run degraded; **root cause is a misleading idea** (several contributors); hindsight bias; change introduces new forms of failure. Implication: an "incident ticket" problem can legitimately have two contributing defects, and grading should accept contributing causes.

### Brandur Leach (Stripe), "Designing robust and predictable APIs with idempotency", Stripe blog, 2017-02-22 ✔
[stripe.com/blog/idempotency](https://stripe.com/blog/idempotency). Three network failure cases: connection never made (safe to retry), failure mid-operation (state in limbo), **success with lost response** (client cannot tell). Idempotency keys for the second and third; exponential backoff with jitter against thundering herds.

### Brandur Leach, "Implementing Stripe-like Idempotency Keys in Postgres", 2017-10-27 ✔
[brandur.org/idempotency-keys](https://brandur.org/idempotency-keys). Failure modes: client retry after timeout, server crash mid-request, failures calling **foreign** systems (charges, emails) that a local rollback cannot undo, concurrent duplicate requests, bad deploys. Tools: **atomic phases** (local writes committed between foreign calls), **recovery points** stored on the key, unique constraints / row locks / serializable transactions, a **completer** that finishes abandoned requests and a **reaper** that removes old keys.

### Jepsen analyses ✔ ([jepsen.io/analyses](https://jepsen.io/analyses), 51 analyses of 39 systems as of today)
Most relevant to application code (not database authors):
- **MySQL 8.0.34** (Alvaro & Kingsbury, 2023-12-19): default **Repeatable Read allows lost updates**, write skew (G2-item) and read skew, even on one healthy node; reads within a transaction are not repeatable. Advice: don't rely on RR for read-modify-write; use `SELECT ... FOR UPDATE` or Serializable; ORM load-modify-save under RR can lose committed updates silently. RDS multi-AZ "Serializable" also showed anomalies with default commit-order settings.
- **Amazon RDS for PostgreSQL 17.4** (2025-04-29, updated 2025-05-03): multi-AZ clusters violate Snapshot Isolation (Long Fork) every few minutes with no faults, versions 13.15-17.4; attributed to primary vs replica visibility order.
- PostgreSQL 12.3 (2020) is listed; I did not read it this session (unverified: its finding, recalled as a serializable-isolation bug).
- Class: **isolation-level anomalies / lost update** in read-modify-write code.

## Failure classes across the literature (used by the field guide)

| Class | Yuan | CBS | COS | TaxDC | danluu | SRE book | Cook | Brandur/Stripe | Jepsen |
|---|---|---|---|---|---|---|---|---|---|
| Error handling / partial failure of a dependency | ●● | ●● | ● | | ● | ● | | ●● | |
| Retries, timeouts, overload amplification | ● | ● | ● | ● | ●● | ●● | | ● | |
| Concurrency: race, lost update, ordering | | ● | | ●● | ● | | | ● | ●● |
| Idempotency / duplicate side effects | | | | | ● | | | ●● | |
| Config / deploy / upgrade change | ● | ● | ●● | | ●● | ● | ● | ● | |
| Schema migration / integer limits | | | | | ● | | | | |
| Caching (cold cache, stale, stampede) | | | ● | | ● | ● | | | |
| Failover / recovery code | | ● | ●● | ● | ● | ● | | ● | ● |
| Time / clocks | | | | | ● | | | | |
| Tenant / data exposure | | | | | ● | | | | |
| Silent data corruption | | ● | | ●● | ● | | | | ● |
| Money / billing logic | | | | | ● (few) | | | ● | |

●● = central finding with numbers; ● = described.
