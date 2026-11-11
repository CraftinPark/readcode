"""HIDDEN engine for ml-4-grasp-drop. Never ship this file to a player.

Ground truth and rubric: see _key/README.md.
"""
import random

# ---------------------------------------------------------------- the world
DAYS = ["Fri 23", "Sat 24", "Sun 25", "Mon 26", "Tue 27", "Wed 28", "Thu 29*"]
END = 480            # the case runs Thu 09:00 -> 17:00 (minutes after 09:00)
CLAM_RAMP = 180      # 12:00 a new customer's clamshell SKUs ramp at every site
REFURB = 240         # 13:00 Reno brings 12 refurbished older-camera robots online
PICKS_PER_MIN = 5    # per robot
MAX_ACTIONS = 40
EXPERT_FIX_MIN = 55
SLO_CELL, SLO_FLEET = 0.90, 0.93

BASE_CELLS = {("columbus", "A"): 60, ("reno", "A"): 12, ("reno", "B"): 68,
              ("leipzig", "B"): 70, ("osaka", "B"): 50}
SITES = ["columbus", "reno", "leipzig", "osaka"]
REVS = ["A", "B"]

# (model, camera_rev, resize) -> (success on other SKUs %, success on clamshells %)
RATES = {
    ("v41", "A", "center_crop"): (94.6, 82.0), ("v41", "A", "letterbox"): (80.2, 70.0),
    ("v41", "B", "any"): (94.6, 82.0),
    ("v42", "A", "center_crop"): (78.5, 68.0), ("v42", "A", "letterbox"): (95.3, 93.5),
    ("v42", "B", "any"): (95.3, 93.5),
    ("v43", "A", "center_crop"): (80.5, 70.5), ("v43", "A", "letterbox"): (94.7, 92.0),
    ("v43", "B", "any"): (94.7, 92.0),
}
CONF = {("v41", "A", "center_crop"): 0.86, ("v41", "A", "letterbox"): 0.64, ("v41", "B", "any"): 0.86,
        ("v42", "A", "center_crop"): 0.57, ("v42", "A", "letterbox"): 0.88, ("v42", "B", "any"): 0.88,
        ("v43", "A", "center_crop"): 0.60, ("v43", "A", "letterbox"): 0.87, ("v43", "B", "any"): 0.87}
FAMILY_OFFSET = {"rigid_box": 1.4, "polybag": -0.9, "deformable": -2.6}
FAMILY_MIX = {"rigid_box": 0.45, "polybag": 0.30, "deformable": 0.20, "clamshell": 0.05}


def cells_at(t):
    c = dict(BASE_CELLS)
    if t >= REFURB:
        c[("reno", "A")] += 12
    return c


def clam_share(t):
    return 0.25 if t >= CLAM_RAMP else 0.05


def rate(model, rev, resize, clam):
    key = (model, rev, "any" if rev == "B" else resize)
    other, cl = RATES[key]
    return ((1 - clam) * other + clam * cl) / 100


def _noise(*parts, size=0.3):
    return random.Random(":".join(map(str, parts))).uniform(-size, size)


def parse_selector(sel):
    """'all' | 'site=reno' | 'camera_rev=A' | 'site=reno,camera_rev=A' -> dict or None."""
    if sel == "all":
        return {}
    out = {}
    for part in sel.split(","):
        if "=" not in part:
            return None
        k, v = part.split("=", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "site" and v.lower() in SITES:
            out["site"] = v.lower()
        elif k in ("camera_rev", "rev") and v.upper() in REVS:
            out["camera_rev"] = v.upper()
        else:
            return None
    return out


def matches(sel, site, rev):
    s = parse_selector(sel)
    return s is not None and s.get("site", site) == site and s.get("camera_rev", rev) == rev


def state_at(changes, t):
    routes, resize, paused = [("all", "v42")], "center_crop", []
    for eff, kind, val in changes:
        if eff > t:
            continue
        if kind == "route":
            routes.append(val)
        elif kind == "resize":
            resize = val
        elif kind == "pause":
            paused.append(val)
        elif kind == "resume":
            paused = [] if val == "all" else [p for p in paused if p != val]
    return routes, resize, paused


def model_for(routes, site, rev):
    m = None
    for sel, model in routes:
        if matches(sel, site, rev):
            m = model
    return m


def minute(changes, t):
    """Per-cell picture of the fleet at minute t (t < 0 means before 09:00 today, same as 09:00)."""
    t = max(t, 0)
    routes, resize, paused = state_at(changes, t)
    clam = clam_share(t)
    out = {}
    for (site, rev), n in cells_at(t).items():
        model = model_for(routes, site, rev)
        is_paused = any(matches(p, site, rev) for p in paused)
        out[(site, rev)] = {"robots": n, "model": model, "paused": is_paused,
                            "rate": rate(model, rev, resize, clam),
                            "conf": CONF[(model, rev, "any" if rev == "B" else resize)]}
    return out, resize


def slo_ok(changes, t):
    cells, _ = minute(changes, t)
    if any(c["paused"] for c in cells.values()):
        return False
    tot = sum(c["robots"] for c in cells.values())
    fleet = sum(c["robots"] * c["rate"] for c in cells.values()) / tot
    return fleet >= SLO_FLEET and all(c["rate"] >= SLO_CELL for c in cells.values())


def day_cost(changes, until=END):
    """Failed grasps (and half a failure per pick lost to paused robots) from 09:00 to `until`."""
    fails = lost = 0.0
    for t in range(until):
        cells, _ = minute(changes, t)
        for c in cells.values():
            picks = c["robots"] * PICKS_PER_MIN
            if c["paused"]:
                lost += picks
            else:
                fails += picks * (1 - c["rate"])
    return fails, lost


IDEAL = [(0, "resize", "letterbox")]
EXPERT = [(EXPERT_FIX_MIN, "route", ("camera_rev=A", "v41"))]


def excess(changes):
    f, l = day_cost(changes)
    fi, _ = day_cost(IDEAL)
    return f + 0.5 * l - fi


# ---------------------------------------------------------------- history (Fri..Thu 09:00)
def _day_mix(day, site):
    """[(share of day, model)] the cell ran on that day. Serving resize was center_crop all week."""
    if day in DAYS[:4]:
        return [(1.0, "v41")]
    if day == "Tue 27":
        return [(10 / 24, "v42"), (14 / 24, "v41")] if site == "leipzig" else [(1.0, "v41")]
    if day == "Wed 28":
        return [(1.0, "v42")] if site == "leipzig" else [(15 / 24, "v42"), (9 / 24, "v41")]
    return [(1.0, "v42")]


def _hist_cells(day):
    """(site, rev, robots, [(share, model, success, conf)])"""
    rows = []
    for (site, rev), n in BASE_CELLS.items():
        mix = [(s, m, rate(m, rev, "center_crop", 0.05), CONF[(m, rev, "any" if rev == "B" else "center_crop")])
               for s, m in _day_mix(day, site)]
        rows.append((site, rev, n, mix))
    return rows


def _agg(rows, key_fn, val_fn):
    num, den = {}, {}
    for site, rev, n, mix in rows:
        for share, model, succ, conf in mix:
            k = key_fn(site, rev, model)
            if k is None:
                continue
            w = n * share
            num[k] = num.get(k, 0) + w * val_fn(site, rev, model, succ, conf)
            den[k] = den.get(k, 0) + w
    return {k: num[k] / den[k] for k in num}, den


METRICS = {
    "grasp_success": ("% of grasp attempts that succeed", ["site", "camera_rev", "model", "sku_family", "gripper"]),
    "picks": ("grasp attempts per day", ["site", "camera_rev", "model"]),
    "drops": ("items dropped mid-move per day", ["site", "camera_rev"]),
    "model_confidence": ("mean top grasp score from the model", ["site", "camera_rev", "model"]),
    "cycle_time_s": ("seconds per pick cycle", ["site"]),
    "input_hue_deg": ("mean hue of camera frames, degrees", ["site", "camera_rev"]),
    "input_brightness": ("mean brightness of camera frames, 0-255", ["site", "camera_rev"]),
    "robot_uptime": ("% of shift robots were picking", ["site"]),
    "gripper_faults": ("gripper fault events per day", ["site", "gripper"]),
}


def history(metric, dim):
    """Rows of (label, [value per day]) for the dashboard."""
    groups = {"site": SITES, "camera_rev": REVS, "model": ["v41", "v42"],
              "sku_family": list(FAMILY_MIX), "gripper": ["suction", "two_finger"], None: ["fleet"]}[dim]
    table = []
    for g in groups:
        vals = []
        for d in DAYS:
            rows = _hist_cells(d)
            hours = 9 if d.endswith("*") else 24
            if dim == "site":
                key = lambda s, r, m, g=g: "x" if s == g else None
            elif dim == "camera_rev":
                key = lambda s, r, m, g=g: "x" if r == g else None
            elif dim == "model":
                key = lambda s, r, m, g=g: "x" if m == g else None
            else:
                key = lambda s, r, m: "x"
            if metric == "grasp_success":
                if dim == "sku_family":
                    def v(s, r, m, succ, conf, g=g):
                        if g == "clamshell":
                            return RATES[(m, r, "any" if r == "B" else "center_crop")][1] / 100
                        return RATES[(m, r, "any" if r == "B" else "center_crop")][0] / 100 + FAMILY_OFFSET[g] / 100
                else:
                    v = lambda s, r, m, succ, conf: succ
                a, den = _agg(rows, key, v)
                off = {"suction": -0.3, "two_finger": 0.6}.get(g, 0) if dim == "gripper" else 0
                vals.append("-" if "x" not in a else f"{100 * a['x'] + off + _noise(metric, d, g):.1f}%")
            elif metric in ("picks", "drops"):
                a, den = _agg(rows, key, lambda s, r, m, succ, conf: succ)
                if "x" not in a:
                    vals.append("-")
                    continue
                picks = den["x"] * 300 * hours * 0.82
                v = picks if metric == "picks" else picks * (1 - a["x"]) * 0.34
                vals.append(f"{int(v * (1 + _noise(metric, d, g, size=0.01))):,}")
            elif metric == "model_confidence":
                a, _ = _agg(rows, key, lambda s, r, m, succ, conf: conf)
                vals.append("-" if "x" not in a else f"{a['x'] + _noise(metric, d, g, size=0.004):.3f}")
            elif metric == "cycle_time_s":
                base = {"columbus": 6.2, "reno": 6.0, "leipzig": 5.8, "osaka": 6.1}[g]
                if g == "columbus" and d in ("Wed 28", "Thu 29*"):
                    base -= 0.35 if d.endswith("*") else 0.27
                vals.append(f"{base + _noise(metric, d, g, size=0.05):.2f}")
            elif metric == "input_hue_deg":
                if dim == "camera_rev":
                    base = {"A": 29.0, "B": 30.5}[g] + (1.6 if g == "B" and d in ("Wed 28", "Thu 29*") else 0)
                else:
                    base = {"columbus": 29.0, "reno": 30.2, "leipzig": 30.8, "osaka": 31.0}[g]
                    if g == "osaka" and d in ("Wed 28", "Thu 29*"):
                        base += 6.2 if d.endswith("*") else 4.3
                vals.append(f"{base + _noise(metric, d, g, size=0.4):.1f}")
            elif metric == "input_brightness":
                base = {"columbus": 121, "reno": 128, "leipzig": 133, "osaka": 126, "A": 122, "B": 130}[g]
                vals.append(f"{base + _noise(metric, d, g, size=2):.0f}")
            elif metric == "robot_uptime":
                vals.append(f"{82 + _noise(metric, d, g, size=1.5):.1f}%")
            elif metric == "gripper_faults":
                base = {"suction": 14, "two_finger": 9}.get(g, 23)
                vals.append(f"{int(base + 4 * _noise(metric, d, g, size=1))}")
        table.append((g, vals))
    return table


# ---------------------------------------------------------------- changes, docs, people
CHANGES = {
    "CH-3288": ("Fri 23 10:05", "wms", "deploy v86: pick-list sort by aisle"),
    "CH-3290": ("Fri 23 15:10", "ml-serving", "deploy grasp-serving 2.14: metrics labels"),
    "CH-3293": ("Fri 23 16:40", "vision-tools", "deploy labeling UI 1.9"),
    "CH-3296": ("Sat 24 11:00", "site-ops", "Leipzig: weekend lighting schedule"),
    "CH-3298": ("Mon 26 08:50", "fleet-mgr", "deploy v51: battery swap scheduling"),
    "CH-3301": ("Mon 26 09:40", "labeling", "data refresh 2026-10-26: +18k clamshell frames annotated by new vendor LabelForge"),
    "CH-3303": ("Mon 26 10:30", "wms", "config: pick_batch_max 12 -> 16"),
    "CH-3307": ("Mon 26 11:20", "ml-data", "dataset loader: unify image resize with the export tool"),
    "CH-3310": ("Mon 26 22:10", "ml-train", "train grasp model v42 on refresh 2026-10-26"),
    "CH-3309": ("Tue 27 08:15", "feature-store", "backfill object_dims for the SKU catalogue (schema v3)"),
    "CH-3311": ("Tue 27 10:00", "hardware", "gripper controller 2.3.1 (two-finger grippers), all sites"),
    "CH-3312": ("Tue 27 14:00", "ml-serving", "roll out grasp model v42 (canary Leipzig Tue, rest of fleet Wed 09:00)"),
    "CH-3314": ("Tue 27 17:30", "analytics", "deploy: new shift report"),
    "CH-3315": ("Wed 28 07:30", "hardware", "camera firmware 4.1 (auto white balance retune), Osaka robots"),
    "CH-3318": ("Wed 28 08:30", "site-ops", "Columbus: conveyor speed 0.8 -> 0.9 m/s"),
    "CH-3321": ("Wed 28 16:00", "wms", "deploy v88: pick-list batching"),
    "CH-3324": ("Thu 29 06:30", "site-ops", "Reno: aisle 3 vacuum pump service"),
}
CHANGE_DETAIL = {
    "CH-3301": "LabelForge annotated 18,012 new clamshell frames (0.9% of the 1.9M-frame refresh). The rest of the refresh "
               "is self-labelled from grasp outcomes as usual. Owner: labeling team.",
    "CH-3307": "ml-data PR #1182: 'Dataset loader: use the export tool's resize_to_square (letterbox, pad value 114) "
               "instead of the loader's own implementation, so training and dataset export agree.' Touches "
               "ml-data/loader/transforms.py only. Reviewed and merged by the ml-data team. Owner: ml-data.",
    "CH-3309": "Backfilled object_dims for 41k SKUs. Read by the pallet planner and the WMS. Owner: feature-store team.",
    "CH-3310": "Job train-v42: refresh 2026-10-26, pipeline ml-data@4be1, 64 GPU-h. Offline eval 95.2% (v41: 94.0%).",
    "CH-3311": "Two-finger gripper controller: smoother close profile. Suction grippers untouched. Owner: hardware.",
    "CH-3312": "Model registry rollout. Tue 14:00 Leipzig 100% (canary). Wed 09:00 all sites 100%. Canary gate: Leipzig "
               "success >= 94.0% for 12 h -> passed (95.3%). Owner: ml-serving (you).",
    "CH-3315": "Camera firmware 4.1 on Osaka's 50 robots: retuned auto white balance for the new LED lights. Staged: "
               "Leipzig next week. Owner: hardware team.",
    "CH-3318": "Columbus conveyor 0.8 -> 0.9 m/s for the holiday ramp. Owner: Columbus site ops.",
}
MODEL_CARDS = {
    "v41": "grasp model v41 (registered Mon 12 Oct)\n  trained on refresh 2026-10-11 (1.7M frames), pipeline ml-data@91c0\n"
           "  input 384x384 RGB, colour jitter + small crops during training\n  offline eval 94.0% (eval split of the same refresh)\n"
           "  known weak spot: clamshell packaging (82% in eval)",
    "v42": "grasp model v42 (registered Mon 26 Oct 23:40)\n  trained on refresh 2026-10-26 (1.9M frames), pipeline ml-data@4be1\n"
           "  input 384x384 RGB, colour jitter + small crops during training\n  offline eval 95.2% (eval split of the same refresh)\n"
           "  clamshell packaging 93.5% in eval",
    "v43": "grasp model v43 (your retrain)\n  trained on the last fleet days, pipeline ml-data@4be1, self-labelled by grasp outcome\n"
           "  offline eval 94.9% (eval split of the same refresh)",
}
TEAMS = {
    "hardware": "Hardware team: \"Firmware 4.1 is on Osaka only so far. It retunes white balance; frames look warmer. "
                "We checked picks at Osaka and they look normal. We'd rather not roll back without evidence; Leipzig is next week.\"",
    "ml-data": "ml-data team: \"#1182 swapped our own resize helper for the export tool's resize_to_square so training and "
               "the exported datasets agree. It only changed the training loader. Every model trained since Mon uses it.\"",
    "labeling": "Labeling lead: \"LabelForge's first batch had a 6% disagreement rate on our audit, a bit above the incumbent's 3%. "
                "Only the 18k clamshell frames were theirs.\"",
    "feature-store": "Feature-store team: \"The object_dims backfill only feeds the pallet planner and WMS. The grasp model doesn't read it.\"",
    "site-ops": "Site ops coordinator: \"Columbus sped its conveyor up Wed 08:30 for the holiday ramp. Reno's aisle 3 (the older "
                "robots) had a pump service this morning. Nothing else this week.\"",
    "ml-platform": "ML platform: \"Training cluster is free. A full retrain is about 4 h and ~$3,800 of GPU. Registry and routing "
                   "are healthy.\"",
}
SITE_REPORTS = {
    "columbus": "Columbus ops lead: \"Drops went way up yesterday morning, right around when we sped the conveyor up. "
                "Arms hesitate, then grab the edge of the tote. Can the model handle 0.9 m/s?\"",
    "reno": "Reno ops lead: \"Mostly fine. A handful of the older units in aisle 3 have been clumsy since yesterday, "
            "and we just had their pumps serviced. We're bringing 12 refurbished units of the same older model online at 13:00 for the peak.\"",
    "leipzig": "Leipzig ops lead: \"No complaints. Clamshells got noticeably better since Tuesday.\"",
    "osaka": "Osaka ops lead: \"Hardware updated our cameras Wednesday; the debug view looks warmer. Picks look normal to us.\"",
}
CAMERAS = {"A": "rev A (older units): 1280x720 colour, wide-angle lens", "B": "rev B: 1024x1024 colour, square ROI"}

MECHANISMS = {
    "A": "Noisy labels from the new annotation vendor taught v42 wrong grasp points",
    "B": "The camera firmware update shifted frame colours, so the model misreads objects",
    "C": "Training and serving now resize frames differently, so some robots feed inputs the model never learned",
    "D": "The feature-store backfill wrote wrong object sizes, so grasps are planned for the wrong size",
    "E": "The faster conveyor moves items during the grasp, so the arm closes on empty space",
    "F": "Worn suction cups and vacuum pumps on the older robots lose grip mid-move",
    "G": "v42 overfit to the new clamshell data and got worse on every other kind of item",
    "H": "Nothing is broken: this week's item mix is harder than usual",
}
SEGMENTS = ["camera rev A robots", "camera rev B robots", "Columbus site", "Reno site", "Leipzig site", "Osaka site",
            "clamshell SKUs", "suction grippers", "whole fleet"]
CORRECT = {"change": "CH-3307", "mechanism": "C", "segment": "camera rev A robots"}

ACTIONS = {
    "dash": (10, "dash <metric> [by <dim>]: daily dashboard, Fri..Thu 09:00 (no args: list metrics)"),
    "live": (10, "live [by site|camera_rev|model|cell]: grasp success over the last 30 minutes"),
    "changes": (5, "changes [team]: change log for the last 7 days"),
    "show": (10, "show <change-id | v41 | v42 | v43>: details of a change or a model card"),
    "config": (5, "config: current model routing and serving settings"),
    "inputs": (20, "inputs <site> <camera_rev>: pull sample frames and show what serving feeds the model"),
    "offline_eval": (30, "offline_eval <model> <center_crop|letterbox>: eval split by camera rev ($40 GPU)"),
    "labels_audit": (20, "labels_audit: label quality audit of the latest data refresh"),
    "ask_site": (20, "ask_site <site>: ask a site's ops lead what they see"),
    "page": (20, "page <team>: ask a team (hardware, ml-data, labeling, feature-store, site-ops, ml-platform)"),
    "route": (15, "route <selector> <model>: serve a model to some robots; selector: all | site=<s> | camera_rev=<A|B> | site=<s>,camera_rev=<r>"),
    "set_config": (15, "set_config <key> <value>: change a production setting (you own serving.*)"),
    "retrain": (10, "retrain [days]: launch a full retrain on recent fleet data (~4 h, ~$3,800 GPU)"),
    "firmware_rollback": (20, "firmware_rollback <site>: roll a site's cameras back to the previous firmware"),
    "pause": (10, "pause <selector>: stop robots picking (no failures, no picks)"),
    "resume": (10, "resume <selector|all>: restart paused robots"),
    "wait": (0, "wait <minutes>: let time pass (up to 120)"),
    "resolve": (5, "declare the incident resolved (you can't change production after this)"),
}
COMPUTE = {"offline_eval": 40, "retrain": 3800}
SERVING_KEYS = {"serving.resize_mode": ("center_crop", "letterbox"), "serving.batch_size": None,
                "serving.min_grasp_score": None}


def _table(header, rows):
    widths = [max(len(str(r[i])) for r in [header, *rows]) for i in range(len(header))]
    line = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    return "\n".join([line(header), line(["-" * w for w in widths]), *map(line, rows)])


def fmt(minute_):
    h, m = divmod(9 * 60 + int(minute_), 60)
    return f"{h:02d}:{m:02d}"


class Session:
    def __init__(self, seed=1):
        self.seed, self.minutes, self.compute = seed, 0, 0
        self.changes, self.log, self.harm, self.out_of_scope = [], [], [], []
        self.config = {"serving.resize_mode": "center_crop", "serving.batch_size": "8", "serving.min_grasp_score": "0.35"}
        self.v43_ready = None
        self.resolved_at = None
        self.live_checks = []          # minutes at which live was started
        self.done = None

    # ---- helpers
    def clock(self):
        return f"Thu {fmt(self.minutes)}"

    def status(self):
        f, l = day_cost(self.changes, min(self.minutes, END))
        state = "resolved (declared)" if self.resolved_at is not None else "open"
        return (f"Time: {self.clock()} ({self.minutes} min in, day ends 17:00). Actions: {len(self.log)}/{MAX_ACTIONS}. "
                f"GPU spent: ${self.compute:,}. Failed grasps today so far: {int(f):,}"
                + (f" (+{int(l):,} picks lost to paused robots)" if l else "") + f". Incident: {state}.")

    def act(self, name, args):
        if self.done:
            return "The case is closed."
        if name not in ACTIONS:
            return f"Unknown action '{name}'. Run: python case.py actions"
        if len(self.log) >= MAX_ACTIONS:
            return f"You've used all {MAX_ACTIONS} actions. Submit: python case.py submit ..."
        if self.minutes >= END:
            return "It's 17:00 and the shift is over. Submit: python case.py submit ..."
        if self.resolved_at is not None and name in ("route", "set_config", "retrain", "firmware_rollback",
                                                      "pause", "resume", "resolve"):
            return "You already declared the incident resolved. Submit your answer."
        start = self.minutes
        out = getattr(self, f"_a_{name}")(args)
        if out.startswith("ERROR:"):
            return out[7:]
        cost = self._wait if name == "wait" else ACTIONS[name][0]
        self.minutes = min(END, self.minutes + cost)
        self.compute += COMPUTE.get(name, 0)
        self.log.append((start, name, args))
        note = ""
        if self.v43_ready is not None and start < self.v43_ready <= self.minutes:
            note = "\n\n[ml-platform] Retrain finished: grasp model v43 is in the registry (offline eval 94.9%)."
        return f"{out}{note}\n\n[{cost} min] {self.status()}"

    def _effective(self, kind, val, cost):
        self.changes.append((self.minutes + cost, kind, val))

    # ---- looking
    def _a_dash(self, args):
        if not args:
            return "Metrics:\n" + "\n".join(f"  {k:<18} {d} (dims: {', '.join(dims)})" for k, (d, dims) in METRICS.items())
        metric, dim = args[0], None
        if metric not in METRICS:
            return f"ERROR: no metric '{metric}'. Run: python case.py do dash"
        if len(args) >= 3 and args[1] == "by":
            dim = args[2]
        elif len(args) == 2:
            dim = args[1]
        if dim and dim not in METRICS[metric][1]:
            return f"ERROR: '{metric}' has dims: {', '.join(METRICS[metric][1])}"
        rows = history(metric, dim)
        return (f"{metric} ({METRICS[metric][0]})" + (f" by {dim}" if dim else "") + "\n"
                + _table([dim or "", *DAYS], [[g, *v] for g, v in rows]) + "\n* Thu 00:00-09:00")

    def _a_live(self, args):
        dim = args[-1] if args else None
        if dim not in (None, "site", "camera_rev", "model", "cell"):
            return "ERROR: live [by site|camera_rev|model|cell]"
        self.live_checks.append(self.minutes)
        num, den, models = {}, {}, {}
        for t in range(self.minutes - 30, self.minutes):
            cells, _ = minute(self.changes, t)
            for (site, rev), c in cells.items():
                if c["paused"]:
                    k0 = {"site": site, "camera_rev": f"rev {rev}", "model": c["model"],
                          "cell": f"{site} / rev {rev}", None: "fleet"}[dim]
                    den.setdefault(k0, 0)
                    num.setdefault(k0, 0)
                    models.setdefault(k0, set()).add("paused")
                    continue
                k = {"site": site, "camera_rev": f"rev {rev}", "model": c["model"],
                     "cell": f"{site} / rev {rev}", None: "fleet"}[dim]
                p = c["robots"] * PICKS_PER_MIN
                num[k] = num.get(k, 0) + p * c["rate"]
                den[k] = den.get(k, 0) + p
                models.setdefault(k, set()).add(f"{c['model']} ({c['robots']} robots)" if dim == "cell" else c["model"])
        rows = []
        for k in sorted(den):
            pct = "paused" if not den[k] else f"{100 * num[k] / den[k] + _noise('live', self.seed, self.minutes, k, size=0.25):.1f}%"
            rows.append([k, f"{int(den[k]):,}", pct, ", ".join(sorted(models[k]))])
        return (f"Grasp success, {fmt(max(0, self.minutes - 30))}-{fmt(self.minutes)}" + (f" by {dim}" if dim else "") + "\n"
                + _table(["group", "attempts", "success", "serving"], rows) + "\nSLO: every site/camera group >= 90%, fleet >= 93%.")

    def _a_changes(self, args):
        items = [[c, w, s, t] for c, (w, s, t) in CHANGES.items() if not args or args[0] in (s, *t.lower().split())]
        return f"Changes, last 7 days ({len(items)})\n" + _table(["id", "when", "team", "summary"], items)

    def _a_show(self, args):
        k = (args or [""])[0]
        if k.lower() in MODEL_CARDS:
            if k.lower() == "v43" and (self.v43_ready is None or self.minutes < self.v43_ready):
                return "ERROR: no model v43 in the registry"
            return MODEL_CARDS[k.lower()]
        cid = k.upper()
        if cid not in CHANGES:
            return "ERROR: show <change-id | v41 | v42 | v43>"
        when, team, title = CHANGES[cid]
        return f"{cid}  {when}  {team}\n{title}\n{CHANGE_DETAIL.get(cid, 'No incidents linked.')}"

    def _a_config(self, args):
        routes, resize, paused = state_at(self.changes, self.minutes)
        pending = [c for c in self.changes if c[0] > self.minutes]
        lines = ["Model routing (later rules win):"] + [f"  {i + 1}. {sel:<28} -> {m}" for i, (sel, m) in enumerate(routes)]
        lines += ["Serving settings (grasp-serving 2.14, owner: you):"] + [f"  {k} = {v}" for k, v in self.config.items()]
        lines += [f"Paused: {', '.join(paused) if paused else 'none'}"]
        lines += [f"Fleet: {', '.join(f'{s} {r}:{n}' for (s, r), n in cells_at(self.minutes).items())} (site rev:robots)"]
        if pending:
            lines += ["Rolling out: " + "; ".join(f"{k} {v} at {fmt(e)}" for e, k, v in pending)]
        return "\n".join(lines)

    def _a_inputs(self, args):
        if len(args) < 2 or args[0].lower() not in SITES or args[1].upper() not in REVS:
            return "ERROR: inputs <site> <camera_rev>, e.g. inputs reno B"
        site, rev = args[0].lower(), args[1].upper()
        if (site, rev) not in BASE_CELLS:
            return f"ERROR: {site} has no rev {rev} robots"
        resize = state_at(self.changes, self.minutes)[1]
        cam = CAMERAS[rev]
        if rev == "B":
            geo = "1024x1024 -> 384x384, whole frame used (frame is already square)"
        elif resize == "center_crop":
            geo = ("1280x720 -> center_crop 720x720 -> 384x384; 280 px cut from each side "
                   "(tote edges and gripper fingers often outside the crop)")
        else:
            geo = "1280x720 -> letterbox to 1280x1280 (pad 114, grey bars top and bottom) -> 384x384; whole width kept"
        hue = 37.0 if site == "osaka" else 30.0
        return (f"Sample of 5 frames, {site} rev {rev} robots\n  camera: {cam}\n  serving.resize_mode = {resize}\n"
                f"  model input: {geo}\n  colour: mean hue {hue:.1f} deg, brightness {125 + (3 if rev == 'B' else -3)}, "
                "no clipping\n  frames look sharp; no dropped frames")

    def _a_offline_eval(self, args):
        if len(args) < 2 or args[0].lower() not in MODEL_CARDS or args[1] not in ("center_crop", "letterbox"):
            return "ERROR: offline_eval <v41|v42|v43> <center_crop|letterbox>"
        m, rs = args[0].lower(), args[1]
        if m == "v43" and (self.v43_ready is None or self.minutes < self.v43_ready):
            return "ERROR: no model v43 in the registry"
        rows = []
        for rev in REVS:
            o, c = RATES[(m, rev, "any" if rev == "B" else rs)]
            rows.append([f"rev {rev}", f"{o + _noise('ev', m, rs, rev, size=0.3):.1f}%", f"{c + _noise('evc', m, rs, rev, size=0.5):.1f}%"])
        return (f"Offline eval of {m}, eval split of refresh 2026-10-26, frames resized with {rs}\n"
                + _table(["camera", "all but clamshell", "clamshell"], rows))

    def _a_labels_audit(self, args):
        return _table(["source", "frames", "audited", "disagreement"], [
            ["self-labelled (grasp outcome)", "1,882,000", "2,000", "2.1%"],
            ["incumbent vendor (prior refreshes)", "-", "1,000", "3.2%"],
            ["LabelForge (clamshells only)", "18,012", "1,000", "6.1%"]])

    def _a_ask_site(self, args):
        s = (args or [""])[0].lower()
        if s not in SITE_REPORTS:
            return "ERROR: ask_site <columbus|reno|leipzig|osaka>"
        return SITE_REPORTS[s]

    def _a_page(self, args):
        t = (args or [""])[0].lower()
        if t not in TEAMS:
            return f"ERROR: page <{'|'.join(TEAMS)}>"
        return TEAMS[t]

    # ---- changing production
    def _a_route(self, args):
        if len(args) < 2 or parse_selector(args[0]) is None:
            return "ERROR: route <all | site=<s> | camera_rev=<A|B> | site=<s>,camera_rev=<r>> <model>"
        sel, model = args[0], args[1].lower()
        if model not in ("v41", "v42", "v43"):
            return "ERROR: models in the registry: v41, v42" + (", v43" if self.v43_ready and self.minutes >= self.v43_ready else "")
        if model == "v43" and (self.v43_ready is None or self.minutes < self.v43_ready):
            return "ERROR: no model v43 in the registry"
        self._effective("route", (sel, model), ACTIONS["route"][0])
        return f"Routing rule added: {sel} -> {model}. Live on matching robots at {fmt(self.minutes + 15)}."

    def _a_set_config(self, args):
        if len(args) < 2:
            return "ERROR: set_config <key> <value>"
        key, value = args[0], args[1]
        if not key.startswith("serving."):
            self.out_of_scope.append(f"set_config {key} (not yours)")
            return f"{key} = {value} pushed (owning team notified)."
        if key not in SERVING_KEYS:
            return f"ERROR: unknown setting {key}. Run: python case.py do config"
        allowed = SERVING_KEYS[key]
        if allowed and value not in allowed:
            return f"ERROR: {key} must be one of {', '.join(allowed)}"
        self.config[key] = value
        if key == "serving.resize_mode":
            self._effective("resize", value, ACTIONS["set_config"][0])
        return f"{key} = {value}. Live on every robot at {fmt(self.minutes + 15)} (applies to whatever model each robot runs)."

    def _a_retrain(self, args):
        if self.v43_ready is not None:
            return "ERROR: a retrain is already running or done"
        self.v43_ready = self.minutes + 10 + 240
        self.harm.append("launched a $3,800 full retrain during the incident, on fleet data self-labelled by the failing grasps")
        return (f"Job train-v43 launched: last {(args or ['3'])[0]} days of fleet grasps (self-labelled by outcome), "
                f"pipeline ml-data@4be1. ETA {fmt(self.v43_ready)}.")

    def _a_firmware_rollback(self, args):
        s = (args or [""])[0].lower()
        if s not in SITES:
            return "ERROR: firmware_rollback <site>"
        self.out_of_scope.append(f"rolled back {s} camera firmware (hardware team's)")
        self.harm.append(f"camera firmware rollback at {s} (robots reboot cameras, 10 min no picks)")
        return f"{s} cameras rolling back to the previous firmware."

    def _a_pause(self, args):
        if not args or parse_selector(args[0]) is None:
            return "ERROR: pause <selector>"
        self._effective("pause", args[0], ACTIONS["pause"][0])
        return f"Robots matching {args[0]} stop picking at {fmt(self.minutes + 10)}."

    def _a_resume(self, args):
        if not args or (args[0] != "all" and parse_selector(args[0]) is None):
            return "ERROR: resume <selector|all>"
        self._effective("resume", args[0], ACTIONS["resume"][0])
        return f"Robots matching {args[0]} resume at {fmt(self.minutes + 10)}."

    def _a_wait(self, args):
        try:
            n = int((args or [""])[0])
        except ValueError:
            return "ERROR: wait <minutes> (1-120)"
        if not 1 <= n <= 120:
            return "ERROR: wait <minutes> (1-120)"
        self._wait = n
        return f"You wait {n} minutes."

    def _a_resolve(self, args):
        self.resolved_at = self.minutes + ACTIONS["resolve"][0]
        return "Incident declared resolved. The shift runs on until 17:00; you'll see how it went when you submit."

    # ---- verdict
    def _first_ok_since(self, until):
        """Earliest minute m <= until such that the SLO held at every minute from m to until."""
        m = None
        for t in range(until, -1, -1):
            if slo_ok(self.changes, t):
                m = t
            else:
                break
        return m

    def _replay(self, start):
        rows, held, first_bad = [], True, None
        for t in range(start, END):
            if not slo_ok(self.changes, t):
                held = False
                first_bad = t if first_bad is None else first_bad
        marks = sorted({start, *range((start // 60 + 1) * 60, END, 60)})
        for t in marks:
            cells, _ = minute(self.changes, t)
            active = {k: c for k, c in cells.items() if not c["paused"]}
            tot = sum(c["robots"] for c in active.values()) or 1
            fleet = sum(c["robots"] * c["rate"] for c in active.values()) / tot
            worst = min(active.items(), key=lambda kv: kv[1]["rate"]) if active else None
            paused = sum(c["robots"] for c in cells.values() if c["paused"])
            rows.append([fmt(t), f"{100 * fleet:.1f}%",
                         f"{worst[0][0]} rev {worst[0][1]} {100 * worst[1]['rate']:.1f}% ({worst[1]['model']})" if worst else "-",
                         str(paused), "ok" if slo_ok(self.changes, t) else "BREACH"])
        events = []
        if start <= CLAM_RAMP:
            events.append("12:00 a new customer's clamshell SKUs ramp to 25% of picks at every site")
        if start <= REFURB:
            events.append("13:00 Reno brings 12 refurbished rev A robots online for the peak")
        return held, first_bad, rows, events

    def submit(self, answer):
        if self.done:
            return self.done
        a = {k: str(answer.get(k, "")).strip() for k in ("change", "mechanism", "segment")}
        seg = a["segment"]
        if seg.isdigit() and 1 <= int(seg) <= len(SEGMENTS):
            seg = SEGMENTS[int(seg) - 1]
        seg_l = seg.lower()
        diag = {"change": 8 if a["change"].upper() == "CH-3307" else 4 if a["change"].upper() in ("CH-3312", "CH-3310") else 0,
                "mechanism": 15 if a["mechanism"].upper() == "C" else 0,
                "segment": 7 if seg_l == "camera rev a robots" else 2 if seg_l in ("columbus site", "reno site") else 0}
        decl = self.resolved_at
        check_from = decl if decl is not None else min(END, self.minutes)
        held, first_bad, rows, events = self._replay(min(check_from, END - 1))
        ok_since = self._first_ok_since(min(check_from, END - 1)) if slo_ok(self.changes, min(check_from, END - 1)) else None

        ex, ex_exp = excess(self.changes), excess(EXPERT)
        ratio = ex / ex_exp if ex_exp else 1
        harm_pts = 15 if ratio <= 1.15 else 0 if ratio >= 3.5 else round(15 * (3.5 - ratio) / 2.35)
        cost_pts = max(0, min(10, round(10 - (self.compute - 150) / 300))) if self.compute > 150 else 10

        pen = []
        routes_all = [v for e, k, v in self.changes if k == "route"]
        if any(sel == "all" and m == "v41" for sel, m in routes_all):
            pen.append((8, "rolled the whole fleet back to v41 (v42 was better on the 72% of robots it worked for)"))
        elif any(parse_selector(sel) == {"site": "columbus"} and m == "v41" for sel, m in routes_all):
            pen.append((3, "scoped the rollback to a site rather than to what the robots had in common"))
        if self.v43_ready is not None:
            pen.append((8, "launched a full retrain mid-incident"))
        if any(m == "v43" for _, m in routes_all):
            pen.append((4, "shipped a model retrained on incident-period data"))
        if self.out_of_scope:
            pen.append((6, "changed things another team owns: " + "; ".join(self.out_of_scope)))
        broken = sum(1 for t in range(END) if any(c["model"] == "v41" and k[1] == "A" and r == "letterbox"
                                                  for cells, r in [minute(self.changes, t)] for k, c in cells.items()))
        if broken >= 30:
            pen.append((6, f"served v41 with a resize it wasn't trained on to rev A robots for {broken} min"))
        paused_min = sum(1 for t in range(END) if any(c["paused"] for c in minute(self.changes, t)[0].values()))
        if paused_min > 60:
            pen.append((4, f"kept robots paused for {paused_min} min"))
        if decl is None:
            pen.append((6, "never declared the incident resolved"))
        else:
            if not slo_ok(self.changes, min(decl, END - 1)):
                pen.append((10, f"declared resolved at {fmt(decl)}, while production was still breaching the SLO"))
            else:
                last_change = max([e for e, _, _ in self.changes if e <= decl] or [0])
                if not any(last_change <= m < decl for m in self.live_checks):
                    pen.append((4, "declared resolved without checking live numbers after the last change took effect"))
                if ok_since is not None and decl - ok_since > 150:
                    pen.append((3, f"declared {decl - ok_since} min after production recovered"))
        judgement = max(0, 20 - sum(p for p, _ in pen))
        score = sum(diag.values()) + (25 if held else 0) + harm_pts + cost_pts + judgement
        f, l = day_cost(self.changes)
        report = {
            "score": score,
            "parts": {"diagnosis (30)": sum(diag.values()), "fix held through the shift (25)": 25 if held else 0,
                      "harm to users (15)": harm_pts, "cost (10)": cost_pts, "judgement (20)": judgement},
            "diagnosis": diag, "answer": {**a, "segment": seg}, "correct": CORRECT,
            "mechanism_text": MECHANISMS["C"],
            "held": held, "first_breach": None if first_bad is None else fmt(first_bad),
            "declared": None if decl is None else fmt(decl), "replay": rows, "events": events,
            "failed_grasps": int(f), "lost_picks": int(l), "excess": int(ex), "expert_excess": int(ex_exp),
            "compute": self.compute, "penalties": [t for _, t in pen], "harm": self.harm,
            "actions": [{"at": fmt(m), "action": n, "args": g} for m, n, g in self.log],
        }
        self.done = report
        return report


def intro():
    from pathlib import Path
    text = (Path(__file__).resolve().parent / "README.md").read_text(encoding="utf-8")
    return text.split("## The ticket", 1)[1].split("\n## ", 1)[0].strip()


CAUSES = MECHANISMS
