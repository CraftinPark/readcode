#!/usr/bin/env python3
"""ReadCode example validator.

Layer 1  JSON Schema: shape of public.json, key.json, manifest.json.
Layer 2  Consistency: cross-file rules and checks against the actual code.

Usage:
    python validate_example.py EXAMPLE_DIR [EXAMPLE_DIR ...] [--schemas DIR]
    python validate_example.py --all EXAMPLES_ROOT

Exit code 0 if every example has no errors (warnings are allowed), 1 otherwise.
Requires: pip install jsonschema   (optional: rfc3339-validator, rfc3987 for date/uri format checks)

Example layout:
    readcode-001/
      public.json  key.json  manifest.json
      code/...                      <- the only code the candidate sees
      internal/baseline/...         <- clean reference code
      internal/evidence/...         <- gate outputs referenced by the manifest
"""
import argparse, hashlib, json, math, os, re, sys

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    sys.exit("This tool needs the 'jsonschema' package:  pip install jsonschema")

FILES = ("public", "key", "manifest")
KEY_ONLY_FIELDS = {"key_points", "anchors", "mechanism_anchors", "red_herrings", "fix", "grader_instructions",
                   "skills", "answer_bug_ids", "verdict", "has_defect", "correct_option", "distractors"}
DEFAULT_TAXONOMY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "taxonomy", "taxonomy.json")
HINT_WORDS = re.compile(r"\b(BUG|FIXME|XXX|HACK|seeded|mutant|injected|vulnerab\w*)\b", re.I)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_keys(v)


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")


def load_schemas(schema_dir):
    out = {}
    for n in FILES:
        with open(os.path.join(schema_dir, f"{n}.schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
        Draft202012Validator.check_schema(schema)
        out[n] = Draft202012Validator(schema, format_checker=FormatChecker())
    return out


class Taxonomy:
    """taxonomy.json indexed by id. `errors` lists problems with the taxonomy itself."""

    def __init__(self, doc, errors):
        self.doc, self.errors = doc, errors
        self.tracks = {t["id"]: t for t in doc.get("tracks", [])}
        self.areas = {a["id"]: a for a in doc.get("areas", [])}
        self.skills = {s["id"] for s in doc.get("skills", [])}
        self.topics = {t["id"] for t in doc.get("topics", [])}


def load_taxonomy(path=DEFAULT_TAXONOMY, schema_dir=None):
    schema_dir = schema_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas")
    with open(os.path.join(schema_dir, "taxonomy.schema.json"), encoding="utf-8") as f:
        v = Draft202012Validator(json.load(f))
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    errs = [f"taxonomy [{'/'.join(map(str, e.path)) or '(root)'}]: {e.message[:200]}" for e in v.iter_errors(doc)]
    if errs:
        return Taxonomy({}, errs)
    for label in ("tracks", "areas", "skills", "topics"):
        ids = [x["id"] for x in doc[label]]
        if len(ids) != len(set(ids)):
            errs.append(f"taxonomy.{label}: duplicate ids")
    tax = Taxonomy(doc, errs)
    if tax.skills & tax.topics:
        errs.append(f"taxonomy: ids used as both skill and topic (topics must not reveal skills): {sorted(tax.skills & tax.topics)}")
    for a in doc["areas"]:
        if a["track"] not in tax.tracks:
            errs.append(f"taxonomy.areas[{a['id']}]: unknown track '{a['track']}'")
        unknown = sorted(set(a["skills"]) - tax.skills)
        if unknown:
            errs.append(f"taxonomy.areas[{a['id']}]: unknown skills {unknown}")
    return tax


def check_tags(rep, tax, pub, key, code_text=""):
    """Track/area/topics in public.json and per-bug skills in key.json must come from the taxonomy.
    A skill named in the public text is a hint, unless the code itself already uses the word."""
    for e in tax.errors:
        rep.err("taxonomy", e)
    if tax.errors:
        return
    if pub["track"] not in tax.tracks:
        rep.err("public.track", f"unknown track '{pub['track']}'")
    area = tax.areas.get(pub["area"])
    if area is None:
        rep.err("public.area", f"unknown area '{pub['area']}'")
    elif area["track"] != pub["track"]:
        rep.err("public.area", f"area '{pub['area']}' belongs to track '{area['track']}', not '{pub['track']}'")
    for t in pub["topics"]:
        if t in tax.skills:
            rep.err("public.topics", f"'{t}' is a skill; skills reveal the bugs and belong in key.json only")
        elif t not in tax.topics:
            rep.err("public.topics", f"unknown topic '{t}'")
    used = set()
    for b in key["bugs"]:
        unknown = sorted(set(b["skills"]) - tax.skills)
        if unknown:
            rep.err(f"key.bugs[{b['id']}]", f"unknown skills {unknown}")
        used |= set(b["skills"])
    if area is not None:
        outside = sorted((used & tax.skills) - set(area["skills"]))
        if outside:
            rep.warn("key.bugs", f"skills not listed for area '{area['id']}': {outside} (add them to the area or retag)")
    text = " ".join([pub["title"]] + [q["text"] for q in pub["questions"] + pub["design_prompts"] + pub.get("tasks", [])]).lower()
    for s in sorted(used & tax.skills):
        word = rf"\b{re.escape(s.replace('-', ' '))}\b|\b{re.escape(s)}\b"
        if re.search(word, text) and not re.search(word, code_text.lower()):
            rep.warn("public.json", f"names the skill '{s}' that one of its bugs is tagged with; this may give the bug away")


def check_tasks(rep, pub, key):
    ptasks = {t["id"]: t for t in pub.get("tasks", [])}
    ktasks = {t["task_id"]: t for t in key.get("tasks", [])}
    if len(ptasks) != len(pub.get("tasks", [])) or len(ktasks) != len(key.get("tasks", [])):
        rep.err("tasks", "duplicate task ids")
    if set(ptasks) != set(ktasks):
        rep.err("tasks", f"public has {sorted(ptasks)} but key answers {sorted(ktasks)}")
    bug_ids = {b["id"] for b in key["bugs"]}
    for tid in sorted(set(ptasks) & set(ktasks)):
        p, k, where = ptasks[tid], ktasks[tid], f"key.tasks[{tid}]"
        if p["type"] != k["type"]:
            rep.err(where, f"type is '{k['type']}' in the key but '{p['type']}' in public")
            continue
        if k["type"] == "incident":
            unknown = sorted(set(k["answer_bug_ids"]) - bug_ids)
            if unknown:
                rep.err(where, f"answer_bug_ids {unknown} are not bugs in the key")
        elif k["type"] == "review_pr":
            if (k["verdict"] == "approve") == k["has_defect"]:
                rep.err(where, "verdict and has_defect contradict each other")
        elif k["type"] == "trace":
            opts = {o["id"] for o in p["options"]}
            if k["correct_option"] not in opts:
                rep.err(where, f"correct_option '{k['correct_option']}' is not one of the options {sorted(opts)}")
            bad = sorted(set(k["distractors"]) - (opts - {k["correct_option"]}))
            if bad:
                rep.err(where, f"distractors {bad} are not wrong options")


def check_shape(rep, validators, docs):
    for n, doc in docs.items():
        for e in sorted(validators[n].iter_errors(doc), key=lambda e: list(map(str, e.path))):
            path = "/".join(map(str, e.path)) or "(root)"
            rep.err(f"{n}.json [{path}]", e.message[:200])


def in_ranges(line, ranges):
    return any(r["start_line"] <= line <= r["end_line"] for r in ranges)


def check_consistency(rep, ex, pub, key, man):
    name = os.path.basename(os.path.normpath(ex))
    code_dir = os.path.join(ex, "code")

    # ---- identity
    if not (pub["id"] == key["id"] == man["id"]):
        rep.err("ids", f"id differs across files: public={pub['id']} key={key['id']} manifest={man['id']}")
    if pub["id"] != name:
        rep.err("ids", f"id '{pub['id']}' does not match the folder name '{name}'")
    if pub["version"] != key["version"]:
        rep.err("versions", f"public.version={pub['version']} but key.version={key['version']}")

    # ---- code files
    lines_of = {}
    for f in pub["files"]:
        p = os.path.join(code_dir, f["path"])
        if not os.path.isfile(p):
            rep.err("public.files", f"code/{f['path']} does not exist")
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        lines_of[f["path"]] = text.split("\n")
        actual = len(text.splitlines())
        if actual != f["line_count"]:
            rep.err("public.files", f"{f['path']}: line_count says {f['line_count']} but the file has {actual}")
        for i, ln in enumerate(text.splitlines(), 1):
            if HINT_WORDS.search(ln):
                rep.warn("code", f"{f['path']}:{i} contains a word that may hint at a bug: {ln.strip()[:60]!r}")
    declared = {f["path"] for f in pub["files"]}
    for root, _, names in os.walk(code_dir):
        for n in names:
            rel = os.path.relpath(os.path.join(root, n), code_dir).replace(os.sep, "/")
            if rel not in declared:
                rep.warn("code", f"code/{rel} exists but is not listed in public.files (candidates would see it)")

    # ---- ids: uniqueness and matching
    def dupes(xs):
        return sorted({x for x in xs if xs.count(x) > 1})
    q_ids = [q["id"] for q in pub["questions"]]
    d_ids = [d["id"] for d in pub["design_prompts"]]
    for label, ids in (("public.questions", q_ids), ("public.design_prompts", d_ids),
                       ("key.comprehension", [c["question_id"] for c in key["comprehension"]]),
                       ("key.design", [d["prompt_id"] for d in key["design"]]),
                       ("key.bugs", [b["id"] for b in key["bugs"]]),
                       ("manifest.bugs", [b["id"] for b in man["bugs"]])):
        if dupes(ids):
            rep.err(label, f"duplicate ids: {dupes(ids)}")
    kq = {c["question_id"] for c in key["comprehension"]}
    kd = {d["prompt_id"] for d in key["design"]}
    if kq != set(q_ids):
        rep.err("questions", f"public has {sorted(q_ids)} but key scores {sorted(kq)}")
    if kd != set(d_ids):
        rep.err("design", f"public has {sorted(d_ids)} but key scores {sorted(kd)}")
    kb = {b["id"] for b in key["bugs"]}
    mb = {b["id"] for b in man["bugs"]}
    if kb != mb:
        rep.err("bugs", f"key lists {sorted(kb)} but manifest records {sorted(mb)}")

    # ---- weights
    close = lambda a, b: math.isclose(a, b, abs_tol=1e-6)
    sec = key["scoring"]["sections"]
    sums = {"comprehension": sum(c["weight"] for c in key["comprehension"]),
            "bugs": sum(b["weight"] for b in key["bugs"]),
            "design": sum(d["weight"] for d in key["design"]),
            "improvements": sum(t["weight"] for t in key["improvements"]["expected_themes"])}
    for s, total in sums.items():
        if not close(total, sec[s]):
            rep.err("key.scoring", f"{s}: item weights sum to {total} but the section is {sec[s]}")
    if not close(key["improvements"]["weight"], sec["improvements"]):
        rep.err("key.improvements", f"weight {key['improvements']['weight']} != section {sec['improvements']}")
    if not close(sum(sec.values()), key["scoring"]["total"]):
        rep.err("key.scoring", f"sections sum to {sum(sec.values())}, total is {key['scoring']['total']}")

    # ---- line ranges in the key
    def check_range(where, r):
        if r["file"] not in lines_of:
            rep.err(where, f"unknown file '{r['file']}'")
        elif r["start_line"] > r["end_line"] or r["end_line"] > len(lines_of[r["file"]]):
            rep.err(where, f"lines {r['start_line']}-{r['end_line']} are outside {r['file']}")
    for b in key["bugs"]:
        for r in b["locations"]:
            check_range(f"key.bugs[{b['id']}]", r)
    for i, h in enumerate(key["red_herrings"]):
        for r in h.get("locations", []):
            check_range(f"key.red_herrings[{i}]", r)

    # ---- manifest <-> code <-> key
    baseline_text = None
    bpath = man["baseline"].get("path")
    if bpath:
        full = os.path.join(ex, bpath)
        if not os.path.isfile(full):
            rep.err("manifest.baseline", f"{bpath} does not exist")
        else:
            baseline_text = open(full, encoding="utf-8", errors="replace").read()
            if sha256(full) != man["baseline"]["sha256"]:
                rep.err("manifest.baseline", "sha256 does not match the baseline file")
    else:
        rep.warn("manifest.baseline", "no baseline path given; cannot check that each bug's clean text exists")

    shipped_paths = {s["path"] for s in man["shipped"]}
    if shipped_paths != declared:
        rep.err("manifest.shipped", f"lists {sorted(shipped_paths)} but public.files lists {sorted(declared)}")
    for s in man["shipped"]:
        p = os.path.join(code_dir, s["path"])
        if os.path.isfile(p) and sha256(p) != s["sha256"]:
            rep.err("manifest.shipped", f"{s['path']} was modified after the checks ran (sha256 mismatch)")

    key_bug = {b["id"]: b for b in key["bugs"]}
    for b in man["bugs"]:
        where = f"manifest.bugs[{b['id']}]"
        lines = lines_of.get(b["file"])
        if lines is None:
            rep.err(where, f"unknown file '{b['file']}'")
        else:
            new_lines = b["change"]["new"].rstrip("\n").split("\n")
            got = lines[b["line"] - 1: b["line"] - 1 + len(new_lines)]
            if got != new_lines:
                rep.err(where, f"the shipped code at line {b['line']} does not match the recorded change")
        if baseline_text is not None and b["change"]["old"] not in baseline_text:
            rep.err(where, "the recorded clean text is not in the baseline file")
        if b["id"] in key_bug and not in_ranges(b["line"], key_bug[b["id"]]["locations"]):
            rep.err(where, f"line {b['line']} is not inside any location the key gives for this bug")
        ev = os.path.join(ex, b["gate_b"]["evidence_file"])
        if not os.path.isfile(ev):
            rep.err(where, f"evidence file {b['gate_b']['evidence_file']} is missing")
        if b["gate_b"]["detected"] != (b["gate_b"]["detected_by"] != "none"):
            rep.err(where, "detected and detected_by contradict each other")
    ev = man["baseline"]["gate_a"].get("evidence_file")
    if ev and not os.path.isfile(os.path.join(ex, ev)):
        rep.err("manifest.baseline", f"evidence file {ev} is missing")

    # ---- licence and review gating
    if pub["license"]["spdx"] != man["source"]["license_spdx"]:
        rep.err("license", f"public says {pub['license']['spdx']} but the manifest says {man['source']['license_spdx']}")
    status = man["review"]["status"]
    undetected = [b["id"] for b in man["bugs"] if not b["gate_b"]["detected"]]
    if status == "approved" and undetected:
        rep.err("review", f"approved, but these bugs were never detected by a check: {undetected}")
    elif undetected:
        rep.warn("gates", f"bugs not detected by any check (cannot be approved yet): {undetected}")
    if not man["baseline"]["gate_a"]["passed"] and status != "approved":
        rep.warn("gates", "gate A (clean baseline) has not passed")
    if "publish" in man and status != "approved":
        rep.err("publish", "has publish info but review status is not 'approved'")

    # ---- the public file must not leak grader-only content
    leaked = sorted(KEY_ONLY_FIELDS & set(walk_keys(pub)))
    if leaked:
        rep.err("public.json", f"contains grader-only fields: {leaked}")
    blob = json.dumps(pub).lower()
    for c in key["comprehension"]:
        for kp in c["key_points"]:
            if len(kp) > 25 and kp.lower() in blob:
                rep.err("public.json", f"contains an answer key point verbatim: {kp[:50]!r}")


def validate(ex, validators, taxonomy=None):
    taxonomy = taxonomy or load_taxonomy()
    rep, docs = Report(), {}
    for n in FILES:
        p = os.path.join(ex, f"{n}.json")
        if not os.path.isfile(p):
            rep.err(f"{n}.json", "file is missing")
            continue
        try:
            with open(p, encoding="utf-8") as f:
                docs[n] = json.load(f)
        except json.JSONDecodeError as e:
            rep.err(f"{n}.json", f"not valid JSON: {e}")
    if len(docs) == len(FILES):
        check_shape(rep, validators, docs)
        if not rep.errors:                       # consistency checks assume the shape is right
            check_consistency(rep, ex, docs["public"], docs["key"], docs["manifest"])
            code_text = "\n".join(open(os.path.join(ex, "code", f["path"]), encoding="utf-8", errors="replace").read()
                                  for f in docs["public"]["files"] if os.path.isfile(os.path.join(ex, "code", f["path"])))
            check_tags(rep, taxonomy, docs["public"], docs["key"], code_text)
            check_tasks(rep, docs["public"], docs["key"])
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="*", help="example folders")
    ap.add_argument("--all", metavar="ROOT", help="validate every sub-folder of ROOT that has a manifest.json")
    ap.add_argument("--schemas", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas"))
    ap.add_argument("--taxonomy", default=DEFAULT_TAXONOMY)
    a = ap.parse_args()
    dirs = list(a.dirs)
    if a.all:
        dirs += sorted(os.path.join(a.all, d) for d in os.listdir(a.all)
                       if os.path.isfile(os.path.join(a.all, d, "manifest.json")))
    if not dirs:
        ap.error("give at least one example folder, or --all ROOT")
    validators = load_schemas(a.schemas)
    taxonomy = load_taxonomy(a.taxonomy, a.schemas)
    bad = 0
    for ex in dirs:
        rep = validate(ex, validators, taxonomy)
        print(f"{'FAIL' if rep.errors else 'OK  '}  {ex}  ({len(rep.errors)} errors, {len(rep.warnings)} warnings)")
        for m in rep.errors:
            print(f"   ERROR  {m}")
        for m in rep.warnings:
            print(f"   warn   {m}")
        bad += bool(rep.errors)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
