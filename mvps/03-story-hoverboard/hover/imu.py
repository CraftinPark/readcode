"""Driver for the Kestrel-9 inertial unit on each patrol board.

Kestrel firmware before 3.4 reported pitch nose-up positive. From 3.4 the vendor switched to the
aviation convention (nose-down positive), so newer units need the sign turned around here.
"""

PITCH_CONVENTION_CHANGED = "3.4"


class IMU:
    def __init__(self, firmware):
        self.firmware = firmware

    def attitude(self, sample):
        """Turn a raw sample into the board's attitude, nose-up positive."""
        pitch = sample["raw_pitch"]
        if self.firmware >= PITCH_CONVENTION_CHANGED:
            pitch = -pitch
        return sample["roll"], pitch
