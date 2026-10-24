"""Study mode: bundle validation, grading and storage, and the analysis on synthetic people."""
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from playground import create_playground_app
from study import Store, fnv1a, form_for, load_study

ROOT = Path(__file__).resolve().parents[2]


def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


synth, analysis = tool("study_synth"), tool("analyze_study")
STUDY = load_study("pilot-1")


@pytest.fixture(scope="module")
def bundles(tmp_path_factory):
    out = tmp_path_factory.mktemp("synth")
    synth.make("pilot-1", out, per_level=15, seed=3, bad_items=["readcode-006:T1:why"])
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("*.json"))]


def test_fnv1a_matches_the_frontend_reference_values():
    # The same values are asserted in frontend/src/lib/lib.test.ts.
    assert [fnv1a(c) for c in ["p01", "syn001", "alice-7", ""]] == [723412596, 3238330556, 2566655595, 2166136261]
    assert form_for(STUDY, "p01") in STUDY["forms"]


def test_analysis_recovers_the_level_ordering_and_flags_the_broken_question(bundles):
    people, excluded = analysis.score_people(STUDY, bundles)
    a = analysis.analyze(STUDY, people, excluded)
    assert a["criteria"]["levels ordered"] and a["criteria"]["seniors >= 1 SD above new grads"]
    assert a["spearman"] > 0.5
    assert all(v is not None for v in a["alpha"].values())
    flags = {r["item"]: r["flags"] for r in a["items"]}
    assert "reversed: weaker people do better" in flags["readcode-006:T1:why"]
    md = analysis.report_md(STUDY, a)
    assert md.startswith("# ") and "Drop or rewrite" in md and "readcode-006:T1:why" in md


def test_people_who_used_ai_are_excluded(bundles):
    b = json.loads(json.dumps(bundles[0]))
    b["honesty"]["used_ai"] = "yes"
    people, excluded = analysis.score_people(STUDY, [b, *bundles[1:]])
    assert b["participant"] in excluded and b["participant"] not in {p["code"] for p in people}


def test_alpha_and_spearman_on_known_values():
    assert analysis.cronbach_alpha([[1, 1], [0, 0], [1, 1], [0, 0]]) == pytest.approx(1.0)
    assert analysis.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert analysis.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("READCODE_STUDY_ADMIN_KEY", "organiser")
    return TestClient(create_playground_app(Store(tmp_path / "study.db")))


def test_submission_is_graded_stored_and_reported(client, bundles):
    r = client.post("/api/study/pilot-1/submissions", json=bundles[0])
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["participant"] == bundles[0]["participant"] and 0 <= report["percent"] <= 100
    assert {t["exercise"] for t in report["tasks"]} == {s["exercise_id"] for s in bundles[0]["tasks"]}
    assert all("skills" in t and "parts" in t for t in report["tasks"])
    assert "answers" not in json.dumps(report)                       # no answers or keys go back
    assert client.post("/api/study/pilot-1/submissions", json=bundles[0]).status_code == 409


def test_comparison_appears_once_there_are_enough_peers(client, bundles):
    for b in bundles[:12]:
        last = client.post("/api/study/pilot-1/submissions", json=b).json()
    assert last["comparison"]["peers_total"] == 11 and "percentile" in last["comparison"]


def test_bad_bundles_are_rejected(client, bundles):
    wrong_form = {**bundles[1], "form": "B" if bundles[1]["form"] == "A" else "A"}
    assert "Wrong form" in client.post("/api/study/pilot-1/submissions", json=wrong_form).json()["detail"]
    no_consent = {**bundles[1], "consent_at": None}
    assert "Consent" in client.post("/api/study/pilot-1/submissions", json=no_consent).json()["detail"]
    missing_task = {**bundles[1], "tasks": bundles[1]["tasks"][:-1]}
    assert "do not match" in client.post("/api/study/pilot-1/submissions", json=missing_task).json()["detail"]
    bad_survey = {**bundles[1], "survey": {**bundles[1]["survey"], "years": "forty"}}
    assert client.post("/api/study/pilot-1/submissions", json=bad_survey).status_code == 400
    assert client.post("/api/study/nope/submissions", json=bundles[1]).status_code == 400


def test_export_and_delete_need_the_organiser_key(client, bundles):
    client.post("/api/study/pilot-1/submissions", json=bundles[2])
    assert client.get("/api/study/pilot-1/export").status_code == 403
    exported = client.get("/api/study/pilot-1/export", headers={"Authorization": "Bearer organiser"}).json()
    assert [b["participant"] for b in exported] == [bundles[2]["participant"]]
    code = bundles[2]["participant"]
    assert client.delete(f"/api/study/pilot-1/submissions/{code}", headers={"Authorization": "Bearer organiser"}).status_code == 200
    assert client.get("/api/study/pilot-1/export", headers={"Authorization": "Bearer organiser"}).json() == []
