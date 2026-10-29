"""Tempting fix: "the new module counts exposure in ~29.6 us lines". Proportional only."""
EXPOSURE = 0x3500
GAIN = 0x3508
LINE_US = 29.63


def set_exposure_us(cam, us):
    lines = max(1, int(round(us / LINE_US)))
    cam.write(EXPOSURE, lines)
    return lines * LINE_US


def set_gain(cam, gain):
    cam.write(GAIN, int(round(gain * 16)))
    return gain
