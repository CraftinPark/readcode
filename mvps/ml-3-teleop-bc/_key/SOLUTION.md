# ML-3 key: what is wrong and how it is graded

## The bug

`pipeline/io.py::_seconds` moves each stream's time origin to **that stream's own first sample** (`t_ns - t_ns.min()`), so each stream's clock starts at 0 when that device's first sample arrived. On rig v2 the streams do not start together (`rig/recorder.py`): follower and camera start within ~60 ms of "record", but the teleop node only forwards the leader once the deadman pedal is down, 0.3-0.9 s later (varies per episode). After loading, `sync.common_window` sees every stream starting at 0 and builds the grid from there, so frame i pairs the arm state and camera at real time t with the leader command from t + (pedal delay).

Every action label is therefore taken 0.3-0.9 s **in the future** relative to its observation, by a different amount per episode. The policy learns to "close when the arm will be at the block in half a second": it closes early, misses (the jaws can shove the block), reopens and retries. Training is unremarkable (validation loss is somewhat higher than with the fix; nothing errors).

**Fix:** convert every stream of an episode against one shared origin, e.g. `meta["start_ns"]` (reference, `_key/reference/pipeline/io.py`), or the minimum first stamp over all streams. Anything that keeps all streams on the host clock works; the hidden alignment tests are origin-agnostic.

Visible paths to it: `tools/inspect_episode.py` on the shipped code shows the follower standing still for most of a second while the leader target already moves away (with the fix the first frame is the pedal-down moment and the arm follows the target); the meta's `start_ns` is never read; the recorder docstring says each stream begins with that device's own first sample and the leader starts only with the pedal.

## Results (seed 0 unless noted; `python _key/ab_eval.py [--seed N]`)

| | success | first try | missed grasps / ep | mean time to success |
|---|---|---|---|---|
| shipped, seed 0 / 1 / 2 | 62% / 56% / 62% | 46% / 50% / 50% | 2.28 / 2.20 / 2.08 | 3.0-4.1 s |
| reference, seed 0 / 1 / 2 | 96% / 96% / 100% | 82% / 86% / 96% | 0.26 / 0.24 / 0.04 | 5.2-5.7 s |

Bench bar in the hidden test: success >= 85% and first try >= 70%.

## Hidden tests (`_key/hidden_tests/test_hidden.py`)

- 5 alignment tests on synthetic rig v2 episodes where every signal is linear in absolute time; streams start together / leader late / follower late / camera late / leader late and ends early. Each aligned frame's observation and action must come from the same instant (6 ms), frames 0.1 s apart inside the common window, gripper held. Shipped passes only "start together".
- 5 guards: rejected episodes unchanged (17, 45, 64, 101, 108, 122, 133), hold/chunk/history semantics, ensembler weights, gripper not normalised, bench files and bench settings untouched.
- 1 closed loop: `train.py --out` + `evaluate.py --json` on the shipped demos.

`python _key/check_key.py` = self-check (shipped fails 5 of 11, reference passes 11 of 11, key answers 7/7). `--fast` skips the closed-loop test.

## Tempting wrong fixes

- Shifting actions by a constant number of frames: the delay varies per episode (0.3-0.9 s), and the synthetic tests use other offsets, including camera-late and follower-late cases.
- Dropping the first N frames of each episode: removes the static start but keeps the offset for the rest of the episode.
- Tuning the gripper threshold, ensembling decay or training length: the labels are wrong; the bench stays near 50% first try.

## Comprehension answers

In `_key/answers.json` with the files each needs and the misread behind each distractor.
