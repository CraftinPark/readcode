"""Build bugs.jsonl from cards_spec.py: exact buggy/fixed text, ranges, commits and tests come from git."""
import subprocess, sys, re, json, os
sys.path.insert(0, os.path.dirname(__file__))
from cards_spec import CARDS
REPOS, OUT = sys.argv[1], sys.argv[2]
META = {"saleor": ("saleor/saleor", "BSD-3-Clause"), "killbill": ("killbill/killbill", "Apache-2.0"),
        "hyperswitch": ("juspay/hyperswitch", "Apache-2.0"), "django-oscar": ("django-oscar/django-oscar", "BSD-3-Clause")}
TEST = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|_test\.|test_|Test[A-Z]\w*\.java$", re.I)

def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout

def hunks(repo, sha, path):
    d = git(repo, "show", "--format=", "-U0", sha, "--", path).splitlines()
    out, cur = [], None
    for l in d:
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", l)
        if m:
            cur = {"old": int(m.group(1)), "n": int(m.group(2) or 1), "minus": [], "plus": []}
            out.append(cur)
        elif cur is not None and l.startswith("-") and not l.startswith("---"):
            cur["minus"].append(l[1:])
        elif cur is not None and l.startswith("+") and not l.startswith("+++"):
            cur["plus"].append(l[1:])
    return out

cards = []
for c in CARDS:
    repo = os.path.join(REPOS, c["repo"])
    full = git(repo, "rev-parse", c["sha"]).strip()
    parent = git(repo, "rev-parse", full + "^").strip()
    subject, body = git(repo, "show", "-s", "--format=%s%x00%b", full).split("\x00", 1)
    prs = re.findall(r"\(#(\d+)\)", subject)
    issue = re.search(r"(?:See|Fixes|Closes|[Ff]ix for|issue|[Ff]ixes:?)\s+#?(\d{3,5})", subject + " " + body)
    files, buggy, fixed = [], [], []
    for p in c["files"]:
        hs = [h for h in hunks(repo, full, p) if not c.get("match") or c["match"] in "\n".join(h["minus"] + h["plus"])]
        if not hs:
            raise SystemExit(f"{c['id']}: no hunk in {p} matching {c.get('match')!r}")
        files.append({"path": p, "ranges": [[h["old"], h["old"] + max(h["n"], 1) - 1] for h in hs]})
        for h in hs:
            buggy.append("\n".join(h["minus"]))
            fixed.append("\n".join(h["plus"]))
    changed = [f for f in git(repo, "show", "--format=", "--name-only", full).splitlines() if f]
    tests = [f for f in changed if TEST.search(f)]
    tdiff = git(repo, "show", "--format=", full, "--", *tests) if tests else ""
    names = re.findall(r"^\+\s*(?:async )?def (test\w+)", tdiff, re.M) + re.findall(r"^\+\s*public void (test\w+)", tdiff, re.M)
    regression = f"{tests[0]}::{names[0]}" if tests and names else (tests[0] if tests else None)
    name, lic = META[c["repo"]]
    pr = int(prs[-1]) if prs else None
    iss = int(issue.group(1)) if issue and (pr is None or int(issue.group(1)) != pr) else None
    cards.append({
        "id": c["id"], "repo": name, "license": lic, "issue": iss, "pr": pr,
        "base_commit": parent, "merge_commit": full, "title": c["title"], "symptom": c["symptom"],
        "root_cause": c["root_cause"], "trigger": c["trigger"], "distance": c["distance"], "why_missed": c["why_missed"],
        "fix_summary": c["fix_summary"], "fix_unique": c["fix_unique"], "skills": c["skills"], "pattern": c["pattern"],
        "field_guide_class": c["cls"], "elusiveness": c["elusiveness"], "distillable": c["distillable"],
        "reproduction_needs": c["reproduction_needs"], "files": files,
        "buggy": "\n...\n".join(buggy), "fixed": "\n...\n".join(fixed), "regression_test": regression,
        "commit_date": git(repo, "show", "-s", "--format=%ad", "--date=short", full).strip(),
        "url": f"https://github.com/{name}/pull/{pr}" if pr else f"https://github.com/{name}/commit/{full}",
        "original_pr": int(prs[0]) if len(prs) > 1 else None,
        "notes": c["notes"] + (" Backport; original PR #%s." % prs[0] if len(prs) > 1 else "") +("" if pr else " No PR number in the commit subject; merge_commit is the fix commit itself.")
                 + (" Fix is a squash-merge commit; merge_commit = that commit." if pr else ""),
    })
with open(OUT, "w", encoding="utf-8") as f:
    for x in cards:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
print(len(cards), "cards")
