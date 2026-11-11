import numpy as np, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lqr
from scipy.linalg import expm

def max_delay(K, hz, ema=0.0, obs_lag_ticks=0):
    A, B = lqr.linear()
    dt = 0.0005
    Ad = expm(A*dt); Bd = np.linalg.solve(A + 1e-9*np.eye(4), (Ad - np.eye(4))) @ B if False else None
    M = np.zeros((5,5)); M[:4,:4]=A*dt; M[:4,4:]=B*dt; E=expm(M); Ad=E[:4,:4]; Bd=E[:4,4]
    per = int(round(1/hz/dt))
    for D in np.arange(0, 60.5, 0.5):
        d = int(D/0.5)
        s = np.array([0.01,0,0,0]); a=0; buf=[0.0]*(d+1); lat=s.copy(); u=0; tq=0
        peak=0
        for k in range(int(3/dt)):
            if k % per == 0:
                o = lat if obs_lag_ticks else s
                lat = s.copy()
                a = ema*a + (1-ema)*float(-(K@o))
            buf.append(a); cmd = buf.pop(0)
            tq += (cmd - tq)*dt/0.002
            s = Ad@s + Bd*tq
            if k > int(2/dt): peak=max(peak, abs(s[0]))
        if peak > 0.01 or not np.isfinite(peak):
            return D
    return 99

if __name__ == "__main__":
    for Q, Rw in [((60,1,6,1.5),1.0), ((300,3,6,1.5),0.3), ((1000,5,10,2),0.2)]:
        K = lqr.gains(100, Q, Rw)
        print(Q, Rw, K.round(2), [ (hz, max_delay(K,hz), max_delay(K,hz,obs_lag_ticks=1)) for hz in (100,200,300)])
