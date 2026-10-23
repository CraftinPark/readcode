"""Multiple-choice (SAT-style) tasks built from real Saleor bugs: graded exactly, no judge."""
import json
from pathlib import Path

import pytest

from grader import FakeJudge
from grader.task import TaskError, grade_task

ROOT = Path(__file__).resolve().parents[2]


def submission(ex, answers, task="T1"):
    return {"schema_version": 1, "exercise_id": ex, "exercise_version": 1, "task_id": task, "task_type": "incident",
            "candidate_id": "t", "submitted_at": "2026-10-22T12:00:00Z", "time_spent_minutes": 5,
            "locations": [], "answers": answers}


def key_answers(ex):
    key = json.loads((ROOT / "examples" / ex / "key.json").read_text(encoding="utf-8"))
    return key["tasks"][0]["part_answers"]


@pytest.mark.parametrize("ex", ["readcode-004", "readcode-005", "readcode-006"])
def test_right_answers_score_100(ex):
    r = grade_task(ROOT / "examples" / ex, submission(ex, key_answers(ex)), FakeJudge())
    assert r["score"] == 100 and r["feedback"] is None


@pytest.mark.parametrize("ex", ["readcode-004", "readcode-005", "readcode-006"])
def test_every_wrong_option_scores_zero_for_its_part_and_explains_the_misread(ex):
    pub = json.loads((ROOT / "examples" / ex / "public.json").read_text(encoding="utf-8"))
    right = key_answers(ex)
    for part in pub["tasks"][0]["parts"]:
        for opt in part["options"]:
            if opt["id"] == right[part["id"]]:
                continue
            r = grade_task(ROOT / "examples" / ex, submission(ex, {**right, part["id"]: opt["id"]}), FakeJudge())
            assert r["parts"][part["id"]] == 0
            assert r["score"] < 100
            assert r["feedback"].startswith(f"{part['id']}: ") and "not this one" not in r["feedback"]


def test_partial_credit_follows_the_part_weights():
    ans = {**key_answers("readcode-006"), "fix": "a"}          # right place and cause, wrong fix
    assert grade_task(ROOT / "examples" / "readcode-006", submission("readcode-006", ans), FakeJudge())["score"] == 80


def test_missing_answers_score_zero_not_an_error():
    r = grade_task(ROOT / "examples" / "readcode-004", submission("readcode-004", {}), FakeJudge())
    assert r["score"] == 0 and "where: not answered" in r["feedback"]


def test_confidence_is_no_longer_accepted():
    sub = {**submission("readcode-004", key_answers("readcode-004")), "confidence": "certain"}
    with pytest.raises(TaskError):
        grade_task(ROOT / "examples" / "readcode-004", sub, FakeJudge())
