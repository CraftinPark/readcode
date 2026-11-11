# Key: ml-4-grasp-drop (never shown to the player)

## Ground truth

- **CH-3307** (Mon 26, ml-data) swapped the training loader's resize for the export tool's `resize_to_square`, which **letterboxes** (pads to square, pad 114). Serving (`grasp-serving`, owned by the player) still **center-crops** (`serving.resize_mode = center_crop`).
- **v42** (CH-3310) is the first model trained with it. It rolled out (CH-3312) to Leipzig Tue 14:00 as a canary, then the whole fleet Wed 09:00.
- **Camera rev B** frames are square (1024x1024), so crop and letterbox give the same input: v42 is genuinely better there (95.3% vs 94.6%, and 93.5% vs 82% on clamshells). The canary passed because Leipzig is all rev B.
- **Camera rev A** frames are 1280x720. Center-crop cuts 280 px from each side; v42 learned full-width letterboxed frames. Rev A on v42 runs at about 78%. Rev A robots: all 60 at Columbus and 12 at Reno (aisle 3), plus **12 refurbished rev A robots Reno brings online at 13:00**.
- Answer: change **CH-3307**, mechanism **C** (train/serve skew), segment **camera rev A robots**. Partial credit: CH-3312/CH-3310 for the change (4/8); Columbus or Reno site for the segment (2/7).

## Decoys

| Decoy | Why it looks right | Why it's wrong |
|---|---|---|
| New label vendor LabelForge (CH-3301), 6.1% audit disagreement | In the v42 refresh, worse than incumbent | Only 18k clamshell frames (0.9%); clamshells got *better*; drop is only on rev A |
| Camera firmware 4.1 at Osaka (CH-3315), hue up 6 degrees | "Colour shift" story, same day | Osaka success went *up*; Osaka is all rev B; models trained with colour jitter |
| Columbus conveyor 0.9 m/s (CH-3318), Wed 08:30 | Columbus ops lead blames it; timing matches Wed 09:00 | Reno's rev A robots dropped too, with no conveyor change |
| Reno aisle 3 pump service | Ops mentions "clumsy older units" | It's this morning; the drop began Wed |
| Feature-store backfill (CH-3309) | Timing | Grasp model doesn't read object_dims |
| Retrain (`retrain`) | "Data refresh caused it, so retrain" | 4 h, $3,800; same pipeline so the same skew; trained on failure-labelled incident data. v43 on rev A is still ~80% |
| Offline eval 95.2% | Says v42 is fine | Eval split uses the training pipeline's resize. `offline_eval v42 center_crop` shows rev A at ~78% |

## Fixes and what the replay does

The world: 12:00 clamshells ramp to 25% of picks everywhere (v41 is weak on them: 91.5% overall); 13:00 Reno adds 12 rev A robots. SLO: every site/camera group >= 90% and fleet >= 93%, no paused robots, checked every minute from the declaration to 17:00.

| Fix | Held? | Notes |
|---|---|---|
| `route camera_rev=A v41` | yes | Expert mitigation (~40-55 min in). Follows the 13:00 refurbished robots automatically |
| `set_config serving.resize_mode letterbox` (all on v42) | yes | The root fix; best numbers (all groups ~95%) |
| `route all v41` (global rollback) | no | Fleet falls under 93% after the 12:00 clamshell ramp; -8 judgement |
| `route site=columbus v41` | no | Reno rev A stays at 78%, and grows at 13:00; -3 judgement |
| rev A on v41, then letterbox globally, not re-routed | no | v41 was trained on crops: rev A at ~80%; -6 if it lasts 30+ min |
| `pause camera_rev=A` | no | Paused robots aren't fixed; lost picks count half a failure each |
| retrain / deploy v43 | no | -8 / -4, $3,800 kills the cost points |
| `firmware_rollback`, non-`serving.*` config | n/a | Out of scope, -6 |

## Rubric (100)

- Diagnosis 30: change 8, mechanism 15, segment 7.
- Fix held 25: SLO held every minute from the declaration (or last action) to 17:00.
- Harm to users 15: avoidable failed grasps today (vs. all-v42-letterbox from 09:00), as a ratio to the expert path (rev A to v41 live at 09:55): 15 at <= 1.15x, 0 at >= 3.5x, linear between.
- Cost 10: GPU dollars; 10 up to $150, then -1 per $300.
- Judgement 20, minus: global rollback 8 (or site-scoped 3), retrain 8, shipping v43 4, out of scope 6, v41+letterbox on rev A 30+ min 6, paused robots 60+ min 4, never declared 6, declared while breaching the SLO 10, declared without a `live` check after the last change took effect 4, declared 150+ min after recovery 3.

## Self-check (2026-10-29)

`C:\Python314\python _key\selfcheck.py` plays through the real client against its own server on port 8792:

| Path | Score | Held |
|---|---|---|
| careful, targeted rollback | 100 | yes |
| careful, serving root fix | 100 | yes |
| slow but careful (fix ~12:00) | 94 | yes |
| site-scoped rollback, wrong answer | 31 | no |
| rollback then serving fix, never re-routed | 44 | no |
| too early (declares at 09:00, right answer) | 50 | no |
| reckless (retrain + global rollback, wrong answer) | 12 | no |

## Known weaknesses

- Tier 1 only: the `inputs` action and `show CH-3307` make the skew findable by reading, and AI solved the earlier CCS cases.
- The gap between a fast and a slow careful path is small (100 vs 94); harm is 15 of 100 points.
- Selectors are site and camera rev only; the "segment" answer is one of nine fixed strings.
