"""List small fix commits from a local clone: <=30 non-test lines in <=3 non-test files."""
import subprocess, sys, re, json
repo, since, out = sys.argv[1], sys.argv[2], sys.argv[3]
TEST = re.compile(r"(^|/)(tests?|__tests__|spec|testdata|fixtures|cypress|integration-tests|postman)(/|$)|_test\.|test_|\.snap$|CHANGELOG|\.md$|\.lock$|\.json$|\.ya?ml$|\.graphql$|schema\.|migrations?/|\.po$|\.txt$|openapi|\.sql$", re.I)
FIX = re.compile(r"\b(fix(e[sd])?|bug|wrong|incorrect|prevent|missing|not (being )?)", re.I)
SKIP = re.compile(r"\b(typo|docs?|lint|clippy|ci\b|bump|deps?|dependenc|flaky|test(s)?:|chore|refactor|revert|readme|format|fmt|warning|deprecat|upgrade|cypress|e2e)\b", re.I)
log = subprocess.run(["git", "-C", repo, "log", "--no-merges", f"--since={since}", "--format=@@%H\t%ad\t%s", "--date=short", "--numstat"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
rows, cur = [], None
for line in log.splitlines():
    if line.startswith("@@"):
        if cur: rows.append(cur)
        h, d, s = line[2:].split("\t", 2)
        cur = {"sha": h, "date": d, "subject": s, "files": [], "test_files": []}
    elif line.strip() and cur:
        a, b, p = line.split("\t", 2)
        n = (int(a) if a.isdigit() else 0) + (int(b) if b.isdigit() else 0)
        (cur["test_files"] if TEST.search(p) else cur["files"]).append((p, n))
if cur: rows.append(cur)
keep = []
for r in rows:
    if not FIX.search(r["subject"]) or SKIP.search(r["subject"]):
        continue
    lines = sum(n for _, n in r["files"])
    if not r["files"] or len(r["files"]) > 3 or lines > 30:
        continue
    m = re.search(r"\(#(\d+)\)\s*$", r["subject"]) or re.search(r"#(\d+)", r["subject"])
    r.update(lines=lines, pr=int(m.group(1)) if m else None, has_test=bool(r["test_files"]))
    keep.append(r)
json.dump(keep, open(out, "w", encoding="utf-8"), indent=0)
print(repo, "commits", len(rows), "kept", len(keep), "with tests", sum(r["has_test"] for r in keep))
