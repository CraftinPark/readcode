# conveyor drive controller, fw 1.7
# R.K. 03/2011 -- ported from the 8051 version. do not change gains, tuned on line 3.
#
# called every 10 ms by the timer ISR.
#   enc   = encoder chip count register (QEI, 16 bit)
#   sp    = position setpoint from the PLC, motor counts
#   returns pwm duty -1000..1000

KP = 6
KI = 0
PWM_MAX = 1000


class Drive:
    def __init__(self):
        self.last = 0
        self.pos = 0
        self.integ = 0

    def isr(self, enc, sp):
        d = enc - self.last
        if d < 0:
            d = 0   # ignore the glitch
        self.last = enc
        self.pos = self.pos + d
        e = sp - self.pos
        self.integ = self.integ + KI * e
        u = KP * e + self.integ
        if u > PWM_MAX:
            u = PWM_MAX
        if u < -PWM_MAX:
            u = -PWM_MAX
        return int(u)
