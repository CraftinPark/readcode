#!/usr/bin/env python3
"""Assemble a file the way a 2020-era student did with a chat assistant:
paste each answer's code into the file without ever showing the assistant
the whole file, and without cleaning anything up.

Rules, applied in order to every ```python block of every reply:
  - A block that creates the app (`app = Flask(`) and is at least 60% the size
    of the current file replaces the whole file ("I just pasted the new one").
  - Import lines not already in the file are added after the existing imports.
  - Each top-level chunk (decorators + def/class, or a statement) whose name is
    already in the file replaces the old one; new chunks go before
    `if __name__ == "__main__":` (or at the end).
Nothing is deduplicated beyond exact name matches, reformatted or fixed.

Usage: python tools/vibe_assemble.py REPLIES_DIR OUT_FILE
       (REPLIES_DIR holds step1.md, step2.md, ... : the raw replies)
"""
import re
import sys
from pathlib import Path

def python_blocks(text):
    """The ```python / ```py blocks of a reply, read fence by fence (other languages are skipped)."""
    blocks, inside, lang, cur = [], False, "", []
    for line in text.splitlines():
        fence = line.strip().startswith("```")
        if fence and not inside:
            inside, lang, cur = True, line.strip()[3:].strip().lower(), []
        elif fence and inside:
            first = next((l.strip() for l in cur if l.strip()), "")
            # a template mislabelled as python: the reply tells the student to save it as a .html file
            if lang in ("python", "py") and not first.startswith(("<", "{%", "{{")):
                blocks.append("\n".join(cur) + "\n")
            inside = False
        elif inside:
            cur.append(line)
    return blocks


def chunks(code):
    """Split code into top-level chunks: [(name or None, text)]."""
    out, cur, name = [], [], None
    for line in code.splitlines():
        top = line and not line[0].isspace() and not line.startswith(("#", ")", "]", "}"))
        starts_def = top and re.match(r"(@|def |class |async def )", line)
        if top and (starts_def or not (cur and cur[-1].startswith("@"))):
            if cur and not (cur[-1].startswith("@") and starts_def):
                out.append((name, "\n".join(cur)))
                cur, name = [], None
        cur.append(line)
        m = re.match(r"(?:async )?(?:def|class) (\w+)", line)
        if m:
            name = m.group(1)
    if cur:
        out.append((name, "\n".join(cur)))
    return out


def apply(current, block):
    if "app = Flask(" in block and len(block) >= 0.6 * len(current):
        return block.rstrip() + "\n"
    lines = current.splitlines()
    imports = [l for l in block.splitlines() if re.match(r"(import |from \S+ import )", l)]
    last_import = max((i for i, l in enumerate(lines) if re.match(r"(import |from \S+ import )", l)), default=-1)
    for imp in imports:
        if imp not in lines:
            lines.insert(last_import + 1, imp)
            last_import += 1
    current = "\n".join(lines) + "\n"
    for name, text in chunks(block):
        if not text.strip() or re.match(r"(import |from \S+ import )", text.strip()):
            continue
        if name:
            pat = re.compile(r"(?ms)^((?:@[^\n]*\n)*)(?:async )?(?:def|class) " + re.escape(name) + r"\b.*?(?=^\S|\Z)")
            if pat.search(current):
                current = pat.sub(lambda _: text.rstrip() + "\n\n", current, count=1)
                continue
        main = current.find('if __name__ == "__main__":')
        if main == -1:
            main = current.find("if __name__ == '__main__':")
        insert = text.rstrip() + "\n\n\n"
        current = current[:main] + insert + current[main:] if main != -1 else current.rstrip() + "\n\n\n" + insert
    return current


def assemble(replies_dir):
    current = ""
    for step in sorted(Path(replies_dir).glob("step*.md"), key=lambda p: int(re.search(r"\d+", p.stem).group())):
        blocks = python_blocks(step.read_text(encoding="utf-8"))
        if not current and blocks:
            current = max(blocks, key=len).rstrip() + "\n"
            blocks = [b for b in blocks if b.rstrip() + "\n" != current]
        for b in blocks:
            current = apply(current, b)
    return current


if __name__ == "__main__":
    Path(sys.argv[2]).write_text(assemble(sys.argv[1]), encoding="utf-8")
    print(f"wrote {sys.argv[2]}")
