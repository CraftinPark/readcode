"""Reference: auto-range in lines, true integration time, gain capped at 8x, CAL from the REF LED."""
from station.sensor import MAX_GAIN, MAX_LINES, integration_us, set_gain, set_lines

BLACK = 64
SATURATED = 1000
WEAK = 100
CAL = 0.001


def measure(cam):
    lines, gain = set_lines(cam, MAX_LINES), set_gain(cam, 1)
    v = cam.capture()
    while v >= SATURATED and lines > 1:
        lines = set_lines(cam, lines // 2)
        v = cam.capture()
    while v - BLACK < WEAK and gain < MAX_GAIN:
        gain = set_gain(cam, gain * 2)
        v = cam.capture()
    return (v - BLACK) / (integration_us(lines) * gain * CAL)
