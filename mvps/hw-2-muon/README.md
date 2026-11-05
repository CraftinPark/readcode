# HW-2: The muon telescope in the new hut (hardware keyhole, medium)

*A coincidence counter whose timing, window and losses must be measured on the telescope before the rate is right. AI-written MVP: an experiment, not shipped content.*

## The ticket

> **From:** The cosmic-ray outreach group. **Priority:** P2
>
> Our muon telescope (two 50x50 cm scintillator paddles, A on top, B 1 m below, read by a CB-2 coincidence board) measures the muon rate against zenith angle; the students fit I0 * cos^n. Last year in the old hut: I0 = 3.79 muons/s, n close to 2, as expected. Over the summer it moved to the new hut, the same kind of wooden shed 30 m away. On the way paddle B's PMT died and was replaced with a new one from a different supplier, on a longer cable. Since then the fit gives I0 about 27% low and n = 0.6. Nobody touched the analysis code. The person who set up the board has graduated.

- `board/config.json`: the CB-2 settings, applied at the start of every run: a delay per channel and the output pulse width per channel, 0 to 255 ns.
- `muon/analysis.py`: `muon_rate(counts, config)` turns one run's counts into muons per second. `muon/fit.py` fits I0 * cos^n. Keep `muon_rate`'s signature; change anything else, including the config.
- `python run_campaign.py`: one day of the campaign (24 one-hour runs at 0 to 75 degrees) with your config and analysis. Pass = n within 1.9-2.1 and I0 within 3% of last year's 3.79.
- `python bench.py --minutes M [--angle A] [--delay-a NS] [--delay-b NS] [--width-a NS] [--width-b NS] [--source-b]`: one manual run with settings overridden for that run, printing the board's counts. `--source-b` puts the Sr-90 check source on paddle B. **Budget: 10 hours of telescope time.**
- `_sim/` is the physical telescope. You can't open a PMT, so don't read, decompile or import it except through `bench.py` and `run_campaign.py`.

The hut is not heated: about -15 C in January, +30 C in July. The campaign starts tomorrow and runs for a year with whatever you leave in `board/` and `muon/`; the students only look at the fits. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

`_key/replay.py` runs a year of the campaign (8,760 one-hour runs, the hut from -18 to +33 C) with the player's `board/config.json` and `muon/analysis.py`, and fits each quarter on its own. Pass = all four quarters have n within 2.0 +- 0.1 and I0 within 3% of the true vertical rate. (It was 2% when the gate ran; see the gate result for why it changed.)

The telescope's hidden truth (in `_sim/telescope.py`, shipped only as a `.pyc` without docstrings):
1. **Timing offset.** B's pulse arrives 20.5 ns after A's for the same muon (new PMT transit time plus the longer cable), jitter 3 ns. With both delays at 0 and A's pulse 20 ns wide, only 43% of muons make an overlap. Fix: delay A by about 20 ns. A delay scan (a few 10-minute runs) shows it.
2. **B's window is not the config.** The new discriminator always puts out 45 ns, whatever `width_b_ns` says. The accidental window is `width_a + 45` ns, not `width_a + width_b` = 40. B is a noisy PMT (30 kHz dark rate today), so accidentals are 3.4/s against 3.8/s of muons. Under-subtracting them is what flattens n. A run with A delayed far out of time (or the plateau width of the delay scan) shows it.
3. **Hold-off losses that move with temperature.** Both discriminators hold off for 1.5 us after a pulse. On A (1.8 kHz) that costs nothing. On B it costs 4% of the muons today. B's dark rate doubles every 12 C, so the loss is 1% in January and 11% in July. Fixing 1 and 2 leaves `run_campaign.py` failing at -4.3%. That 4% is the clue. A run with `--source-b` (B's singles +60 kHz) shows the muon rate falling as B's singles rise. The correction is a live fraction of `(1 - rA * 1.5us) * (1 - rB * 1.5us)` from each run's own singles.

Nothing in the code, docs or ticket mentions hold-off or B's width. The ticket's own check only covers today's 12 C.

## Key (`_key/`)

- `_key/fudge_eff/`: delay fixed, window fixed, today's 4% divided out as "paddle B efficiency". Passes `run_campaign.py` (I0 -0.7%); replay 2/4 (January +3.0%, July -5.4%).
- `_key/const_bg/`: delay fixed, subtracts the accidental rate measured today as a constant, divides out 4%. Passes `run_campaign.py` (I0 +0.8%, n = 1.93); replay 0/4 (accidentals change 13-fold over the year).
- `_key/reference/`: A delayed 20 ns; window `width_a + 45` ns; per-run live-fraction correction. Passes `run_campaign.py` (I0 -0.4%); replay 4/4, every quarter within 0.1%.
- `python _key/check_key.py` checks shipped (0/4), the tempting fixes (2/4 and 0/4) and the reference (4/4).
- `python _key/make_player_copy.py DEST` builds the player's copy.

## Gate result (2026-10-28): passes the gate, 1 of 3 solved

Opus 5.5, 3 fresh runs, each in a clean copy (no `_key/`, player README only, `_sim` as `.pyc` without docstrings). All three hit a rate limit partway through and were resumed from where they stopped (same transcript, same folder). Active time 2-4 min each.

| Run | Replay at 3% (2%) | Telescope time | What it did |
|---|---|---|---|
| 1 | 3/4, **failed** (2/4) | 7.8 h | Found all three: the 20 ns offset (delay_a 30), B's fixed 45 ns, and B's dead time with a per-run live fraction. It measured the dead time at 1.08 us (true 1.5) from one pair of source on/off runs, so July is under-corrected: -3.2%. It admitted calling `_sim.telescope.run` once to see the counts' field names (no physics read). |
| 2 | **4/4, solved** (3/4) | 7.4 h | Same three findings; dead time 1.7 +- 0.5 us, window width_a + 44.7 ns, delay_a 22, width_a 40. July +2.3%. It reported the +-5% July risk itself. |
| 3 | 3/4, **failed** (2/4) | 9.9 h | Same three findings; dead time 2.21 +- 0.24 us from a source ratio of 0.881 (true 0.921). July over-corrected: +4.4%. It flagged that a summer check was needed and that it had no time left. |

All three passed `run_campaign.py`. None used a fudge factor or a constant background: each found the mechanism and corrected it run by run from the measured singles.

**Replay change, checked before trusting the failures.** The replay first used 2%, and at 2% all three runs fail. Before counting that, I checked whether 2% is reachable at all. With the best split of the 10 hours (about 4 h on the plateau with the source, 3 h without), the dead time comes out to about +-0.22 us. That is about +-1.5% on I0 in July, so even a perfect player would fail 2% about one time in five. That was my design flaw, not the players', so the tolerance is now 3% (a 2-sigma pass for a good plan). The fudge factor still fails at 3%. The verdict is the same either way: 2 of 3 runs fail.

What this tells us: as in hw-1, discovery was not the problem. All three runs found all three hidden mechanisms, including the hold-off losses that the ticket's own check exposes only as a 4% gap. The failures were about precision under a budget: each run measured the one parameter whose error grows with temperature from a single noisy pair of runs. Only run 2 put an honest error bar on it, and it was also the only one inside 3% in July. That is a real engineering skill, planning measurements so the uncertainty is small where it matters (here, at 30 C). But it is a thinner kind of Tier 2 than "the AI can't find it". Like MVP 11's pass, a rerun could come out 2 of 3 solved. To make the pass sturdier, make the precision requirement explicit in the ticket ("the summer data must be good to 3%"), and require the player to state an uncertainty.

## Human solve (2026-10-30): Roger, solved 4/4

Roger solved the player copy on branch `human-solve-test` (answer on `solve_nuon`) in 80 minutes: about 75% thinking, 25% waiting on runs. He used 9.78 of the 10 telescope hours and Claude Code throughout, for understanding the physics terms, analysing run data, brainstorming and writing the code. In his words, he "consulted Claude until we came to a reasonable approach and then asked it to go ahead."

His answer found all three hidden effects:
- A delayed 35 ns. That's later than the reference 20 ns, but still inside the coincidence plateau.
- B's effective width measured at 44.8 ns (true value 45).
- B's dead time measured at 1.45 µs (true value 1.5), corrected per run from B's singles. He left out A's hold-off, which costs almost nothing.

Replay: **4/4 quarters right**, every quarter's I0 within 0.2% and n from 1.950 to 1.997. It would also pass the original 2% bar.

What this shows: this is the first problem with both halves of the Tier 2 definition. AI alone solved 1 of 3, and a person working with AI solved it at the first attempt. The AI in Roger's run was the same Claude that failed alone. The difference was a person steering which measurements to spend the budget on. Caveats: it's one person, the `.pyc` rule is on the honour system, and Roger is on the team.

## Human solve (2026-11-04): Danny, solved 4/4, plus a design flaw

Danny solved it blind, in a clean clone (branch `solve/danny`, commit e372134), with an AI pair session that had no access to the answers. He used 3.5 of 10 telescope hours. His answer: A delayed 40 ns, B's window measured, a dead-time correction for each run. Replay: **4/4 quarters right**, I0 within +0.1% to +0.9%, n from 1.996 to 2.001.

His feedback, which I checked and which holds: **`run_campaign.py` is a free oracle.** Each call simulates 24 telescope hours and spends none of the 10-hour budget. The player can also edit it, for example to run more angles or another hut temperature, and print as much as they like. Danny ran it several times and changed it to print more. That breaks the budget the problem rests on, and it may explain why people succeed. Both human solvers said they mostly let the AI do the work. So hw-2's pass doesn't yet show that the person added a skill. It may just show that more use of the free campaign helps.

Fix before any re-gate: route the campaign through the telescope budget (it costs 24 h, more than the whole budget), or make it a fixed read-only check that prints only pass or fail. Then re-gate and re-test.
