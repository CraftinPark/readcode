"""Builds the flash-sale oversell problem inside a bigger codebase, with the "start with tickets/worker.py"
hint and the file table removed. The player gets one repo and has to decide where to look.

    python build.py                       # out/ = flash-sale tickets service + the marketplace backend
    python build.py --extra PATH/TO/REPO  # also copy a real permissive codebase in as surrounding code (e.g. Saleor, BSD-3)

Reads the flash-sale problem from the danny-problem-for-john branch (git show), so the working tree is not touched.
"""
import argparse
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BRANCH = "danny-problem-for-john"
FLASH = "problems/flash-sale-oversell"
MARKET = os.path.join(REPO, "examples", "_sources", "market", "code")


def git_show(path):
    return subprocess.run(["git", "show", f"{BRANCH}:{path}"], cwd=REPO, capture_output=True, text=True, check=True).stdout


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        f.write(text)


def readme(original):
    """Keep the ticket, on-call's findings and the questions; drop the code tour and the hint."""
    head = original.split("## The code")[0]
    questions = "## Questions" + original.split("## Questions")[1].split("## Afterwards")[0]
    head = head.replace("*A ReadCode problem. Backend, about 30 minutes. Made by Danny for John.*",
                        "*A ReadCode problem. Backend, about 45 minutes. Big-repo variant: no starting hint.*")
    code = ("## The code\n\nThis is the whole backend monorepo. The ticket service is in here somewhere, next to the "
            "marketplace and everything else. Nobody will tell you where to start.\n\n"
            "Run the flash-sale replay with `python simulate.py` (Python 3.10+, no packages).\n\n")
    return head + code + questions


def build(extra=None):
    out = os.path.join(HERE, "out")
    shutil.rmtree(out, ignore_errors=True)
    files = subprocess.run(["git", "ls-tree", "-r", "--name-only", BRANCH, FLASH], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    for f in files:
        rel = os.path.relpath(f, FLASH)
        text = git_show(f)
        write(os.path.join(out, "README.md" if rel == "README.md" else rel), readme(text) if rel == "README.md" else text)
    for root, _, names in os.walk(MARKET):
        for n in names:
            if n.endswith((".py", ".ini")) or n == "README.md":
                src = os.path.join(root, n)
                rel = os.path.relpath(src, MARKET)
                dst = os.path.join(out, "market_service", rel) if rel != "README.md" else os.path.join(out, "market_service", "README.md")
                write(dst, open(src, encoding="utf-8").read())
    if extra:
        shutil.copytree(extra, os.path.join(out, "vendor", os.path.basename(extra.rstrip("/\\"))),
                        ignore=shutil.ignore_patterns(".git", "node_modules", "*.png", "*.jpg"))
    lines = 0
    for root, _, names in os.walk(out):
        for n in names:
            if n.endswith(".py"):
                lines += sum(1 for _ in open(os.path.join(root, n), encoding="utf-8", errors="ignore"))
    print(f"built {out}: {lines} lines of Python")
    if lines < 10000:
        print(f"  {10000 - lines} lines short of the ~10,000 target: pass --extra with a real permissive codebase")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra")
    build(ap.parse_args().extra)
