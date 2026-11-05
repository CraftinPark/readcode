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

## What I'm sending back (Danny)

1. **Time:** 2026-11-04 21:31–22:13 PST (about 40 minutes). Almost all thinking: bench and campaign runs return instantly.
2. **AI tools:** Claude Code (Opus 5.5) as pair: read the code, proposed each measurement with its cost, ran `bench.py` / `run_campaign.py` after I approved, did the rate/window/dead-time arithmetic and wrote the `analysis.py` change.
3. **Telescope time used:** 3.50 of 10 h. Also 4 runs of `run_campaign.py` (not counted by the budget; it replays the same fixed day each time, so we used it only as a check, never to tune constants).
4. **Final answer: resolved.** Files changed: `board/config.json` (`delay_a_ns` 0 -> 40) and `muon/analysis.py` (accidentals window = width_a + max(width_b, 45 ns); divide by B's live fraction 1 - rB * 1.7 us). Campaign: I0 = 3.789 (-0.0%), n = 1.996.
5. **Approach:** The campaign rates fit 0.41 x true + 1.31/s at every angle, so there were two faults: lost muons and a constant excess. A delay scan showed B arrives ~20 ns late (fixed by delaying A 40 ns, mid-plateau with margin for the longer flight time at 75 deg), and accidentals measured at a 200 ns offset showed B's new PMT gives ~45 ns pulses whatever width_b says (window 65 ns, not 40). The last ~5% was board dead time on B (~1.7 us), driven by the new PMT's high, temperature-dependent noise; we measured it from the ratio with and without the Sr-90 source, so it doesn't rely on last year's I0. Concern: bench runs are always at 12 C, so we couldn't test whether the 45 ns pulse length or the dead time drift between -15 and +30 C, and in July (B noise ~80k/s) the accidentals and dead-time corrections are large (~3% uncertainty from tau alone).
