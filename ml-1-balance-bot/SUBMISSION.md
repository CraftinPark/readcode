# ML-1 balance bot: submission

**Answer: not resolved.** The best settings are in `deploy/config.json`: `control_hz` 250, `tilt_filter_tau_s` 1.2, `action_smoothing` 0. Expected acceptance on Friday: **about 60–75%**, below the 97% requirement.

## Report

1. **Time:** 2.5 hours. Thinking vs waiting: 50/50.
2. **AI tools:** Claude Code (Claude Opus 5.5), to read the code, write sim experiments and analyse robot telemetry.
3. **Runs used:** 60 of 60 robot episodes, plus many free sim runs.
4. **Files changed:** `deploy/config.json` only.

## Why it can't reach 97%

- **The IMU readings arrive about 10 ms late**, partly counted in loop ticks. At 100 Hz the robot rocks at about 10 Hz and trips the driver. Running at 220–260 Hz removes this. At 300 Hz about 5% of ticks overrun.
- **The gyro has a random offset each episode** (spread about 0.09 rad/s). The tilt filter turns it into a false lean, so the robot parks off-centre and drives off the mat. A long τ (1.5 or more) makes this worse. A short τ (0.7 or less) lets in the real accelerometer's noise, which is far worse than the sim's. The best is τ 1.0–1.2: **13 of 21 episodes passed (62%)**. Failed episodes had about twice the gyro offset of passing ones. If the true rate were 97%, a result this bad would almost never happen.
- **Smoothing only adds lag.** Torque and shaking rose at 0.3 and 0.5. At 0.95 the robot fell in 0.5 s.

**Fix outside the config:** measure the gyro offset at startup while the robot is held still, and subtract it.

## Approach and what was confusing

I compared the robot telemetry with the training sim, fitted the delay, gyro offset and overruns into a copy of the sim, then tuned on the robot. The confusing part: the fitted sim was too kind to the accelerometer. It predicted 95% at τ 0.35, but the robot got 0/10, so the final tuning was done on the robot directly.
