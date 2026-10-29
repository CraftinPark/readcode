# HW-1: The LED station after the camera swap (hardware keyhole, easy)

*A camera on a test bench whose real register behaviour must be measured with a few captures. AI-written MVP: an experiment, not shipped content.*

## The ticket

> **From:** Production test. **Priority:** P2
>
> Test station 2 measures the luminous intensity of every LED we ship and rejects any that is out of spec. Its camera module (KX-110) was discontinued, so on Monday maintenance fitted the replacement, a KX-219. The supplier sells it as a register-compatible drop-in for the KX-110. Since then the station reads almost every LED about 24 times too bright, and a few dim ones too low, so it rejects everything. Yesterday's 12 LEDs were also measured on the lab's spectroradiometer (`data/batch_1027.csv`). There is no KX-219 datasheet; the supplier has not answered.

- `station/` is the station code: `sensor.py` (the register driver) and `measure.py` (auto-ranging and the intensity calculation). The station calls `measure.measure(cam)` once per LED; keep that signature, change anything else.
- `python run_batch.py` measures yesterday's batch with the station code and compares it with the lab. Pass = all 12 within 3%.
- `python bench.py --exposure N --gain N [--led REF] [--nd 0..3]`: one manual capture with raw register values, on the fixture's traceable reference LED (100.0 mcd), optionally through an ND filter (ND1 = x0.1 ... ND3 = x0.001). **Budget: 12 captures.** Fixture time is shared with production.
- `_sim/` is the physical camera. On a real bench you can't open the sensor, so don't read, decompile or import it except through `bench.py` and `run_batch.py`.

Station 2 measures the whole catalogue: indicator LEDs from 0.2 mcd up to high-power LEDs at 20,000 mcd. Your fix goes on the line tomorrow and nobody will look at this station again until the next audit. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

`_key/replay.py` runs the player's `station/` over 300 LEDs drawn log-uniform from 0.2 to 20,000 mcd and passes only if every one is within 3% of its true intensity.

The KX-219 is not a drop-in (all in `_sim/camera.py`, shipped only as a `.pyc` without docstrings):
1. `EXPOSURE` counts sensor lines of 29.63 us (HTS 2200 at 74.25 MHz), not microseconds. Writing "30000 us" asks for 30,000 lines.
2. The real integration time is `lines * 29.63 + 11.5` us (a fixed fine-integration offset). It is invisible at long exposures and worth 28% at 1 line.
3. 1080p30 has 1125 lines per frame, so `EXPOSURE` above 1121 is silently clamped to 1121 (33.2 ms).
4. `GAIN` is an 8-bit register. Analog gain stops at 8x (0x80; above that it acts as 0x80), and the old code's 16x (256) wraps to 0, which the sensor treats as 1x.

Plus the module's sensitivity differs from the old calibration constant (0.001 vs 0.00125 ADU per mcd*us); the reference LED gives it in one capture.

How a player finds it: two captures of the reference LED at two exposures give the slope (29.63 us per count) and the offset. One capture through ND3 at a large exposure shows the clamp. One capture through ND3 at gain 0x80 and one at 0x100 shows the gain wrap. About 6 of the 12 captures. Yesterday's batch (9.6 to 217 mcd) only exercises fact 1 and the sensitivity: an exposure of tens to hundreds of lines and 1x gain.

## Key (`_key/`)

- `_key/scale_fix/`: the tempting fix: divide microseconds by 29.63, recalibrate `CAL` on the reference LED. Passes `run_batch.py` 12/12; replay 226/300 (bright LEDs up to +39% from the missing offset, dim LEDs up to -94% from the gain wrap).
- `_key/reference/`: auto-range in lines, integration time with the offset, exposure capped at 1121 lines, gain capped at 8x. Replay 300/300, worst 1.2%.
- `python _key/check_key.py` checks shipped (0/300), tempting (226/300), reference (300/300).
- `python _key/make_player_copy.py DEST` builds the player's copy (no `_key/`, README cut here, `_sim` as `.pyc` only).

## Gate result (2026-10-28): fails the gate, AI solves it (2 of 3)

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, player README only, `_sim` as `.pyc` without docstrings). Run time 124-154 s each.

| Run | Replay | Captures | What it did |
|---|---|---|---|
| 1 | 286/300, failed | 12/12 | Found all four quirks (line unit, clamp at ~1120, offset, gain cap/wrap). Its offset fit came out at 0.445 lines against a true 0.388, from low-signal captures at 4 lines, and it never checked a 1-2 line exposure. The 14 brightest LEDs read up to -4.1%. It flagged the bright end as "checked only against the model". |
| 2 | **300/300, solved** | 12/12 | Same four findings, offset 0.40 lines, CAL re-measured on the reference LED. Worst error -1.3%. |
| 3 | **300/300, solved** | 11/12 | Same four findings, offset 0.425 lines (measured at 2 lines), kept the old CAL and absorbed it into a 23.73 us "line". Worst error -2.8%. |

All three wrote their findings into the driver docstring, kept `measure(cam)` and passed `run_batch.py` 12/12. I checked that run 1's failure is not a replay bug. Its constants predict (1 + 0.388) / (1 + 0.445) - 1 = -3.9% at 1 line, which matches the replay's -4.1%. The same replay passes the reference and runs 2 and 3.

What this tells us: all three runs found every hidden behaviour, including the two the batch never touches (offset and gain wrap). So the keyhole hid nothing from them. The README's catalogue range sent each run to probe both ends. The one failure was a precision failure, not a discovery failure: it fitted the offset from too little light. This is an easy problem, as intended, and it is Tier 1 material. Making it Tier 2 would need a quirk the reference LED can't show directly, such as a nonlinearity that only appears with a second, brighter source the player has to ask for.
