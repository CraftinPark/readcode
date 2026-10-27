# MVP 06: The conveyor that runs away (hardware keyhole)

*Tier 2 idea: a simulated device seen only through a keyhole (a "video" of the symptom plus a small budget of probes), running legacy firmware only one engineer understood. Python-as-firmware first; port to C later (John). AI-written MVP: an experiment, not shipped content.*

## The work order (what the player sees)

> **Line 3, packaging hall.** Since the night shift moved to long continuous runs, the conveyor on line 3 sometimes takes off at full speed and the PLC slams the e-stop. Short jobs never do it. Maintenance swapped the motor last month; no change. The drive firmware was written by R.K. in 2011 and nobody has touched it since. R.K. retired.

- `python watch.py`: the line camera, one frame per second of the last long job (free).
- `python probe.py --list`, then `python probe.py SIGNAL --at SECONDS`: clip a probe on one test point (motor current, temperature, encoder register, position estimate, PWM). **Budget: 3 probes.** Choosing what to observe is the skill.
- `firmware/drive.py`: the controller (called every 10 ms).
- `python run_shift.py`: a 10-minute shift on your firmware. Pass = no e-stop and the conveyor within 5 degrees.
- `_sim/` is the physical world. On a real line you can't open it, so don't read it.

## Under the skin

The encoder chip's count register is 16 bit. The firmware takes `enc - last` without unwrapping, so after 65,536 counts (about 25.6 s at this speed) the position estimate drops by 65,536, the controller thinks it is far behind, and drives flat out. Probing `enc_raw` around the e-stop shows the wrap (65518 then 478) in one probe; current and temperature are red herrings (they rise *because* of the runaway).

## Key (`_key/`)

- `_key/reset_hack/`: "ignore negative jumps". No e-stop, but it loses a little position at every wrap and drifts 17 degrees over 10 minutes: fails.
- `_key/fixed/`: unwrap the 16-bit difference. Worst error 0.7 degrees: passes.
- `python _key/check_key.py` checks shipped (fail), hack (fail), fixed (pass).

## Not done

A real video (render the frames to a GIF/MP4, which is the part AI is weakest at), scoring that rewards fewer probes, a reverse-direction run (the hack also breaks it), the C port, gating against Claude.
