"""Measures one LED's luminous intensity (mcd) from the station camera.

Auto-ranging: start long, shorten until the spot is not saturated, then add gain if the signal is weak.
CAL is from the 2019 calibration against the lab's spectroradiometer.
"""
from station.sensor import set_exposure_us, set_gain

BLACK = 64          # ADU
SATURATED = 1000    # ADU, spot mean at or above this is clipped
WEAK = 100          # ADU above black
EXP_MAX_US = 30000
GAIN_MAX = 16
CAL = 0.001         # ADU per (mcd * us) at 1x, recalibrated on the REF LED


def measure(cam):
    exp_us, gain = EXP_MAX_US, 1
    set_gain(cam, gain)
    set_exposure_us(cam, exp_us)
    v = cam.capture()
    while v >= SATURATED and exp_us > 2:
        exp_us = set_exposure_us(cam, exp_us / 2)
        v = cam.capture()
    while v - BLACK < WEAK and gain < GAIN_MAX:
        gain = set_gain(cam, gain * 2)
        v = cam.capture()
    return (v - BLACK) / (exp_us * gain * CAL)
