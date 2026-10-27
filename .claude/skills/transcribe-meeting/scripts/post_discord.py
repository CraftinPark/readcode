"""Post a meeting's decisions and action items to Discord through a channel webhook.

The message is built from the notes file's "## Decided" and "## Action items"
sections (Discord doesn't render tables, so rows become bullets); the notes and
the transcript go along as attachments. Without --send it only prints the message.

    python post_discord.py NOTES.md [TRANSCRIPT.md] [--send]

The webhook URL comes from READCODE_DISCORD_WEBHOOK (never commit it).
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# section -> how many table columns to keep (None = all); decisions keep only their text
SECTIONS = {"Decided": 1, "Action items": None}
LIMIT = 2000  # Discord's cap on message content


def section(md: str, title: str) -> list[str]:
    m = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", md, re.M | re.S)
    return m.group(1).strip().splitlines() if m else []


def bullets(lines: list[str], keep: int | None = None) -> list[str]:
    out, header_seen = [], False
    for line in lines:
        if not line.startswith("|"):
            if line.strip():
                out.append(line.strip())
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not header_seen:  # first row of a table is its header
            header_seen = True
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        # Keep a "#" column as the bullet's number so "see #5" still points somewhere.
        marker = "-"
        if cells and cells[0].isdigit():
            marker, cells = f"{cells[0]}.", cells[1:]
        cells = [c for c in cells[:keep] if c]
        if cells:
            out.append(f"{marker} " + " · ".join(cells))
    return out


def build_message(notes: Path) -> str:
    md = notes.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", md, re.M)
    parts = [f"**{title.group(1) if title else notes.stem}**"]
    for name, keep in SECTIONS.items():
        rows = bullets(section(md, name), keep)
        if rows:
            parts.append(f"\n__{name}__\n" + "\n".join(rows))
    msg = "\n".join(parts)
    tail = "\n… (full notes attached)"
    if len(msg) > LIMIT:
        msg = msg[: LIMIT - len(tail)].rsplit("\n", 1)[0] + tail
    return msg


def post(url: str, content: str, files: list[Path]) -> None:
    boundary = uuid.uuid4().hex
    body = bytearray()

    def field(headers: str, data: bytes) -> None:
        body.extend(f"--{boundary}\r\n{headers}\r\n\r\n".encode())
        body.extend(data + b"\r\n")

    payload = {"content": content, "allowed_mentions": {"parse": []}}
    field('Content-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json',
          json.dumps(payload).encode())
    for i, f in enumerate(files):
        field(f'Content-Disposition: form-data; name="files[{i}]"; filename="{f.name}"\r\n'
              "Content-Type: text/markdown", f.read_bytes())
    body.extend(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(url, data=bytes(body), method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "ReadCode-meeting-notes (local script, 1.0)",  # Discord rejects urllib's default
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"posted ({resp.status})", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("notes", type=Path)
    ap.add_argument("transcript", type=Path, nargs="?")
    ap.add_argument("--send", action="store_true", help="actually post; default prints only")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # the Windows console default can't print "·"

    content = build_message(args.notes)
    files = [args.notes] + ([args.transcript] if args.transcript else [])
    print(content)
    print(f"\n[{len(content)} chars; attachments: {', '.join(f.name for f in files)}]", file=sys.stderr)
    if not args.send:
        return 0
    url = os.environ.get("READCODE_DISCORD_WEBHOOK", "")
    if not re.fullmatch(r"https://(ptb\.|canary\.)?discord(app)?\.com/api/webhooks/\d+/[\w-]+", url.strip()):
        print("READCODE_DISCORD_WEBHOOK is not a full Discord webhook URL (.../api/webhooks/<id>/<token>)",
              file=sys.stderr)
        return 1
    try:
        post(url.strip(), content, files)
    except urllib.error.HTTPError as e:
        print(f"Discord refused the post: {e.code} {e.read().decode('utf-8', 'replace')[:300]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
