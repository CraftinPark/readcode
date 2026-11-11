"""Grade a player's answers.json. No judge: location + three multiple-choice answers.

    python _key/check_key.py path/to/answers.json     # grade one file
    python _key/check_key.py --self-test              # reference passes, misreads fail

Location: file must match one accepted site and the range [start_line, end_line]
(at most MAX_SPAN lines) must overlap that site widened by TOL lines.
Sites are found by anchor text in the shipped files, so they follow edits.
Pass = verdict "bug" + location + q1 + q2 + q3 all right.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOL = 3
MAX_SPAN = 15

ANSWERS = {"q1": "b", "q2": "a", "q3": "a"}

# (file, first-line anchor, last-line anchor, label)
SITES = [
    ("armrl/buffer.py", "    @property", "        return self.advantages + self.values",
     "returns property derived from advantages (primary)"),
    ("armrl/buffer.py", "    def normalize_advantages(self, eps=1e-8):",
     "        self.advantages = (adv - adv.mean()) / (adv.std() + eps)",
     "normalize_advantages overwrites what returns is derived from"),
    ("armrl/buffer.py", '            "returns": torch.as_tensor(self.returns.reshape(B)),',
     '            "returns": torch.as_tensor(self.returns.reshape(B)),',
     "flat() reads returns after normalisation"),
    ("armrl/ppo.py", "        if cfg.norm_adv:", "            buf.normalize_advantages()",
     "update normalises before flat() reads returns"),
]


def find_sites(root=ROOT):
    out = []
    for rel, first, last, label in SITES:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            lines = f.read().splitlines()
        hits = [i for i, l in enumerate(lines) if l == first]
        # the property anchor ("    @property") is only unique next to its body
        start = None
        for i in hits:
            for j in range(i, min(i + 8, len(lines))):
                if lines[j] == last:
                    start, end = i + 1, j + 1
                    break
            if start:
                break
        if start is None:
            raise SystemExit(f"anchor not found in {rel}: {first!r}")
        out.append((rel, start, end, label))
    return out


def grade(ans, sites=None):
    sites = sites or find_sites()
    res = {"verdict": ans.get("verdict") == "bug", "location": False, "site": None}
    f = str(ans.get("file", "")).replace("\\", "/").lstrip("./")
    try:
        s, e = int(ans.get("start_line", 0)), int(ans.get("end_line", 0))
    except (TypeError, ValueError):
        s, e = 0, 0
    if s > e:
        s, e = e, s
    if res["verdict"] and s >= 1 and e - s + 1 <= MAX_SPAN:
        for rel, a, b, label in sites:
            if f == rel and s <= b + TOL and e >= a - TOL:
                res["location"], res["site"] = True, label
                break
    for q, right in ANSWERS.items():
        res[q] = str(ans.get(q, "")).strip().lower().rstrip(")") == right
    res["pass"] = all(res[k] for k in ("verdict", "location", "q1", "q2", "q3"))
    return res


def report(res):
    for k in ("verdict", "location", "q1", "q2", "q3"):
        print(f"  {k:<9} {'right' if res[k] else 'wrong'}")
    print("  PASS" if res["pass"] else "  FAIL")


def self_test():
    sites = find_sites()
    for rel, a, b, label in sites:
        print(f"site {rel}:{a}-{b}  {label}")
    cases = []
    for name in sorted(os.listdir(HERE)):
        if name.startswith("answers_") and name.endswith(".json"):
            with open(os.path.join(HERE, name)) as fh:
                cases.append((name, json.load(fh)))
    bad = 0
    for name, ans in cases:
        want = ans.pop("_expect_pass")
        r = grade(ans, sites)
        ok = r["pass"] == want
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {name:<40} pass={r['pass']} (expected {want})"
              f"  loc={r['location']} q1={r['q1']} q2={r['q2']} q3={r['q3']}")
    return 1 if bad else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        return self_test()
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "answers.json")
    with open(path) as fh:
        ans = json.load(fh)
    r = grade(ans)
    report(r)
    if r["site"]:
        print("  matched:", r["site"])
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
