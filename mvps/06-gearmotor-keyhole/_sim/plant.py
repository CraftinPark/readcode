"""The physical world (not part of the problem). A DC gearmotor, 64-line quadrature encoder (256
counts per motor turn), 50:1 planetary gearbox, driving a conveyor that should turn 0.2 output rev/s. The line PLC trips the e-stop when the
conveyor is 90 degrees off where it should be."""
DT = 0.01
COUNTS_PER_OUT_REV = 256 * 50


def run(drive_cls, seconds=40):
    drive = drive_cls()
    vel = 0.0          # motor speed, counts per tick
    true = 0.0         # true motor position, counts
    temp = 31.0
    log = {k: [] for k in ("t", "shaft_angle_error_deg", "motor_current_a", "enc_raw", "pos_estimate", "pwm", "temperature_c")}
    for i in range(int(seconds / DT)):
        t = i * DT
        sp = int(COUNTS_PER_OUT_REV * 0.2 * t)           # 0.2 output rev per second
        enc = int(true) & 0xFFFF                          # 16-bit counter register
        pwm = drive.isr(enc, sp)
        target_vel = pwm * 0.25
        vel += (target_vel - vel) * 0.2
        true += vel
        current = 0.4 + abs(target_vel - vel) * 0.02 + abs(vel) * 0.0015
        temp += (current * current * 0.004) - (temp - 31.0) * 0.002
        log["t"].append(round(t, 2))
        log["shaft_angle_error_deg"].append(round((true - sp) / COUNTS_PER_OUT_REV * 360, 1))
        log["motor_current_a"].append(round(current, 2))
        log["enc_raw"].append(enc)
        log["pos_estimate"].append(drive.pos)
        log["pwm"].append(pwm)
        log["temperature_c"].append(round(temp, 1))
        if abs(log["shaft_angle_error_deg"][-1]) > 90:
            log["estop_at"] = round(t, 2)
            break
    return log
