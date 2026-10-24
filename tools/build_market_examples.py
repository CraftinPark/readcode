#!/usr/bin/env python3
"""Build the marketplace problems (examples/_sources/market) into examples/readcode-NNN.

For each problem in problems.py:
  1. copy the clean codebase to internal/baseline/ and to code/, then plant the
     bug in code/ (the main hunk plus any extra hunks; each must match once),
  2. gate A: t0 and the candidate's smoke tests pass on both; the problem's gate
     test passes on the baseline. Gate B: the gate test fails on code/,
  3. write evidence, manifest.json (keeps review status), public.json and key.json.

The answer to "where is the cause?" is the planted line(s); key.json also gives
the enclosing function as the bug's location.

Usage: python tools/build_market_examples.py [readcode-NNN ...]
"""
import ast, hashlib, importlib.util, json, os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "examples", "_sources", "market")
GATES = os.path.join(SRC, "gates", "test_gates.py")
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
LICENSE = {"spdx": "LicenseRef-ReadCode-Original", "attribution": "Written for ReadCode. Not affiliated with any delivery company."}
WEIGHTS = {"where": 40, "why": 40, "fix": 20}


def load_problems():
    spec = importlib.util.spec_from_file_location("market_problems", os.path.join(SRC, "problems.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def tree_files(root):
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in ("__pycache__", ".pytest_cache"))
        out += [os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/") for n in sorted(names)]
    return sorted(out)


def tree_sha256(root):
    """Same definition as tools/validate_example.py."""
    return hashlib.sha256("".join(f"{p}\t{sha256(os.path.join(root, p))}\n" for p in tree_files(root)).encode()).hexdigest()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def patch(code, hunk):
    p = os.path.join(code, hunk["file"])
    text = open(p, encoding="utf-8").read()
    if text.count(hunk["old"]) != 1:
        sys.exit(f"{hunk['file']}: text to replace must occur exactly once (found {text.count(hunk['old'])}): {hunk['old'][:60]!r}")
    write(p, text.replace(hunk["old"], hunk["new"]))


def enclosing_function(path, line):
    tree = ast.parse(open(path, encoding="utf-8").read())
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno <= line <= node.end_lineno:
            if best is None or node.lineno > best.lineno:
                best = node
    return best


def scrub(out, ex):
    return out.replace(ex, "<example>").replace(ex.replace("\\", "/"), "<example>")


def pytest(args, cwd, root=None):
    env = dict(ENV, READCODE_ROOT=root) if root else ENV
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-W", "ignore", *args],
                       cwd=cwd, env=env, capture_output=True, text=True)
    return p.returncode == 0, p.stdout + p.stderr


def build(prob, presets, where_prompt):
    ex = os.path.join(ROOT, "examples", prob["id"])
    code, base = os.path.join(ex, "code"), os.path.join(ex, "internal", "baseline")
    for d in (code, base):
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(os.path.join(SRC, "code"), d, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    for hunk in [prob["mutation"], *prob["extra"]]:
        patch(code, hunk)
    gates = os.path.join(ex, "internal", "verification", "test_gates.py")
    os.makedirs(os.path.dirname(gates), exist_ok=True)
    shutil.copyfile(GATES, gates)

    log, gate_a = [], True
    for label, (ok, out) in (
            ("t0 on baseline", pytest([f"{gates}::test_t0_ordinary_flow"], ex, base)),
            (f"{prob['gate']} on baseline", pytest([f"{gates}::{prob['gate']}"], ex, base)),
            ("t0 on shipped (must pass: the bug only shows in its scenario)", pytest([f"{gates}::test_t0_ordinary_flow"], ex, code)),
            ("smoke tests on baseline", pytest([], base)),
            ("smoke tests on shipped (the candidate's own tests pass)", pytest([], code))):
        gate_a &= ok
        log.append(f"== {label}: {'PASS' if ok else 'FAIL'}\n{scrub(out, ex)}")
    write(os.path.join(ex, "internal", "evidence", "gate_a.txt"), "\n".join(log))
    ship_ok, ship_out = pytest([f"{gates}::{prob['gate']}"], ex, code)
    detected = gate_a and not ship_ok
    write(os.path.join(ex, "internal", "evidence", "B1.txt"),
          f"== {prob['gate']} on shipped: {'PASS' if ship_ok else 'FAIL'} (must fail)\n{scrub(ship_out, ex)}")

    m = prob["mutation"]
    shipped_path = os.path.join(code, m["file"])
    text = open(shipped_path, encoding="utf-8").read()
    line = text[: text.index(m["new"])].count("\n") + 1
    span = max(1, m["new"].rstrip("\n").count("\n") + 1)
    fn = enclosing_function(shipped_path, line)

    mpath = os.path.join(ex, "manifest.json")
    old = json.load(open(mpath, encoding="utf-8")) if os.path.isfile(mpath) else {}
    manifest = {
        "schema_version": 1, "id": prob["id"],
        "source": {"kind": "generated", "license_spdx": LICENSE["spdx"], "original_sha256": tree_sha256(base)},
        "baseline": {"path": "internal/baseline", "sha256": tree_sha256(base),
                     "changes_summary": "The shared marketplace codebase (examples/_sources/market), clean. "
                                        "code/ is this with one planted bug from problems.py.",
                     "gate_a": {"passed": gate_a, "tests_run": 5, "tools": ["test-driver"],
                                "evidence_file": "internal/evidence/gate_a.txt"}},
        "shipped": [{"path": p, "sha256": sha256(os.path.join(code, p))} for p in tree_files(code)],
        "bugs": [{"id": "B1", "file": m["file"], "line": line, "change": {"old": m["old"], "new": m["new"]},
                  "gate_b": {"detected": detected, "detected_by": "test-driver" if detected else "none",
                             "evidence_file": "internal/evidence/B1.txt"}}],
        "review": old.get("review", {"status": "pending",
                                     "notes": "Marketplace problem (danny-v0). Needs a fresh-agent pilot solve and human review."}),
    }
    write(mpath, json.dumps(manifest, indent=2) + "\n")

    files = [{"path": p, "line_count": len(open(os.path.join(code, p), encoding="utf-8").read().splitlines())}
             for p in tree_files(code)]
    order = ["README.md", "market/app.py", "market/orders.py", "market/pricing.py", "market/payments.py",
             "market/dispatch.py", "market/payouts.py", "market/catalog.py", "market/money.py",
             "market/providers.py", "market/db.py", "market/seed.py", "market/__init__.py", "tests/test_smoke.py", "pytest.ini"]
    files.sort(key=lambda f: (order.index(f["path"]) if f["path"] in order else 99, f["path"]))
    where = {"file": m["file"], "start_line": line, "end_line": line + span - 1}
    public = {"schema_version": 1, "id": prob["id"], "version": 1, "title": prob["title"], "language": "python",
              "difficulty": prob["difficulty"], "track": "payments-infra", "area": prob["area"], "rung": prob["rung"],
              "topics": ["api", "payments", "multi-tenant"], "estimated_minutes": prob["minutes"], "files": files,
              "license": LICENSE, "questions": [], "design_prompts": [],
              "playground": {"kind": "backend-console", "engine": "market", "presets": presets},
              "tasks": [{"id": "T1", "type": "incident", "text": prob["ticket"], "parts": [
                  {"id": "where", "prompt": where_prompt, "select": "lines"},
                  {"id": "why", "prompt": "Why does that produce what they see?", "options": prob["why"]["options"]},
                  {"id": "fix", "prompt": "Which change fixes it?", "options": prob["fix"]["options"]}]}]}
    distractors = {**{f"why.{k}": v for k, v in prob["why"]["distractors"].items()},
                   **{f"fix.{k}": v for k, v in prob["fix"]["distractors"].items()}}
    key = {"schema_version": 1, "id": prob["id"], "version": 1,
           "scoring": {"total": 100, "sections": {"comprehension": 0, "bugs": 100, "design": 0, "improvements": 0}},
           "comprehension": [], "design": [], "improvements": {"weight": 0, "expected_themes": []}, "red_herrings": [],
           "bugs": [{"id": "B1", **{k: prob["bug"][k] for k in ("title", "severity", "category")}, "weight": 100,
                     "skills": prob["skills"],
                     "locations": [{"file": m["file"], "function": fn.name, "start_line": fn.lineno, "end_line": fn.end_lineno}],
                     **{k: prob["bug"][k] for k in ("description", "mechanism_anchors", "fix")}}],
           "grader_instructions": ["Task-only marketplace problem. 'where' is graded by line overlap (within 3 lines) "
                                   "with the planted lines; 'why' and 'fix' are multiple choice."],
           "tasks": [{"task_id": "T1", "type": "incident", "answer_bug_ids": ["B1"],
                      "part_answers": {"why": prob["why"]["answer"], "fix": prob["fix"]["answer"]},
                      "part_locations": {"where": [where]}, "part_weights": WEIGHTS, "distractors": distractors}]}
    write(os.path.join(ex, "public.json"), json.dumps(public, indent=2, ensure_ascii=False) + "\n")
    write(os.path.join(ex, "key.json"), json.dumps(key, indent=2, ensure_ascii=False) + "\n")
    print(f"{prob['id']}: gate A {'passed' if gate_a else 'FAILED'}, bug {'detected' if detected else 'NOT detected'} "
          f"({m['file']}:{line}, in {fn.name})")
    return gate_a and detected


def main():
    mod = load_problems()
    want = set(sys.argv[1:])
    ok = all([build(p, mod.PRESETS, mod.WHERE) for p in mod.PROBLEMS if not want or p["id"] in want])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
