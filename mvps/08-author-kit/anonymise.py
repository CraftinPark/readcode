"""Scrubs a submitted problem folder before anyone else sees it: company and product names you list,
plus emails, internal hostnames, IP addresses and internal URLs. Then lists what still looks like a name,
for a human (or an LLM QA pass) to check.

    python anonymise.py SRC_DIR OUT_DIR --names names.txt

names.txt: one `RealName=Replacement` per line (e.g. `Acme Pay=Payments Co`).
"""
import argparse
import os
import re
import shutil

PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "person@example.com"),
    (re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b"), "10.0.0.1"),
    (re.compile(r"https?://[\w.-]*(internal|corp|intra|local)[\w./?=&-]*", re.I), "https://internal.example"),
    (re.compile(r"\b[\w-]+\.(corp|internal|intra)\b", re.I), "service.internal.example"),
]
CAPWORD = re.compile(r"\b[A-Z][a-z]+[A-Z]\w*\b|\b[A-Z]{3,}\b")   # CamelCase or ACRONYMS: often product/team names
TEXT = (".py", ".md", ".txt", ".toml", ".json", ".yaml", ".yml", ".ini", ".sql", ".c", ".h", ".js", ".ts")


def scrub(text, names):
    for real, fake in names:
        text = re.sub(re.escape(real), fake, text, flags=re.I)
    for pat, fake in PATTERNS:
        text = pat.sub(fake, text)
    return text


def run(src, out, names_file):
    names = []
    if names_file:
        for line in open(names_file, encoding="utf-8"):
            if "=" in line:
                real, fake = line.rstrip("\n").split("=", 1)
                names.append((real.strip(), fake.strip()))
        names.sort(key=lambda x: -len(x[0]))
    shutil.rmtree(out, ignore_errors=True)
    suspects = {}
    for root, _, files in os.walk(src):
        for n in files:
            s = os.path.join(root, n)
            if names_file and os.path.abspath(s) == os.path.abspath(names_file):
                continue   # the list of real names must never ship
            d = os.path.join(out, scrub(os.path.relpath(s, src), names))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            if not n.endswith(TEXT):
                shutil.copy(s, d)
                continue
            text = scrub(open(s, encoding="utf-8", errors="replace").read(), names)
            open(d, "w", encoding="utf-8").write(text)
            for w in CAPWORD.findall(text):
                suspects.setdefault(w, set()).add(os.path.relpath(d, out))
    print(f"scrubbed {src} -> {out}")
    if suspects:
        print("still check these (could be names):")
        for w, where in sorted(suspects.items()):
            print(f"  {w}: {', '.join(sorted(where))}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--names")
    a = ap.parse_args()
    run(a.src, a.out, a.names)
