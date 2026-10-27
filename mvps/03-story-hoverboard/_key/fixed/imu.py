"""Reference fix: compare versions as numbers, not strings ("3.10" < "3.4" as text)."""

PITCH_CONVENTION_CHANGED = (3, 4)


def _version(firmware):
    return tuple(int(x) for x in firmware.split(".")[:2])


class IMU:
    def __init__(self, firmware):
        self.firmware = firmware

    def attitude(self, sample):
        """Turn a raw sample into the board's attitude, nose-up positive."""
        pitch = sample["raw_pitch"]
        if _version(self.firmware) >= PITCH_CONVENTION_CHANGED:
            pitch = -pitch
        return sample["roll"], pitch
