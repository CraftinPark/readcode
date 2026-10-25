#!/usr/bin/env python3
"""Analyse a study: does the score rise with experience, and which questions work?

Re-grades every bundle from the keys (so results never depend on what was
stored), then reports against the success criteria written before collecting:
  - scores rise with level, seniors at least 1 SD above new grads
  - each question separates the top third of scorers from the bottom third
  - internal consistency (Cronbach's alpha) >= 0.7, per form
People who say they used AI or web search are excluded and counted.

Usage:
  python tools/analyze_study.py pilot-1 --bundles DIR [--out report.md]
  python tools/analyze_study.py pilot-1 --db backend/.data/study.db [--out report.md]
"""
import argparse, json, sqlite3, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from grader import FakeJudge  # noqa: E402
from grader.task import grade_task  # noqa: E402
from study import level_of, load_study  # noqa: E402

YEARS_MID = {"0-1": 0.5, "2-5": 3.5, "6-10": 8.0, "10+": 12.0}
LEVEL_ORDER = ["new grad", "mid", "senior"]


def load_bundles(study_id, bundles=None, db=None):
    if bundles:
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(bundles).glob("*.json"))]
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT bundle FROM submissions WHERE study = ? ORDER BY received_ms", (study_id,)).fetchall()
    conn.close()
    return [json.loads(r[0]) for r in rows]


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def cronbach_alpha(matrix):
    """matrix: list of people, each a list of 0/1 item scores (same items)."""
    if len(matrix) < 3 or len(matrix[0]) < 2:
        return None
    k = len(matrix[0])
    item_vars = [statistics.pvariance([row[i] for row in matrix]) for i in range(k)]
    total_var = statistics.pvariance([sum(row) for row in matrix])
    return (k / (k - 1)) * (1 - sum(item_vars) / total_var) if total_var else None


def score_people(study, bundles):
    """-> people: [{code, form, level, years, percent, items: {item_id: 0/1}, picks: {item_id: option}, minutes: {task: m}}]"""
    people, excluded = [], []
    for b in bundles:
        if b["honesty"].get("used_ai") == "yes" or b["honesty"].get("used_search") == "yes":
            excluded.append(b["participant"])
            continue
        items, picks, minutes, got, most = {}, {}, {}, 0.0, 0.0
        for sub in b["tasks"]:
            r = grade_task(ROOT / "examples" / sub["exercise_id"], sub, FakeJudge())
            task_key = f"{sub['exercise_id']}:{sub['task_id']}"
            minutes[task_key] = sub.get("time_spent_minutes")
            got += r["score"]
            most += r["max"]
            for part, pts in r["parts"].items():
                item = f"{task_key}:{part}"
                items[item] = 1 if pts > 0 else 0
                chosen = (sub.get("answers") or {}).get(part) or (sub.get("option") if part == "option" else None)
                if chosen:
                    picks[item] = chosen
        people.append({"code": b["participant"], "form": b["form"], "level": level_of(b["survey"]),
                       "years": YEARS_MID.get(b["survey"].get("years")), "percent": 100 * got / most if most else 0,
                       "items": items, "picks": picks, "minutes": minutes})
    return people, excluded


def item_table(people):
    by_item = defaultdict(list)
    for p in people:
        for item, v in p["items"].items():
            by_item[item].append(p)
    rows = []
    for item, takers in sorted(by_item.items()):
        # Separation: rank takers by their score on everything else, compare top and bottom thirds.
        rest = sorted(takers, key=lambda p: sum(v for k, v in p["items"].items() if k != item))
        third = max(1, len(rest) // 3)
        bottom, top = rest[:third], rest[-third:]
        p_top = statistics.mean(p["items"][item] for p in top)
        p_bottom = statistics.mean(p["items"][item] for p in bottom)
        wrong = Counter(p["picks"][item] for p in takers if p["items"][item] == 0 and item in p["picks"])
        by_level = {lvl: [p["items"][item] for p in takers if p["level"] == lvl] for lvl in LEVEL_ORDER}
        task = item.rsplit(":", 1)[0]
        times = [p["minutes"][task] for p in takers if p["minutes"].get(task) is not None]
        p_all = statistics.mean(p["items"][item] for p in takers)
        flags = []
        if p_all > 0.9:
            flags.append("too easy")
        if p_all < 0.1:
            flags.append("too hard")
        if p_top - p_bottom < 0:
            flags.append("reversed: weaker people do better")
        elif p_top - p_bottom < 0.1:
            flags.append("does not separate")
        rows.append({"item": item, "n": len(takers), "p": p_all,
                     "by_level": {k: (statistics.mean(v) if v else None) for k, v in by_level.items()},
                     "separation": p_top - p_bottom, "median_minutes": statistics.median(times) if times else None,
                     "top_wrong": wrong.most_common(1)[0] if wrong else None, "flags": flags})
    return rows


def fast_correct(people):
    """People who got a whole task right in under a quarter of its median time: worth a look."""
    medians = defaultdict(list)
    for p in people:
        for task, m in p["minutes"].items():
            if m is not None:
                medians[task].append(m)
    medians = {t: statistics.median(v) for t, v in medians.items()}
    out = []
    for p in people:
        for task, m in p["minutes"].items():
            parts = [v for k, v in p["items"].items() if k.startswith(task + ":")]
            if m is not None and parts and all(parts) and m < 0.25 * medians[task]:
                out.append(f"{p['code']} on {task} ({m} min vs median {medians[task]:.1f})")
    return out


def analyze(study, people, excluded):
    levels = {lvl: [p["percent"] for p in people if p["level"] == lvl] for lvl in LEVEL_ORDER}
    med = {k: (statistics.median(v) if v else None) for k, v in levels.items()}
    ng, sr = levels["new grad"], levels["senior"]
    effect = None
    if len(ng) >= 2 and len(sr) >= 2:
        pooled = (((len(ng) - 1) * statistics.variance(ng) + (len(sr) - 1) * statistics.variance(sr)) / (len(ng) + len(sr) - 2)) ** 0.5
        effect = (statistics.mean(sr) - statistics.mean(ng)) / pooled if pooled else None
    dated = [p for p in people if p["years"] is not None]
    rho = spearman([p["years"] for p in dated], [p["percent"] for p in dated])
    alphas = {}
    for form in sorted(study["forms"]):
        group = [p for p in people if p["form"] == form]
        if group:
            items = sorted(set.intersection(*(set(p["items"]) for p in group)))
            alphas[form] = cronbach_alpha([[p["items"][i] for i in items] for p in group]) if items else None
    items = item_table(people)
    ordered = all(med[a] is not None and med[b] is not None and med[a] < med[b]
                  for a, b in zip(LEVEL_ORDER, LEVEL_ORDER[1:]))
    return {"n": len(people), "excluded": excluded, "medians": med, "counts": {k: len(v) for k, v in levels.items()},
            "effect_sd": effect, "spearman": rho, "alpha": alphas, "items": items, "fast": fast_correct(people),
            "criteria": {"levels ordered": ordered,
                         "seniors >= 1 SD above new grads": effect is not None and effect >= 1.0,
                         "every form alpha >= 0.7": bool(alphas) and all(a is not None and a >= 0.7 for a in alphas.values()),
                         "questions that separate": f"{sum(1 for r in items if r['separation'] >= 0.1)} of {len(items)}"}}


def answer_counts(study, bundles):
    """Share of people picking each option, for every choice question (everyone, excluded or not)."""
    out = []
    for where in ("survey", "honesty"):
        for q in study[where]:
            if q["type"] != "choice":
                continue
            c = Counter(b[where].get(q["id"]) for b in bundles if b[where].get(q["id"]))
            n = sum(c.values())
            out.append({"id": q["id"], "label": q["label"], "n": n,
                        "shares": [(o, c[o] / n if n else None) for o in q["options"]]})
    return out


def fmt(x, pct=False):
    if x is None:
        return "-"
    return f"{100 * x:.0f}%" if pct else f"{x:.2f}"


def report_md(study, a):
    m = a["medians"]
    lines = [f"# {study['title']}: analysis", "",
             f"**Headline:** seniors {fmt(m['senior'])}, mids {fmt(m['mid'])}, new grads {fmt(m['new grad'])} "
             f"(median % of points; n = {a['n']}); {a['criteria']['questions that separate']} questions separate levels; "
             f"consistency {', '.join(f'form {k} {fmt(v)}' for k, v in a['alpha'].items())}.", "",
             "## Success criteria (set before collecting)", ""]
    for k, v in a["criteria"].items():
        lines.append(f"- {k}: **{('yes' if v else 'no') if isinstance(v, bool) else v}**")
    lines += ["", "## Scores by level", "", "| Level | n | Median % |", "|---|---|---|"]
    for lvl in LEVEL_ORDER:
        lines.append(f"| {lvl} | {a['counts'][lvl]} | {fmt(m[lvl])} |")
    lines += ["", f"Seniors vs new grads: {fmt(a['effect_sd'])} standard deviations. "
                  f"Rank correlation, years of experience vs score: {fmt(a['spearman'])}.", "",
              f"Excluded (said they used AI or search): {len(a['excluded'])}" + (f" ({', '.join(a['excluded'])})" if a["excluded"] else ""), "",
              "## Questions", "",
              "| Question | n | Right | New grad | Mid | Senior | Separation | Median min | Most-picked wrong | Flags |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in a["items"]:
        bl = r["by_level"]
        wrong = f"{r['top_wrong'][0]} ({r['top_wrong'][1]})" if r["top_wrong"] else "-"
        lines.append(f"| {r['item']} | {r['n']} | {fmt(r['p'], True)} | {fmt(bl['new grad'], True)} | {fmt(bl['mid'], True)} | "
                     f"{fmt(bl['senior'], True)} | {fmt(r['separation'])} | {fmt(r['median_minutes'])} | {wrong} | {', '.join(r['flags']) or '-'} |")
    flagged = [r for r in a["items"] if r["flags"]]
    lines += ["", "## Drop or rewrite", ""] + ([f"- {r['item']}: {', '.join(r['flags'])}" for r in flagged] or ["- none"])
    lines += ["", "## Very fast perfect answers (check these)", ""] + ([f"- {x}" for x in a["fast"]] or ["- none"])
    lines += ["", "## Answers to the questions before and after", ""]
    for q in a.get("answers", []):
        lines.append(f"- {q['label']} (n = {q['n']}): " + ", ".join(f"{o} {fmt(s, True)}" for o, s in q["shares"]))
    lines += ["", "_With about 15 people per group only large differences show up. This is first evidence, not proof._", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("study")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--bundles")
    src.add_argument("--db")
    ap.add_argument("--out")
    a = ap.parse_args()
    study = load_study(a.study)
    bundles = load_bundles(a.study, a.bundles, a.db)
    people, excluded = score_people(study, bundles)
    result = analyze(study, people, excluded)
    result["answers"] = answer_counts(study, bundles)
    text = report_md(study, result)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
