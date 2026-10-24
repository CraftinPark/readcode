import re, sys, json, collections
src = open(sys.argv[1], encoding="utf-8").read().splitlines()
section, entries = None, []
for line in src:
    if line.startswith("## "):
        section = line[3:].strip()
    elif line.startswith("[") and section not in ("Other lists of postmortems", "Analysis", "Contributors", "Table of Contents"):
        m = re.match(r"\[([^\]]+)\]\(([^)]+)\)\.?\s*(.*)", line)
        if m:
            entries.append({"section": section, "org": m.group(1), "url": m.group(2), "text": m.group(3)})
# keyword classes (an entry may hit several); applied to the summary text only
K = {
 "config_change": r"config(?:uration)?\b|misconfigur|feature flag|\bflag\b",
 "deploy_upgrade_rollout": r"deploy|rollout|roll(?:ed)? out|upgrad|release|push(?:ed)? to",
 "overload_capacity": r"overload|capacity|load spike|traffic spike|surge|exhaust|saturat|thundering herd|too many",
 "retries_amplification": r"retr(?:y|ies|ied)|reconnect|backoff",
 "timeouts": r"time ?outs?|timed out",
 "cascading_dependency": r"cascad|dependen|downstream|upstream",
 "database_schema_migration": r"migrat|schema|column|index|alter table",
 "integer_overflow_limits": r"overflow|integer|int32|int64|max(?:imum)? (?:value|int)|wraparound|limit was reached|hit the limit",
 "time_clock": r"leap|clock|time ?zone|daylight|date |expir",
 "cache": r"cach",
 "queue_backlog": r"queue|backlog|kafka|rabbitmq",
 "race_concurrency": r"race|concurren|lock|deadlock",
 "failover_recovery": r"failover|fail over|fell back|fallback|recovery|replica|promot",
 "data_loss_corruption": r"data loss|lost data|corrupt|deleted|inconsisten|wrong owner|leak",
 "dns_cert_network": r"\bdns\b|certificat|bgp|route|network",
 "duplicate_side_effects": r"duplicat|twice|multiple times|more than once|double",
 "billing_money": r"billing|charg|payment|refund|invoice|money|\$\d",
 "error_handling": r"exception|error handling|unhandled|crash|panic|null",
 "monitoring_gap": r"alert|monitor|detect",
}
K = {k: re.compile(v, re.I) for k, v in K.items()}
c = collections.Counter()
ex = collections.defaultdict(list)
for e in entries:
    for k, rx in K.items():
        if rx.search(e["text"]):
            c[k] += 1
            ex[k].append(f'{e["org"]}: {e["url"]}')
sec = collections.Counter(e["section"] for e in entries)
out = {"entries": len(entries), "by_section": dict(sec), "keyword_class_counts": dict(c.most_common()),
       "regexes": {k: v.pattern for k, v in K.items()}, "examples": {k: v[:8] for k, v in ex.items()}}
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
print(len(entries), dict(sec))
for k, v in c.most_common():
    print(f"{k:28s}{v:4d} {100*v/len(entries):5.1f}%")
