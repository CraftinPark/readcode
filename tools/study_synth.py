#!/usr/bin/env python3
"""Synthetic study participants, to test the analysis before real people take part.

Each simulated person has an ability by level (new grad < mid < senior) and
answers each scored part with a 2-parameter logistic model:
    P(right) = 1 / (1 + exp(-a * (ability - difficulty)))
Wrong answers pick a wrong option (or lines in the wrong place). --bad-item
makes one part answered right more often by weaker people, so the analysis
should flag it.

Usage: python tools/study_synth.py pilot-1 OUT_DIR [--per-level 15] [--seed 1] [--bad-item EXERCISE:TASK:PART]
"""
import argparse, json, math, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from study import form_for, load_study  # noqa: E402

ABILITY = {"0-1": -0.9, "2-5": 0.0, "6-10": 0.9, "10+": 1.1}
LEVEL_FOR_YEARS = {"0-1": "new grad / junior", "2-5": "mid", "6-10": "senior", "10+": "staff or above"}


def task_parts(exercise, task_id):
    pub = json.loads((ROOT / "examples" / exercise / "public.json").read_text(encoding="utf-8"))
    key = json.loads((ROOT / "examples" / exercise / "key.json").read_text(encoding="utf-8"))
    t = next(x for x in pub["tasks"] if x["id"] == task_id)
    k = next(x for x in key["tasks"] if x["task_id"] == task_id)
    return pub, t, k


def answer(rng, pub, t, k, ability, minutes_est, bad_parts):
    sub = {"schema_version": 1, "exercise_id": pub["id"], "exercise_version": pub["version"], "task_id": t["id"],
           "task_type": t["type"], "candidate_id": "synthetic", "submitted_at": "2026-11-01T12:00:00Z",
           "time_spent_minutes": round(max(0.5, rng.lognormvariate(math.log(minutes_est), 0.35) * (1.15 - 0.1 * ability)), 1),
           "locations": []}

    def right(item, difficulty):
        p = 1 / (1 + math.exp(-1.6 * (ability - difficulty)))
        if item in bad_parts:
            p = 1 - p                      # reversed: weaker people do better
        return rng.random() < p

    if t.get("parts"):
        sub["answers"] = {}
        for i, part in enumerate(t["parts"]):
            item = f"{pub['id']}:{t['id']}:{part['id']}"
            difficulty = {"easy": -1.0, "medium": 0.0, "hard": 0.7}[pub["difficulty"]] + 0.3 * (i - 1)
            ok = right(item, difficulty)
            if part.get("select"):
                target = k["part_locations"][part["id"]][0]
                sub["locations"] = [target] if ok else [{"file": pub["files"][0]["path"], "start_line": 1, "end_line": 2}]
            else:
                correct = k["part_answers"][part["id"]]
                wrong = [o["id"] for o in part["options"] if o["id"] != correct]
                sub["answers"][part["id"]] = correct if ok else rng.choice(wrong)
    else:                                   # trace: a single multiple-choice option
        item = f"{pub['id']}:{t['id']}:option"
        ok = right(item, -0.3)
        wrong = [o["id"] for o in t["options"] if o["id"] != k["correct_option"]]
        sub["option"] = k["correct_option"] if ok else rng.choice(wrong)
        sub["explanation"] = "synthetic"
    return sub


def make(study_id, out, per_level=15, seed=1, bad_items=()):
    rng = random.Random(seed)
    study = load_study(study_id)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for years in ("0-1", "2-5", "6-10"):
        for _ in range(per_level):
            n += 1
            code = f"syn{n:03d}"
            ability = rng.gauss(ABILITY[years], 0.55)
            form = form_for(study, code)
            tasks = []
            for entry in study["forms"][form]:
                pub, t, k = task_parts(entry["exercise"], entry["task"])
                tasks.append(answer(rng, pub, t, k, ability, max(5, pub["estimated_minutes"] * 0.6), set(bad_items)))
            bundle = {"schema_version": 1, "study_id": study_id, "participant": code, "form": form,
                      "order": [f"{e['exercise']}:{e['task']}" for e in study["forms"][form]],
                      "consent_at": "2026-11-01T11:00:00Z", "started_at": "2026-11-01T11:00:00Z",
                      "finished_at": "2026-11-01T12:20:00Z",
                      "survey": {"years": years, "level": LEVEL_FOR_YEARS[years], "on_call": "yes" if years != "0-1" else "no",
                                 "python": str(rng.choice([3, 4, 5])), "seen_saleor": "no", "company_type": "other company"},
                      "honesty": {"used_ai": "yes" if rng.random() < 0.05 else "no", "used_search": "no", "interrupted": "no"},
                      "tasks": tasks}
            (out / f"{code}.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("study")
    ap.add_argument("out")
    ap.add_argument("--per-level", type=int, default=15)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--bad-item", action="append", default=[])
    a = ap.parse_args()
    print(f"wrote {make(a.study, a.out, a.per_level, a.seed, a.bad_item)} synthetic participants to {a.out}")


if __name__ == "__main__":
    main()
