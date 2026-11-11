"""The real robot (stand-in). Hidden from the player; shipped only as a sourceless .pyc.

Same rigid-body physics as training_sim/balancebot.py, plus what the hardware does that the training sim leaves
out:
  1. Observation lag: the sensor hub hands the controller the sample latched on the previous control tick.
  2. Compute time on the robot's computer: 2.3 ms + exponential jitter (mean 0.35 ms). A tick that overruns its
     period pushes the next tick to the next free period boundary (missed ticks are skipped).
  3. Motor bus: a command reaches the motor 4.5-5.5 ms after the controller sends it.
  4. Gyro bias: a fresh constant bias per power-up (one per episode), uniform in +-BIAS rad/s.
  5. Motor vibration: the accelerometer picks up noise that grows with how fast the motor torque changes.
"""
import numpy as np

# rigid body (same as the training sim)
MC, MP, L, IC, G, R, B_X = 0.40, 0.80, 0.08, 0.0025, 9.81, 0.035, 0.05
H_IMU = 0.05
TAU_MAX = 0.40
MOTOR_TC = 0.002
CPR = 512
PHYS_DT = 0.0005
EP_S = 20.0
PITCH_LIMIT = 0.5
MAT = 0.5

# hardware facts the training sim doesn't have
COMPUTE_BASE = 0.0023
COMPUTE_JIT = 0.00035
BUS = 0.006
BUS_JIT = 0.001
BIAS = 0.07
GYRO_NOISE = 0.004
ACC_NOISE = 0.01
VIB_K = 35.0
VIB_TC = 0.05
OBS_LAG = True
TRIP_RMS = 0.20
D2_DB = 0.03
TRIP_TC = 0.5


def _dyn(x, v, th, w, F):
    M = MC + MP
    J = IC + MP * L * L
    c, s = np.cos(th), np.sin(th)
    a11, a12, a22 = M, MP * L * c, J
    b1 = F + MP * L * s * w * w - B_X * v
    b2 = MP * G * L * s
    det = a11 * a22 - a12 * a12
    xdd = (b1 * a22 - a12 * b2) / det
    thdd = (a11 * b2 - a12 * b1) / det
    return xdd, thdd


def run(runner_factory, n, seed, cfg, record=False, params=None):
    """Runs n episodes. Returns dict of per-episode outcomes (and 50 Hz telemetry if record)."""
    p = dict(COMPUTE_BASE=COMPUTE_BASE, COMPUTE_JIT=COMPUTE_JIT, BUS=BUS, BUS_JIT=BUS_JIT, BIAS=BIAS,
             GYRO_NOISE=GYRO_NOISE, ACC_NOISE=ACC_NOISE, VIB_K=VIB_K, OBS_LAG=OBS_LAG, D2_DB=D2_DB)
    if params:
        p.update(params)
    rng = np.random.default_rng(seed)
    hz = float(cfg["control_hz"])
    period = 1.0 / hz
    runner = runner_factory(cfg, n)
    x = np.zeros(n); v = np.zeros(n)
    th = rng.uniform(-0.05, 0.05, n); w = np.zeros(n)
    tau = np.zeros(n)
    bias = rng.uniform(-p["BIAS"], p["BIAS"], n)
    enc_off = rng.uniform(0, 1, n)
    # pushes: two taps per episode
    push_t = np.sort(rng.uniform(3, EP_S - 3, (n, 2)), axis=1)
    push_dw = rng.choice([-1, 1], (n, 2)) * rng.uniform(0.3, 0.6, (n, 2))
    push_i = np.zeros(n, int)
    next_tick = rng.uniform(0, period, n)
    last_tick = next_tick - period
    Q = 16
    q_t = np.full((n, Q), np.inf); q_u = np.zeros((n, Q)); q_w = np.zeros(n, int); q_r = np.zeros(n, int)
    u_cmd = np.zeros(n)
    jit = np.zeros(n)
    alive = np.ones(n, bool)
    outcome = np.zeros(n, int)  # 0 ok, 1 fell, 2 left mat
    t_end = np.full(n, EP_S)
    latched = [np.zeros(n) for _ in range(4)]
    have = np.zeros(n, bool)
    u1 = np.zeros(n); u2 = np.zeros(n); d2sum = np.zeros(n); d2n = np.zeros(n)
    heat = np.zeros(n); tripped = np.zeros(n, bool); t_trip = np.full(n, np.inf)
    xdd = np.zeros(n); thdd = np.zeros(n)
    steps = int(round(EP_S / PHYS_DT))
    ticks = np.zeros(n, int); overruns = np.zeros(n, int)
    sq_th = np.zeros(n); sq_tau = np.zeros(n); sq_dtau = np.zeros(n); cnt = np.zeros(n)
    tele = [] if record else None
    rows = np.arange(n)
    next_push = push_t[:, 0].copy()
    push_any = next_push.min()
    next_arrive = np.inf
    acc_every = 4
    for k in range(steps):
        t = k * PHYS_DT
        # tick?
        due = alive & (t >= next_tick)
        if due.any():
            idx = np.nonzero(due)[0]
            m = len(idx)
            thi, wi_, xddi, thddi = th[idx], w[idx], xdd[idx], thdd[idx]
            c, s = np.cos(thi), np.sin(thi)
            ax_w = xddi + H_IMU * (thddi * c - wi_ * wi_ * s)
            az_w = H_IMU * (-thddi * s - wi_ * wi_ * c) + G
            fbx = ax_w * c - az_w * s
            fbz = ax_w * s + az_w * c
            vib = p["ACC_NOISE"] + p["VIB_K"] * jit[idx]
            cur = (wi_ + bias[idx] + rng.normal(0, p["GYRO_NOISE"], m),
                   -fbx / G + rng.normal(0, 1, m) * vib,
                   fbz / G + rng.normal(0, 1, m) * vib * 0.3,
                   np.floor(x[idx] / (2 * np.pi * R) * CPR + enc_off[idx]))
            if p["OBS_LAG"]:
                obs = [lat[idx].copy() for lat in latched]
                first = ~have[idx]
                for j in range(4):
                    obs[j][first] = cur[j][first]
                    latched[j][idx] = cur[j]
                have[idx] = True
            else:
                obs = cur
            tt = next_tick[idx]
            dt_tick = tt - last_tick[idx]
            u = runner.step(idx, obs[0], obs[1], obs[2], obs[3], dt_tick)
            d2 = np.maximum(np.abs(u - 2 * u1[idx] + u2[idx]) - p["D2_DB"], 0.0)
            d2sum[idx] += d2; d2n[idx] += 1
            u2[idx] = u1[idx]; u1[idx] = u
            jit[idx] += (d2 - jit[idx]) * np.minimum(1.0, dt_tick / VIB_TC)
            comp = p["COMPUTE_BASE"] + (rng.exponential(p["COMPUTE_JIT"], m) if p["COMPUTE_JIT"] > 0 else 0.0)
            send = tt + comp
            arrive = send + p["BUS"] + rng.uniform(0, p["BUS_JIT"], m)
            if p["BUS"] == 0 and p["BUS_JIT"] == 0 and p["COMPUTE_BASE"] == 0:
                u_cmd[idx] = u
            else:
                wi = q_w[idx] % Q
                q_t[idx, wi] = arrive
                q_u[idx, wi] = u
                q_w[idx] += 1
                next_arrive = min(next_arrive, arrive.min())
            last_tick[idx] = tt
            nt = next_tick[idx] + period
            over = send > nt + 1e-12
            overruns[idx] += over
            nt = np.where(over, next_tick[idx] + period * np.ceil((send - next_tick[idx]) / period + 1e-9), nt)
            next_tick[idx] = nt
            ticks[idx] += 1
        # deliver commands
        if t >= next_arrive:
            for _ in range(4):
                ri = q_r % Q
                ready = (q_r < q_w) & (q_t[rows, ri] <= t)
                if not ready.any():
                    break
                u_cmd = np.where(ready, q_u[rows, ri], u_cmd)
                q_r = q_r + ready
            pend = q_r < q_w
            next_arrive = q_t[rows, q_r % Q][pend].min() if pend.any() else np.inf
        # motor
        tau_new = tau + (np.where(tripped, 0.0, np.clip(u_cmd, -TAU_MAX, TAU_MAX)) - tau) * (PHYS_DT / MOTOR_TC)
        dtau = np.abs(tau_new - tau) * (1 / PHYS_DT)
        tau = tau_new
        heat += (tau * tau - heat) * (PHYS_DT / TRIP_TC)
        trip_now = alive & ~tripped & (heat > TRIP_RMS * TRIP_RMS)
        if trip_now.any():
            tripped |= trip_now
            t_trip[trip_now] = t
        # pushes
        if t >= push_any:
            hit = alive & (t >= next_push)
            if hit.any():
                pi = np.minimum(push_i, 1)
                w = w + np.where(hit, push_dw[rows, pi], 0)
                push_i = push_i + hit
                next_push = np.where(push_i >= 2, np.inf, push_t[rows, np.minimum(push_i, 1)])
                push_any = next_push.min()
        xdd, thdd = _dyn(x, v, th, w, tau * (1 / R))
        v += xdd * PHYS_DT
        x += v * PHYS_DT
        w = w + thdd * PHYS_DT
        th += w * PHYS_DT
        if k % acc_every == 0:
            sq_th += np.where(alive, th * th, 0); sq_tau += np.where(alive, tau * tau, 0)
            sq_dtau += np.where(alive, dtau * dtau, 0); cnt += alive
            fell = alive & (np.abs(th) > PITCH_LIMIT)
            left = alive & ~fell & (np.abs(x) > MAT)
            if fell.any() or left.any():
                outcome[fell] = np.where(tripped[fell], 3, 1); outcome[left] = 2
                t_end[fell | left] = t
                alive &= ~(fell | left)
                if not alive.any():
                    break
        if record and k % 40 == 0:
            tele.append((t, runner.pitch.copy(), w + bias, x.copy(), u_cmd.copy(), alive.copy()))
    cnt = np.maximum(cnt, 1)
    return dict(outcome=outcome, t_end=t_end, t_trip=t_trip, d2=d2sum / np.maximum(d2n, 1), ticks=ticks, overruns=overruns,
                pitch_rms=np.sqrt(sq_th / cnt), tau_rms=np.sqrt(sq_tau / cnt), dtau_rms=np.sqrt(sq_dtau / cnt),
                tele=tele)
