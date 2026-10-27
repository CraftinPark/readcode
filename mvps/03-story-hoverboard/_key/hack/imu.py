"""The tempting patch: special-case the version that broke. Fixes tonight's fleet, not the next update."""

PITCH_CONVENTION_CHANGED = "3.4"


class IMU:
    def __init__(self, firmware):
        self.firmware = firmware

    def attitude(self, sample):
        pitch = sample["raw_pitch"]
        if self.firmware >= PITCH_CONVENTION_CHANGED or self.firmware == "3.10":
            pitch = -pitch
        return sample["roll"], pitch
