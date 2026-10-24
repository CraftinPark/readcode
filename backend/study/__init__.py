"""Study mode: store and grade a participant's whole session.

A study (studies/<id>/study.json) lists forms of tasks. Each participant code is
assigned one form by a hash both the browser and this module compute (fnv1a).
At the end the browser sends one bundle: consent, background survey, every task
submission, and the honesty questions. We validate it, grade each task with the
exact task grader (no judge needed for multiple choice and selected lines),
store it, and return the participant's personal report.

Answers and keys never go back to the browser; the report has scores and the
bug patterns ("skills") each task was about.
"""
import json
import os
import sqlite3
import statistics
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException

from grader import FakeJudge
from grader.task import TaskError, grade_task

ROOT = Path(__file__).resolve().parents[2]
STUDIES = ROOT / "studies"
EXAMPLES = ROOT / "examples"
DEFAULT_DB = ROOT / "backend" / ".data" / "study.db"
MIN_PEERS = 5          # don't compare with a group smaller than this
LEVELS = {"0-1": "new grad", "2-5": "mid", "6-10": "senior", "10+": "senior"}


class BundleError(Exception):
    pass


def fnv1a(text: str) -> int:
    """32-bit FNV-1a; frontend/src/lib/study.ts computes the same value."""
    h = 0x811C9DC5
    for b in text.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def load_study(study_id: str) -> dict:
    p = STUDIES / study_id / "study.json"
    if not p.is_file():
        raise BundleError(f"No such study: {study_id}")
    return json.loads(p.read_text(encoding="utf-8"))


def form_for(study: dict, participant: str) -> str:
    names = sorted(study["forms"])
    return names[fnv1a(participant) % len(names)]


def level_of(survey: dict) -> str:
    return LEVELS.get(survey.get("years", ""), "unknown")


def _check_answers(questions: list[dict], answers: dict, where: str) -> None:
    for q in questions:
        v = answers.get(q["id"])
        if q.get("required") and not v:
            raise BundleError(f"{where}: '{q['id']}' is required")
        if v and q["type"] == "choice" and v not in q["options"]:
            raise BundleError(f"{where}: '{v}' is not an option for '{q['id']}'")


def validate_bundle(study: dict, b: dict) -> None:
    if b.get("schema_version") != 1 or b.get("study_id") != study["id"]:
        raise BundleError("This bundle is not for this study.")
    code = b.get("participant", "")
    if not (3 <= len(code) <= 40) or not code.replace("-", "").replace("_", "").isalnum():
        raise BundleError("Participant codes are 3-40 letters, digits, - or _.")
    if b.get("form") != form_for(study, code):
        raise BundleError("Wrong form for this participant code.")
    if not b.get("consent_at"):
        raise BundleError("Consent is required.")
    _check_answers(study["survey"], b.get("survey", {}), "survey")
    _check_answers(study["honesty"], b.get("honesty", {}), "honesty")
    want = sorted((t["exercise"], t["task"]) for t in study["forms"][b["form"]])
    got = sorted((s.get("exercise_id"), s.get("task_id")) for s in b.get("tasks", []))
    if got != want:
        raise BundleError("The tasks do not match this participant's form.")


def _task_info(exercise: str, task_id: str) -> tuple[str, list[str]]:
    pub = json.loads((EXAMPLES / exercise / "public.json").read_text(encoding="utf-8"))
    key = json.loads((EXAMPLES / exercise / "key.json").read_text(encoding="utf-8"))
    task = next(t for t in pub["tasks"] if t["id"] == task_id)
    ktask = next(t for t in key["tasks"] if t["task_id"] == task_id)
    skills = sorted({s for bug in key["bugs"] if bug["id"] in ktask.get("answer_bug_ids", []) for s in bug["skills"]})
    first_sentence = task["text"].split(". ")[0].rstrip(".")
    title = task["text"].split(":")[0] if task["type"] == "incident" else first_sentence[:90]
    return f"{pub['title']} ({title})", skills


def grade_bundle(b: dict) -> dict:
    tasks = []
    for sub in b["tasks"]:
        try:
            r = grade_task(EXAMPLES / sub["exercise_id"], sub, FakeJudge())
        except TaskError as e:
            raise BundleError(f"{sub.get('exercise_id')} {sub.get('task_id')}: {e}")
        title, skills = _task_info(sub["exercise_id"], sub["task_id"])
        tasks.append({"exercise": sub["exercise_id"], "task": sub["task_id"], "title": title, "score": r["score"],
                      "max": r["max"], "parts": r["parts"], "skills": skills,
                      "minutes": sub.get("time_spent_minutes")})
    got = sum(t["score"] for t in tasks)
    most = sum(t["max"] for t in tasks)
    return {"participant": b["participant"], "form": b["form"], "level": level_of(b["survey"]),
            "percent": round(100 * got / most, 1) if most else 0.0, "tasks": tasks}


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("READCODE_STUDY_DB", DEFAULT_DB))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._conn()
        conn.execute("CREATE TABLE IF NOT EXISTS submissions (study TEXT NOT NULL, participant TEXT NOT NULL, "
                     "received_ms INTEGER NOT NULL, bundle TEXT NOT NULL, report TEXT NOT NULL, "
                     "PRIMARY KEY (study, participant))")
        conn.close()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, study_id, bundle, report) -> bool:
        conn = self._conn()
        try:
            with conn:
                conn.execute("INSERT INTO submissions VALUES (?, ?, ?, ?, ?)",
                             (study_id, bundle["participant"], int(time.time() * 1000), json.dumps(bundle), json.dumps(report)))
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def reports(self, study_id) -> list[dict]:
        conn = self._conn()
        rows = conn.execute("SELECT report FROM submissions WHERE study = ?", (study_id,)).fetchall()
        conn.close()
        return [json.loads(r["report"]) for r in rows]

    def bundles(self, study_id) -> list[dict]:
        conn = self._conn()
        rows = conn.execute("SELECT bundle FROM submissions WHERE study = ? ORDER BY received_ms", (study_id,)).fetchall()
        conn.close()
        return [json.loads(r["bundle"]) for r in rows]

    def delete(self, study_id, participant) -> bool:
        conn = self._conn()
        with conn:
            n = conn.execute("DELETE FROM submissions WHERE study = ? AND participant = ?", (study_id, participant)).rowcount
        conn.close()
        return n > 0


def compare(report: dict, others: list[dict]) -> dict:
    """How this participant compares with others at the same level (if there are enough)."""
    same = [o["percent"] for o in others if o["level"] == report["level"] and o["participant"] != report["participant"]]
    everyone = [o["percent"] for o in others if o["participant"] != report["participant"]]
    out = {"level": report["level"], "peers_at_level": len(same), "peers_total": len(everyone)}
    if len(same) >= MIN_PEERS:
        out["level_median"] = statistics.median(same)
    if len(everyone) >= MIN_PEERS:
        out["percentile"] = round(100 * sum(p < report["percent"] for p in everyone) / len(everyone))
    return out


def create_router(store: Store | None = None) -> APIRouter:
    router = APIRouter()
    store = store or Store()
    admin_key = os.environ.get("READCODE_STUDY_ADMIN_KEY")

    def staff(authorization: str):
        if not admin_key or authorization != f"Bearer {admin_key}":
            raise HTTPException(403, "Study organisers only (set READCODE_STUDY_ADMIN_KEY).")

    @router.post("/api/study/{study_id}/submissions")
    def submit(study_id: str, bundle: dict):
        try:
            study = load_study(study_id)
            validate_bundle(study, bundle)
            report = grade_bundle(bundle)
        except BundleError as e:
            raise HTTPException(400, str(e))
        if not store.add(study_id, bundle, report):
            raise HTTPException(409, "This participant code has already submitted.")
        return {**report, "comparison": compare(report, store.reports(study_id))}

    @router.get("/api/study/{study_id}/export")
    def export(study_id: str, authorization: str = Header(default="")):
        staff(authorization)
        return store.bundles(study_id)

    @router.delete("/api/study/{study_id}/submissions/{participant}")
    def delete(study_id: str, participant: str, authorization: str = Header(default="")):
        staff(authorization)
        if not store.delete(study_id, participant):
            raise HTTPException(404, "No submission for that code.")
        return {"deleted": participant}

    return router
