"""Grade one task (incident ticket, PR review, trace) out of 100.

Deterministic parts are decided here: did the candidate point at the cause,
pick the right verdict, pick the right option. Only the written explanation
and fix go to the judge (judge_task), which scores them 0..1.

    parts      each part's weight (exact): multiple choice, or selected lines within 3 lines of the answer
    incident   locate 40 + mechanism 40 + fix 20   (mechanism and fix count only if located)
    review_pr  verdict 50 + reasons 50              (reasons count only with the right verdict)
    trace      option 100                           (a wrong option reports the misread it is built on)
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .matcher import _near

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
_task_v = Draft202012Validator(json.loads((SCHEMAS / "task-submission.schema.json").read_text(encoding="utf-8")),
                               format_checker=FormatChecker())


class TaskError(Exception):
    pass


def is_task_submission(sub):
    return "task_id" in sub


def grade_task(example_dir, sub, judge):
    ex = Path(example_dir)
    public = json.loads((ex / "public.json").read_text(encoding="utf-8"))
    key = json.loads((ex / "key.json").read_text(encoding="utf-8"))
    errs = [f"[{'/'.join(map(str, e.path)) or '(root)'}] {e.message}" for e in _task_v.iter_errors(sub)]
    if errs:
        raise TaskError("; ".join(errs[:5]))
    if (sub["exercise_id"], sub["exercise_version"]) != (public["id"], public["version"]):
        raise TaskError(f"submission is for {sub['exercise_id']} v{sub['exercise_version']}, not {public['id']} v{public['version']}")
    ptask = next((t for t in public.get("tasks", []) if t["id"] == sub["task_id"]), None)
    ktask = next((t for t in key.get("tasks", []) if t["task_id"] == sub["task_id"]), None)
    if ptask is None or ktask is None:
        raise TaskError(f"{public['id']} has no task {sub['task_id']}")
    if sub["task_type"] != ktask["type"]:
        raise TaskError(f"{sub['task_id']} is a {ktask['type']} task, not {sub['task_type']}")

    parts, feedback = {}, None
    if "part_answers" in ktask:
        # Multiple choice (SAT style): exact, no judge. Wrong picks report the misread
        # that option was built on, never the right answer.
        chosen = sub.get("answers", {})
        misreads = []
        # Line parts: right if any selected range is within 3 lines of the answer, in the same file.
        for pid, ranges in ktask.get("part_locations", {}).items():
            hit = any(_near(c, k, tol=3) for c in sub["locations"] for k in ranges)
            parts[pid] = float(ktask["part_weights"][pid]) if hit else 0.0
            if not hit:
                misreads.append(f"{pid}: " + ("the cause is not in the lines you selected; follow the symptom back through the code"
                                              if sub["locations"] else "no lines selected"))
        for pid, right in ktask["part_answers"].items():
            ok = chosen.get(pid) == right
            parts[pid] = float(ktask["part_weights"][pid]) if ok else 0.0
            if not ok and chosen.get(pid):
                misreads.append(f"{pid}: {ktask['distractors'].get(f'{pid}.{chosen[pid]}', 'not this one')}")
            elif not ok:
                misreads.append(f"{pid}: not answered")
        feedback = "; ".join(misreads) or None
    elif ktask["type"] == "incident":
        bugs = [b for b in key["bugs"] if b["id"] in ktask["answer_bug_ids"]]
        located = any(_near(c, k) for c in sub["locations"] for b in bugs for k in b["locations"])
        j = judge.judge_task({"type": "incident", "explanation": sub.get("explanation", ""), "fix": sub.get("fix", ""),
                              "anchors": [a for b in bugs for a in b["mechanism_anchors"] + [b["title"]]],
                              "fix_key": " ".join(b["fix"] for b in bugs)})
        parts = {"locate": 40.0 if located else 0.0,
                 "mechanism": round(40 * j["explanation"], 1) if located else 0.0,
                 "fix": round(20 * j["fix"], 1) if located else 0.0}
        if not located:
            feedback = "The cause is not in the lines you pointed at. Follow the symptom back through the code path it describes."
    elif ktask["type"] == "review_pr":
        right = sub.get("verdict") == ktask["verdict"]
        j = judge.judge_task({"type": "review_pr", "explanation": sub.get("explanation", ""), "fix": "",
                              "anchors": ktask["anchors"], "fix_key": ""})
        parts = {"verdict": 50.0 if right else 0.0, "reasons": round(50 * j["explanation"], 1) if right else 0.0}
        if not right:
            feedback = ("This PR has a problem you approved." if ktask["has_defect"]
                        else "This PR is correct; requesting changes would block a good fix.")
    else:
        right = sub.get("option") == ktask["correct_option"]
        parts = {"option": 100.0 if right else 0.0}
        if not right:
            feedback = f"Option {sub.get('option')} {ktask['distractors'].get(sub.get('option'), 'is not right')}."

    total = round(sum(parts.values()), 1)
    return {"exercise_id": public["id"], "task_id": sub["task_id"], "task_type": ktask["type"],
            "candidate_id": sub["candidate_id"], "judge": judge.name, "score": total, "max": 100,
            "parts": parts, "feedback": feedback}
