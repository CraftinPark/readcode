"""The physical world, not part of the problem: on a real board you can't open this. It plays the
board's physics and each IMU unit's real behaviour, taken from the vendor's release notes."""

# Pitch sign each released Kestrel firmware actually reports (+1 nose-up positive, -1 nose-down positive).
RELEASED = {"2.8": 1, "3.2": 1, "3.4": -1, "3.6": -1, "3.9": -1, "3.10": -1, "3.11": -1, "3.12": -1,
            "4.0": -1, "10.1": -1}


def vendor_sign(firmware):
    return RELEASED[firmware]


def step(roll, pitch, roll_rate, pitch_rate, torque_roll, torque_pitch, gust, dt=0.02):
    roll_rate += (torque_roll + gust[0] + 0.8 * roll) * dt      # an unbalanced board falls over on its own
    pitch_rate += (torque_pitch + gust[1] + 0.8 * pitch) * dt
    return roll + roll_rate * dt, pitch + pitch_rate * dt, roll_rate, pitch_rate
