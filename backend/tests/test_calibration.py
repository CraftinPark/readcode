"""Calibration: does the grader rank weak < mid < strong candidates on readcode-003?

The fixtures in fixtures/calibration are written answers at three levels (see
docs/calibration.md). These tests pin what the grader does with them today.
The xfail tests are known gaps of FakeJudge (word overlap): they should start
passing once a real judge is plugged in, and strict=True makes that visible.
"""
import json
from pathlib import Path

import pytest

from grader import FakeJudge, grade
from grader.task import grade_task

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "examples" / "readcode-003"
CAL = Path(__file__).parent / "fixtures" / "calibration"


def load(name):
    return json.loads((CAL / f"readcode-003-{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reviews():
    return {lvl: grade(EX, load(lvl), FakeJudge()) for lvl in ("weak", "mid", "strong")}


def test_full_review_ranks_the_levels(reviews):
    assert reviews["weak"]["total"] < reviews["mid"]["total"] < reviews["strong"]["total"]
    assert reviews["strong"]["total"] >= 85
    assert reviews["weak"]["total"] <= 15


def test_strong_finds_every_bug_and_weak_misses_the_failure_mode_bug(reviews):
    assert [f["bug_id"] for f in reviews["strong"]["bugs_found"]] == ["B1", "B2", "B3", "B4"]
    assert "B1" not in {f["bug_id"] for f in reviews["weak"]["bugs_found"]}
    assert "B1" not in {f["bug_id"] for f in reviews["mid"]["bugs_found"]}


def test_pointing_at_a_red_herring_is_penalized_not_credited(reviews):
    # weak flags the 60 s takeover in claim(), which sits in the same function as B2.
    weak = reviews["weak"]
    assert [fp["comment_id"] for fp in weak["false_positives"]] == ["c1"]
    assert "B2" not in {f["bug_id"] for f in weak["bugs_found"]}
    # mid confidently calls the refund reservation a bug, in different words than the key.
    assert [fp["comment_id"] for fp in reviews["mid"]["false_positives"]] == ["c3"]
    assert reviews["mid"]["penalties"] == 2.0


@pytest.mark.xfail(strict=True, reason="FakeJudge scores short paraphrased answers near zero; a real judge should put mid at 40-70")
def test_mid_lands_in_the_middle(reviews):
    assert 40 <= reviews["mid"]["total"] <= 70


@pytest.mark.parametrize("task,expected", [
    ("T1", {"weak": 0, "mid": (40, 70), "strong": (90, 100)}),   # incident: wrong place / right place, wrong cause / full
    ("T5", {"weak": 0, "mid": 0, "strong": (90, 100)}),          # PR review: mid and weak approve a subtly wrong fix
    ("T7", {"weak": 0, "mid": 100, "strong": 100}),              # trace
])
def test_tasks(task, expected):
    for lvl, want in expected.items():
        r = grade_task(EX, load(f"{task}-{lvl}"), FakeJudge())
        lo, hi = want if isinstance(want, tuple) else (want, want)
        assert lo <= r["score"] <= hi, (task, lvl, r)


def test_task_feedback_names_the_misread_without_the_answer():
    r = grade_task(EX, load("T7-weak"), FakeJudge())
    assert r["overconfident"] is True
    assert "saved response is already there" in r["feedback"]
    r = grade_task(EX, load("T1-weak"), FakeJudge())
    assert r["score"] == 0 and "not in the lines you pointed at" in r["feedback"]
