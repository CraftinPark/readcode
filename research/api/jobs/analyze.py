import json, re, sys, html, csv, hashlib, collections
RAW, OUTDIR = sys.argv[1], sys.argv[2]
raw = json.load(open(RAW, encoding="utf-8"))

# slugs whose board turned out to be a different (non-target) org or a near-empty board; dropped
DROP = set()

def text(s):
    s = html.unescape(html.unescape(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s)

ENG = re.compile(r"\b(engineer|engineering|developer|sre|swe|architect|programmer)\b", re.I)
EXCL = re.compile(r"\b(sales|solutions?|support|customer|field|hardware|mechanical|electrical|manufacturing|"
                  r"recruit|designer|design engineer|analog|rf|firmware|embedded|asic|fpga|silicon|thermal|"
                  r"process engineer|quality engineer|test technician|forward deployed|deployment strategist|"
                  r"product manager|program manager|technical account|implementation|partner|pre-?sales|"
                  r"value engineer|mechatronics|optical|network engineer|it engineer|desktop|"
                  r"research scientist|research engineer|machine learning|\bml\b|\bai\b engineer|data scientist|"
                  r"computer vision|perception|robotics|frontend|front-end|front end|ios|android|mobile|"
                  r"web engineer|ui engineer|ux)\b", re.I)
BACKEND = re.compile(r"\b(backend|back-end|back end|api|payments?|platform|infrastructure|infra|reliability|sre|"
                     r"distributed|server|core|ledger|billing|money|banking|card|treasury|risk|fraud|storage|database|"
                     r"systems?|full[- ]?stack|fullstack|software engineer|software developer|swe|devops|"
                     r"production engineer|integrations?|developer experience|cloud)\b", re.I)

THEMES = {
 "idempotency": r"idempoten\w*|exactly[- ]once|at[- ]least[- ]once|de-?duplicat\w*|double[- ]charg\w*",
 "retries_timeouts": r"\bretr(?:y|ies|ying)\b|timeouts?\b|backoff|circuit[- ]breaker\w*",
 "webhooks": r"webhooks?",
 "consistency_transactions": r"(?:data|strong|eventual|transactional|read|write) consistency|consistency (?:guarantees|models?)|\bacid\b|transactional|isolation level|serializab\w*|two[- ]phase commit|\bsagas?\b|eventual consistency|strong consistency",
 "migrations": r"\bmigrations?\b|schema change\w*|backfill\w*|zero[- ]downtime",
 "multi_tenancy": r"multi[- ]?tenan\w*|tenant isolation|\btenants?\b",
 "rate_limiting_overload": r"rate[- ]limit\w*|throttl\w*|load[- ]shedding|backpressure|overload\w*",
 "observability": r"observab\w*|monitoring|\bmetrics\b|\btracing\b|\blogging\b|alerting|\bslos?\b|\bslis?\b|opentelemetry|prometheus|grafana|datadog",
 "on_call": r"on[- ]call|pager",
 "incident_response": r"incidents?\b|post-?mortems?|outages?|root[- ]cause|\brca\b",
 "debugging_troubleshooting": r"debug\w*|troubleshoot\w*",
 "data_correctness": r"data (?:integrity|correctness|quality|accuracy)|correctness|reconcil\w*|accura(?:te|cy) (?:of )?(?:data|records|books)",
 "money_ledger": r"ledgers?|double[- ]entry|accounting|money movement|settlement\w*|payouts?|reconciliation",
 "api_design_versioning": r"api design|api versioning|versioning|backward[s]?[- ]compatib\w*|breaking changes?|public apis?|rest(?:ful)? apis?|graphql|grpc|api contracts?",
 "queues_async": r"\bqueues?\b|kafka|rabbitmq|\bsqs\b|pub/?sub|asynchronous|\basync\b|event[- ]driven|message (?:bus|broker)|stream processing|background jobs?",
 "caching": r"\bcach(?:e|es|ing)\b|redis|memcache\w*|\bcdn\b",
 "concurrency": r"concurren\w*|race conditions?|locking|deadlocks?|multi[- ]thread\w*|mutex\w*",
 "distributed_systems": r"distributed systems?",
 "scalability_perf": r"scalab\w*|high[- ]throughput|low[- ]latency",
 "availability_fault_tolerance": r"high(?:ly)? availab\w*|fault[- ]toleran\w*|resilien\w*|failover|disaster recovery|redundan\w*|uptime",
 "security_authz": r"authori[sz]ation|authenticat\w*|access control|permissions?|\boauth\b|\biam\b|least privilege",
 "pci_kyc_compliance": r"\bpci\b|\bsox\b|\bkyc\b|\baml\b|regulatory (?:compliance|requirements|reporting)|financial regulat\w*",
 "testing": r"unit tests?|integration tests?|test coverage|automated testing|\btesting\b",
 "code_review": r"code reviews?|reviewing code|design reviews?",
 "pagination": r"paginat\w*",
 "state_machines_workflows": r"state machines?|state transitions?|workflow (?:engine|orchestration)|durable execution|lifecycle of (?:a |an )?(?:payment|order|transaction)s?",
 "time_timezones": r"time ?zones?|daylight saving|clock skew",
 "sql_databases": r"\bsql\b|postgres\w*|mysql|dynamodb|cassandra|spanner|cockroach\w*|aurora",
}
THEMES = {k: re.compile(v, re.I) for k, v in THEMES.items()}

rows, seen = [], set()
companies_all = collections.Counter()
for key, b in raw.items():
    if key in DROP:
        continue
    companies_all[b["slug"]] += len(b["jobs"])
    for j in b["jobs"]:
        t = j.get("title") or ""
        if not ENG.search(t) or EXCL.search(t) or not BACKEND.search(t):
            continue
        body = text(j.get("content"))
        h = hashlib.md5((b["slug"] + t + body[:2000]).encode()).hexdigest()
        if h in seen:   # same posting duplicated across locations
            continue
        seen.add(h)
        hits = {k: len(rx.findall(body)) for k, rx in THEMES.items()}
        rows.append({"company": b["slug"], "board": b["board"], "category": b["category"], "title": t,
                     "location": j.get("location"), "url": j.get("url"), "updated": j.get("updated"),
                     "chars": len(body), "themes": [k for k, v in hits.items() if v]})

n = len(rows)
comp = collections.Counter(r["company"] for r in rows)
theme_posts = collections.Counter(t for r in rows for t in r["themes"])
theme_comp = {k: len({r["company"] for r in rows if k in r["themes"]}) for k in THEMES}
by_cat = collections.defaultdict(collections.Counter)
cat_n = collections.Counter(r["category"] for r in rows)
for r in rows:
    for t in r["themes"]:
        by_cat[r["category"]][t] += 1
pay = [r for r in rows if re.search(r"payment|ledger|billing|money|card|treasury|banking|financial|risk|fraud", r["title"], re.I)]
pay_c = collections.Counter(t for r in pay for t in r["themes"])

summary = {
 "boards_with_jobs": len(raw), "companies_with_jobs": len(companies_all), "postings_total": sum(companies_all.values()),
 "engineering_backend_postings_deduped": n, "companies_with_matching_roles": len(comp),
 "theme_postings": {k: theme_posts[k] for k in sorted(THEMES, key=lambda k: -theme_posts[k])},
 "theme_share_pct": {k: round(100 * theme_posts[k] / n, 1) for k in sorted(THEMES, key=lambda k: -theme_posts[k])},
 "theme_companies": {k: theme_comp[k] for k in sorted(THEMES, key=lambda k: -theme_comp[k])},
 "by_category_share_pct": {c: {k: round(100 * by_cat[c][k] / cat_n[c], 1) for k in THEMES} for c in cat_n},
 "category_postings": dict(cat_n),
 "payments_titled_postings": len(pay),
 "payments_titled_share_pct": {k: round(100 * pay_c[k] / max(1, len(pay)), 1) for k in sorted(THEMES, key=lambda k: -pay_c[k])},
 "postings_per_company": dict(comp.most_common()),
 "regexes": {k: v.pattern for k, v in THEMES.items()},
}
json.dump(summary, open(f"{OUTDIR}/job-theme-counts.json", "w", encoding="utf-8"), indent=1)
with open(f"{OUTDIR}/job-roles.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["company", "board", "category", "title", "location", "url", "updated", "themes"])
    for r in rows:
        w.writerow([r["company"], r["board"], r["category"], r["title"], r["location"], r["url"], r["updated"], ";".join(r["themes"])])
print(json.dumps({k: summary[k] for k in ["companies_with_jobs", "postings_total", "engineering_backend_postings_deduped", "companies_with_matching_roles", "category_postings", "payments_titled_postings"]}))
for k in summary["theme_share_pct"]:
    print(f"{k:28s} {theme_posts[k]:5d} {summary['theme_share_pct'][k]:5.1f}%  cos={theme_comp[k]:3d}  pay={summary['payments_titled_share_pct'].get(k)}")
