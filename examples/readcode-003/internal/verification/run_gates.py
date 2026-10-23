#!/usr/bin/env python3
"""Build and verify readcode-003 (a multi-file example).

1. Copy internal/baseline/ to code/ and apply MUTATIONS (each `old` must occur
   exactly once in its file).
2. Gate A: every test passes on the baseline; t0 and the candidate's own
   smoke tests (code/tests) pass on the shipped code.
3. Gate B: each B# test fails on the shipped code.
4. Write evidence files and refresh the baseline/shipped/bugs parts of
   manifest.json (review status and the rest are left alone).

Usage: python internal/verification/run_gates.py [EXAMPLE_DIR]   (default: this example)
"""
import hashlib, json, os, shutil, subprocess, sys

EX = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", ".."))
BASELINE = "internal/baseline"
TESTS = os.path.join(EX, "internal", "verification", "test_gates.py")

MUTATIONS = [
    ("B1", "payments/app.py",
     '        reference = idempotency.network_reference(acct, idempotency_key) if idempotency_key else db.new_id("ref")\n',
     '        reference = db.new_id("ref")\n'),
    ("B2", "payments/idempotency.py",
     "    cutoff = now_ms - int(KEY_TTL.total_seconds() * 1000)\n",
     "    cutoff = now_ms - int(KEY_TTL.total_seconds())\n"),
    ("B3", "payments/webhooks.py",
     "        if status is not None and 200 <= status < 300:\n",
     "        if status is not None and status < 500:\n"),
    ("B4", "payments/webhooks.py",
     '        cache_key = ev["account_id"]\n',
     '        cache_key = ev["type"]\n'),
]
TEST_FOR = {"t0": "test_t0_ordinary_flow",
            "B1": "test_B1_retry_after_a_failure_does_not_charge_the_card_twice",
            "B2": "test_B2_a_key_is_kept_for_24_hours",
            "B3": "test_B3_a_4xx_from_the_endpoint_is_retried",
            "B4": "test_B4_events_go_to_their_own_accounts_endpoint"}
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def tree_files(root):
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        out += [os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/") for n in sorted(names)]
    return sorted(out)


def tree_sha256(root):
    """Same definition as tools/validate_example.py: sha256 over 'path<TAB>sha256' lines."""
    lines = "".join(f"{p}\t{sha256(os.path.join(root, p))}\n" for p in tree_files(root))
    return hashlib.sha256(lines.encode()).hexdigest()


def build_shipped():
    code = os.path.join(EX, "code")
    shutil.rmtree(code, ignore_errors=True)
    shutil.copytree(os.path.join(EX, BASELINE), code, ignore=shutil.ignore_patterns("__pycache__"))
    records = []
    for bug, rel, old, new in MUTATIONS:
        p = os.path.join(code, rel)
        text = open(p, encoding="utf-8").read()
        if text.count(old) != 1:
            sys.exit(f"{bug}: the clean text must occur exactly once in {rel} (found {text.count(old)})")
        text = text.replace(old, new)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        records.append({"id": bug, "file": rel, "old": old, "new": new})
    for r in records:                               # line numbers in the final shipped files
        text = open(os.path.join(code, r["file"]), encoding="utf-8").read()
        r["line"] = text[: text.index(r["new"])].count("\n") + 1
    return records


def scrub(out):
    return out.replace(EX, "<example>").replace(EX.replace("\\", "/"), "<example>")


def run_gate(test, root):
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-W", "ignore",
                        f"{TESTS}::{TEST_FOR[test]}"], cwd=EX, env=dict(ENV, READCODE_ROOT=os.path.join(EX, root)),
                       capture_output=True, text=True)
    return p.returncode == 0, scrub(p.stdout + p.stderr)


def run_smoke(root):
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-W", "ignore"],
                       cwd=os.path.join(EX, root), env=ENV, capture_output=True, text=True)
    return p.returncode == 0, scrub(p.stdout + p.stderr)


def evidence(name, text):
    os.makedirs(os.path.join(EX, "internal", "evidence"), exist_ok=True)
    rel = f"internal/evidence/{name}.txt"
    with open(os.path.join(EX, rel), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return rel


def main():
    records = build_shipped()

    gate_a, log = True, []
    for t in TEST_FOR:
        ok, out = run_gate(t, BASELINE)
        gate_a &= ok
        log.append(f"== {t} on baseline: {'PASS' if ok else 'FAIL'}\n{out}")
    for label, (ok, out) in (("t0 on shipped", run_gate("t0", "code")),
                             ("smoke tests on baseline", run_smoke(BASELINE)),
                             ("smoke tests on shipped (the candidate's tests must pass)", run_smoke("code"))):
        gate_a &= ok
        log.append(f"== {label}: {'PASS' if ok else 'FAIL'}\n{out}")
    a_file = evidence("gate_a", "\n".join(log))
    print(f"gate A: {'passed' if gate_a else 'FAILED'}")

    bugs = []
    for r in records:
        base_ok, base_out = run_gate(r["id"], BASELINE)
        ship_ok, ship_out = run_gate(r["id"], "code")
        detected = base_ok and not ship_ok
        ev = evidence(r["id"], f"== {r['id']} on baseline: {'PASS' if base_ok else 'FAIL'}\n{base_out}\n"
                               f"== {r['id']} on shipped: {'PASS' if ship_ok else 'FAIL'}\n{ship_out}")
        print(f"{r['id']}: {'detected' if detected else 'NOT detected'}")
        bugs.append({"id": r["id"], "file": r["file"], "line": r["line"], "change": {"old": r["old"], "new": r["new"]},
                     "gate_b": {"detected": detected, "detected_by": "test-driver" if detected else "none",
                                "evidence_file": ev}})

    mpath = os.path.join(EX, "manifest.json")
    man = json.load(open(mpath, encoding="utf-8")) if os.path.isfile(mpath) else {}
    man["baseline"] = dict(man.get("baseline", {}), path=BASELINE, sha256=tree_sha256(os.path.join(EX, BASELINE)),
                           gate_a={"passed": gate_a, "tests_run": len(TEST_FOR) + 3,
                                   "tools": ["test-driver"], "evidence_file": a_file})
    man["shipped"] = [{"path": p, "sha256": sha256(os.path.join(EX, "code", p))} for p in tree_files(os.path.join(EX, "code"))]
    man["bugs"] = bugs
    with open(mpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(man, indent=2) + "\n")
    sys.exit(0 if gate_a and all(b["gate_b"]["detected"] for b in bugs) else 1)


if __name__ == "__main__":
    main()
