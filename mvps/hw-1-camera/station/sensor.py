"""Sensor driver for test station 2. Register map from the KX-110 datasheet, rev C."""
EXPOSURE = 0x3500   # integration time, microseconds
GAIN = 0x3508       # analog gain, 1/16 steps (0x10 = 1x)


def set_exposure_us(cam, us):
    cam.write(EXPOSURE, int(round(us)))
    return us


def set_gain(cam, gain):
    cam.write(GAIN, int(round(gain * 16)))
    return gain
