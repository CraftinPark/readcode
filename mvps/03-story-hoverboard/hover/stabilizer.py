"""Keeps a patrol board level: a PD controller per axis."""

KP, KD = 40.0, 9.0


class Stabilizer:
    def __init__(self, imu):
        self.imu = imu
        self.prev = (0.0, 0.0)

    def torque(self, sample, dt=0.02):
        roll, pitch = self.imu.attitude(sample)
        d_roll = (roll - self.prev[0]) / dt
        d_pitch = (pitch - self.prev[1]) / dt
        self.prev = (roll, pitch)
        return -KP * roll - KD * d_roll, -KP * pitch - KD * d_pitch
