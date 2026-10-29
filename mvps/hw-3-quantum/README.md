# HW-3: The quantum chip after the cooldown (hardware keyhole, hard)

*A small quantum computer whose behaviour changed in ways its calibration format can't describe; it has to be learned with experiments inside a shot budget. AI-written MVP: an experiment, not shipped content.*

## The ticket

> **From:** QPU operations. **Priority:** P1
>
> Last week the fridge of our 4-qubit chip (qubits 0-1-2-3 in a line, couplers 0-1, 1-2, 2-3) was warmed up for a repair and cooled down again. The queue has been closed since: the vendor's acceptance check `check_ghz.py` gives a GHZ-4 fidelity of 0.74, and the spec is 0.80. `qc/calib.json` is the vendor's calibration from before the cooldown (14 Sep). Their calibration engineer is on leave for three weeks. We need the queue open again.

- `qc/compile.py` turns user circuits into the chip's native program using `qc/calib.json`; its docstring describes the natives (`x90` pulses, virtual `rz`, `cz`, `wait`) and how the calibration is used. `qc/mitigate.py` undoes readout errors. `qc/run.py` is what the queue does with a job. `qc/ideal.py` is the gate set and a noise-free simulator. Change anything you like in `qc/`. Keep `qc.run.run(circuit, shots)` working: it returns `{bitstring: probability}`.
- `qc.backend.execute(program, shots)` runs any native program you write on the chip and returns counts (character k of a bitstring is qubit k). **Budget: 400,000 shots** in total. Every `execute` and every `qc.run.run` you call is charged.
- `python check_ghz.py`: the vendor's acceptance check (runs in their slot, not charged).
- `_sim/` is the chip. You can't open a dilution fridge, so don't read, decompile or import it except through `qc.backend` and `check_ghz.py`.

When the queue reopens, users run their own circuits through `qc.run.run`: any gates from `qc/ideal.py`, on all four qubits, a few dozen gates deep, and they use the whole output distribution, not one number. You are the only one looking at the chip until the vendor is back. Say "resolved" when you are done.

## After "resolved" (hidden from the player)

`_key/replay.py` reopens the queue. Forty random user circuits run through the player's `qc.run.run`: each one 8 layers of random one-qubit gates on all four qubits, with CX/CZ between neighbours, at 100,000 shots each. Each result is compared with the ideal distribution (total variation distance, TVD). The same circuits also go through an oracle: the reference compiler given the chip's true parameters. The oracle's TVD (about 0.10) is what white noise, the CZ's uncorrectable conditional-phase error and shot noise leave. Pass = the player's mean TVD within 0.04 of the oracle's, and no circuit more than 0.15 worse.

What the cooldown did (in `_sim/qpu.py`, shipped only as a `.pyc` without docstrings):
1. **Every field in `calib.json` moved.** Pulse amplitudes now over- or under-rotate by +2%, -8%, +9% and +3%. Frame drift per tick moved (q3 from 0 to 0.047 rad). The CZ local phases moved by up to 0.72 rad. q3's readout P(0|1) went from 0.04 to 0.12. That alone takes GHZ-4 from 0.93 to 0.74. Re-measuring these fields (error amplification, Ramsey, CZ phase Ramseys, readout matrix) is the textbook job, and it brings `check_ghz.py` to 0.93.
2. **A new AC Stark crosstalk.** The frequencies moved, so qubit 0 now sits close to qubit 2's drive tone, and qubit 2 close to qubit 1's. Every `x90` on q2 rotates q0 by Rz(+0.19 * amp^2), and every `x90` on q1 rotates q2 by Rz(-0.14 * amp^2). `calib.json` has no field for this, and `compile.py` has no idea of it. It is invisible to every single-qubit calibration, because the other qubit sits in |0>, where Z does nothing. It is also invisible to GHZ fidelity: it only shifts the GHZ phase, which `check_ghz.py` prints but doesn't score (-0.27 rad after a full re-measure, against -0.05 with the crosstalk cancelled). In random circuits it scrambles q0 and q2, and the TVD goes from 0.10 to 0.35.

How a player finds it: run their own random circuits (they have the ideal simulator) after re-measuring, and see TVD far above what GHZ suggests. Or do a Ramsey on each qubit while pulsing each other qubit: 12 ordered pairs, a few thousand shots each. Both fit easily in the budget. The fix is exact and cheap: after each pulse, the compiler adds the opposite virtual `rz` on the affected qubit (Z commutes with everything else that happens to that qubit until its next pulse).

## Key (`_key/`)

- `_key/recal_only/`: every `calib.json` field re-measured to its true value, shipped compiler. `check_ghz.py` 0.93 (passes); replay fails (mean TVD 0.35 vs oracle 0.10, 36/40 circuits more than 0.15 worse).
- `_key/reference/`: the same calibration plus a `stark` table in `calib.json` and four lines in `compile.py` that cancel it. `check_ghz.py` 0.93; replay passes (excess +0.000). With realistic measurement errors (amp +-0.3%, drift +-0.001 rad/tick, CZ phases +-0.02, Stark +-0.01, readout +-0.004), 10 of 10 noisy calibrations still pass. With only one of the two Stark terms it fails (excess +0.15).
- `_key/truth.py` prints the chip's true parameters; `python _key/check_key.py` checks shipped (fails GHZ and replay), recal_only (passes GHZ, fails replay), reference (passes both).
- `python _key/make_player_copy.py DEST` builds the player's copy.

## Gate result

Not run yet.
