"""KX-219 driver, measured on the bench: EXPOSURE counts lines of 29.63 us plus a fixed 11.5 us, clamped at
1121 lines in 1080p30; analog gain stops at 8x (GAIN 0x80)."""
EXPOSURE = 0x3500
GAIN = 0x3508
LINE_US = 29.63
OFFSET_US = 11.5
MAX_LINES = 1121
MAX_GAIN = 8


def set_lines(cam, lines):
    lines = max(1, min(int(lines), MAX_LINES))
    cam.write(EXPOSURE, lines)
    return lines


def integration_us(lines):
    return lines * LINE_US + OFFSET_US


def set_gain(cam, gain):
    gain = min(gain, MAX_GAIN)
    cam.write(GAIN, int(round(gain * 16)))
    return gain
