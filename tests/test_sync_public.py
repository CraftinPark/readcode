"""The frontend copy of the examples must never contain grading content."""
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("sync_public", ROOT / "tools" / "sync_public.py")
sp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sp)


def test_only_public_files_are_copied(tmp_path):
    out = tmp_path / "out"
    index = sp.sync(ROOT / "examples", out)
    pubs = {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "examples").glob("*/public.json"))}
    assert [e["id"] for e in index] == sorted(pubs)
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    expected = ["index.json"] + [f"{ex}/public.json" for ex in pubs] + [f"{ex}/code/{f['path']}" for ex, pub in pubs.items() for f in pub["files"]]
    assert files == sorted(expected)
    assert {e["id"]: e["in_mvp"] for e in index}["readcode-001"] is False
    assert all(e["in_mvp"] for e in index if e["id"] != "readcode-001")


def test_key_content_never_reaches_the_frontend(tmp_path):
    out = tmp_path / "out"
    sp.sync(ROOT / "examples", out)
    blob = "".join(p.read_text(encoding="utf-8") for p in out.rglob("*.json"))
    for key_path in (ROOT / "examples").glob("*/key.json"):
        key = json.loads(key_path.read_text(encoding="utf-8"))
        for b in key["bugs"]:
            assert b["description"] not in blob and b["fix"] not in blob
        for t in key.get("tasks", []):
            for answer in t.get("anchors", []) + list(t.get("distractors", {}).values()):
                assert answer not in blob


def test_stray_files_in_code_are_not_copied(tmp_path):
    examples = tmp_path / "examples"
    shutil.copytree(ROOT / "examples" / "readcode-001", examples / "readcode-001")
    (examples / "readcode-001" / "code" / "answers.txt").write_text("B1 is in evict_tail")
    out = tmp_path / "out"
    sp.sync(examples, out)
    assert not (out / "readcode-001" / "code" / "answers.txt").exists()
