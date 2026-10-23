#!/usr/bin/env python3
"""Build and verify readcode-002.

1. Apply MUTATIONS to the clean baseline (each `old` must occur exactly once) and
   write the result to code/payments_api.py.
2. Gate A: every test passes on the baseline.
3. Gate B: t0 passes on the shipped code and each B# test fails on it.
4. Write one evidence file per gate, and refresh the baseline/shipped/bugs parts
   of manifest.json (review status and the rest are left alone).

Usage: python internal/verification/run_gates.py [EXAMPLE_DIR]   (default: this example)
"""
import hashlib, json, os, subprocess, sys

EX = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", ".."))
BASELINE = "internal/baseline/payments_api.py"
SHIPPED = "payments_api.py"                      # relative to code/
TESTS = os.path.join(EX, "internal", "verification", "test_gates.py")

MUTATIONS = [
    ("B1", "        if charge is None or charge.account_id != account.id:\n",
           "        if charge is None:\n"),
    ("B2", "            if amount > charge.amount - charge.amount_refunded:\n",
           "            if amount > charge.amount:\n"),
    ("B3", "                scope = (account.id, idempotency_key)\n",
           "                scope = idempotency_key\n"),
    ("B4", "            mine = [c for c in mine if c.seq < cursor.seq]\n",
           "            mine = [c for c in mine if c.seq <= cursor.seq]\n"),
]
TEST_FOR = {"t0": "test_t0_ordinary_flow", "B1": "test_B1_cannot_read_another_accounts_charge",
            "B2": "test_B2_partial_refunds_cannot_exceed_the_charge",
            "B3": "test_B3_idempotency_keys_are_per_account", "B4": "test_B4_pages_do_not_repeat_or_skip"}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build_shipped():
    text = open(os.path.join(EX, BASELINE), encoding="utf-8").read()
    records = []
    for bug, old, new in MUTATIONS:
        if text.count(old) != 1:
            sys.exit(f"{bug}: the clean text must occur exactly once in the baseline (found {text.count(old)})")
        text = text.replace(old, new)
    for bug, old, new in MUTATIONS:                # line numbers in the final shipped file
        line = text[: text.index(new)].count("\n") + 1
        records.append({"id": bug, "line": line, "old": old, "new": new})
    os.makedirs(os.path.join(EX, "code"), exist_ok=True)
    with open(os.path.join(EX, "code", SHIPPED), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return records


def run(test, unit):
    env = dict(os.environ, READCODE_UNIT=os.path.join(EX, unit))
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-W", "ignore",
                        f"{TESTS}::{TEST_FOR[test]}"], cwd=EX, env=env, capture_output=True, text=True)
    out = (p.stdout + p.stderr).replace(EX, "<example>").replace(EX.replace("\\", "/"), "<example>")
    return p.returncode == 0, out


def evidence(name, text):
    os.makedirs(os.path.join(EX, "internal", "evidence"), exist_ok=True)
    rel = f"internal/evidence/{name}.txt"
    with open(os.path.join(EX, rel), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return rel


def main():
    records = build_shipped()
    shipped_rel = os.path.join("code", SHIPPED)

    gate_a, log = True, []
    for t in TEST_FOR:
        ok, out = run(t, BASELINE)
        gate_a &= ok
        log.append(f"== {t} on baseline: {'PASS' if ok else 'FAIL'}\n{out}")
    ok, out = run("t0", shipped_rel)
    gate_a &= ok
    log.append(f"== t0 on shipped: {'PASS' if ok else 'FAIL'} (must pass: tests discriminate)\n{out}")
    a_file = evidence("gate_a", "\n".join(log))
    print(f"gate A: {'passed' if gate_a else 'FAILED'}")

    bugs = []
    for r in records:
        base_ok, base_out = run(r["id"], BASELINE)
        ship_ok, ship_out = run(r["id"], shipped_rel)
        detected = base_ok and not ship_ok
        ev = evidence(r["id"], f"== {r['id']} on baseline: {'PASS' if base_ok else 'FAIL'}\n{base_out}\n"
                               f"== {r['id']} on shipped: {'PASS' if ship_ok else 'FAIL'}\n{ship_out}")
        print(f"{r['id']}: {'detected' if detected else 'NOT detected'}")
        bugs.append({"id": r["id"], "file": SHIPPED, "line": r["line"],
                     "change": {"old": r["old"], "new": r["new"]},
                     "gate_b": {"detected": detected, "detected_by": "test-driver" if detected else "none",
                                "evidence_file": ev}})

    mpath = os.path.join(EX, "manifest.json")
    man = json.load(open(mpath, encoding="utf-8")) if os.path.isfile(mpath) else {}
    man["baseline"] = dict(man.get("baseline", {}), path=BASELINE, sha256=sha256(os.path.join(EX, BASELINE)),
                           gate_a={"passed": gate_a, "tests_run": len(TEST_FOR) + 1,
                                   "tools": ["test-driver"], "evidence_file": a_file})
    man["shipped"] = [{"path": SHIPPED, "sha256": sha256(os.path.join(EX, shipped_rel))}]
    man["bugs"] = bugs
    with open(mpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(man, indent=2) + "\n")
    sys.exit(0 if gate_a and all(b["gate_b"]["detected"] for b in bugs) else 1)


if __name__ == "__main__":
    main()
