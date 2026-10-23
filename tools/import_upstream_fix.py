#!/usr/bin/env python3
"""Build an example's code from a real, already-fixed upstream bug.

Reads EXAMPLE/internal/source/spec.json, then:
  1. fetches each listed file at the pre-fix commit (raw.githubusercontent.com),
  2. keeps only the listed line ranges (an excerpt) under a short provenance
     header, and writes them to code/ (what the candidate sees: the buggy code),
  3. applies the upstream fix to the excerpt and writes internal/baseline/,
  4. copies the upstream license into code/ (BSD/MIT require it),
  5. writes evidence (issue, fix PR, the PR's regression tests) and fills the
     source/baseline/shipped/bugs parts of manifest.json.

The candidate-facing files (public.json, key.json) are written by hand.

Evidence class: the bug is proven by the upstream fix and its regression
test, not by running anything here (gate_b.detected_by = "upstream-fix").

Usage: python tools/import_upstream_fix.py examples/readcode-004
"""
import datetime, hashlib, json, os, re, sys, urllib.request

RAW = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def tree_files(root):
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        out += [os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/") for n in sorted(names)]
    return sorted(out)


def tree_sha256(root):
    """Same definition as tools/validate_example.py."""
    lines = "".join(f"{p}\t{sha256_bytes(open(os.path.join(root, p), 'rb').read())}\n" for p in tree_files(root))
    return hashlib.sha256(lines.encode()).hexdigest()


def excerpt(text, ranges, header):
    lines = text.split("\n")
    parts = []
    for i, (a, b) in enumerate(ranges):
        if i:
            parts.append("\n\n# ...\n\n")
        parts.append("\n".join(lines[a - 1:b]).strip("\n"))
    return header + "\n\n" + "".join(parts) + "\n"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def regression_tests(diff):
    """The test files the fix PR added or changed, as evidence."""
    chunks = re.split(r"(?=^diff --git )", diff, flags=re.M)
    return "".join(c for c in chunks if re.match(r"diff --git a/\S*tests?/", c))


def main():
    ex = os.path.abspath(sys.argv[1])
    spec = json.load(open(os.path.join(ex, "internal", "source", "spec.json"), encoding="utf-8"))
    repo, base = spec["repo"], spec["base_commit"]
    code, baseline = os.path.join(ex, "code"), os.path.join(ex, "internal", "baseline")
    originals = []

    for f in spec["files"]:
        raw = fetch(RAW.format(repo=repo, commit=base, path=f["path"]))
        originals.append(raw.encode())
        spans = ", ".join(f"{a}-{b}" for a, b in f["ranges"])
        whole = f["ranges"] == [[1, len(raw.rstrip("\n").split("\n"))]]
        header = (f"# {f['path']} from {repo} at {base[:10]} ({'full file' if whole else f'lines {spans}; other code removed'}).\n"
                  f"# {spec['license_spdx']}, see {spec['license_file']}.")
        shipped = excerpt(raw, f["ranges"], header)
        clean = shipped
        for fix in spec["fixes"]:
            if fix["file"] == f["path"]:
                if clean.count(fix["buggy"]) != 1:
                    sys.exit(f"{fix['id']}: the buggy text must occur exactly once in the excerpt of {f['path']}")
                clean = clean.replace(fix["buggy"], fix["fixed"])
        write(os.path.join(code, f["path"]), shipped)
        write(os.path.join(baseline, f["path"]), clean)

    license_text = fetch(RAW.format(repo=repo, commit=base, path=spec.get("license_path", "LICENSE")))
    for root in (code, baseline):
        write(os.path.join(root, spec["license_file"]), license_text)

    diff = fetch(f"https://github.com/{repo}/pull/{spec['pr']}.diff")
    ev_dir = os.path.join(ex, "internal", "evidence")
    bugs = []
    # A fix with "record": false is part of the upstream change (e.g. a caller's
    # signature) but not a separate bug: it goes into the baseline only.
    for fix in (f for f in spec["fixes"] if f.get("record", True)):
        shipped = open(os.path.join(code, fix["file"]), encoding="utf-8").read()
        line = shipped[: shipped.index(fix["buggy"])].count("\n") + 1
        ev = f"internal/evidence/{fix['id']}.txt"
        write(os.path.join(ex, ev),
              f"{fix['id']}: real bug, fixed upstream (not executed here)\n"
              f"issue:  https://github.com/{repo}/issues/{spec['issue']}\n"
              f"fix PR: https://github.com/{repo}/pull/{spec['pr']} (merged as {spec['merge_commit']})\n"
              f"buggy code at {base}\n\n== regression tests added or changed by the fix PR ==\n"
              + (regression_tests(diff) or "(none in the PR diff)\n"))
        bugs.append({"id": fix["id"], "file": fix["file"], "line": line,
                     "change": {"old": fix["fixed"], "new": fix["buggy"]},
                     "gate_b": {"detected": True, "detected_by": "upstream-fix", "evidence_file": ev}})
    write(os.path.join(ev_dir, "gate_a.txt"),
          f"Gate A was not run locally: {repo} needs its full stack (database, settings) to run tests.\n"
          f"The fixed code is upstream commit {spec['merge_commit']}, merged after review.\n")

    mpath = os.path.join(ex, "manifest.json")
    man = json.load(open(mpath, encoding="utf-8")) if os.path.isfile(mpath) else {"review": {"status": "pending"}}
    man = {
        "schema_version": 1, "id": os.path.basename(ex),
        "source": {"kind": "scraped", "repo": f"https://github.com/{repo}", "path": spec["files"][0]["path"],
                   "commit": base, "license_spdx": spec["license_spdx"],
                   "retrieved_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                   "original_sha256": sha256_bytes(b"".join(originals))},
        "baseline": {"path": "internal/baseline", "sha256": tree_sha256(baseline),
                     "changes_summary": f"Excerpts of the files above with the upstream fix (PR #{spec['pr']}) applied.",
                     "gate_a": {"passed": False, "tests_run": 0, "tools": ["upstream-ci"],
                                "evidence_file": "internal/evidence/gate_a.txt"}},
        "shipped": [{"path": p, "sha256": sha256_bytes(open(os.path.join(code, p), "rb").read())} for p in tree_files(code)],
        "bugs": bugs,
        "review": man.get("review", {"status": "pending"}),
    }
    write(mpath, json.dumps(man, indent=2) + "\n")
    print(f"{man['id']}: {len(spec['files'])} file(s), {len(bugs)} bug(s), shipped {len(man['shipped'])} files")


if __name__ == "__main__":
    main()
