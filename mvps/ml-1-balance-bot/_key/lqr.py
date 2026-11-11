"""LQR teacher for the balance policy (used only to train policy.pt)."""
import numpy as np
from scipy.linalg import solve_discrete_are, expm

MC, MP, L, IC, G, R, B_X = 0.40, 0.80, 0.08, 0.0025, 9.81, 0.035, 0.05
TAU_MAX = 0.40


def linear(mc=MC, mp=MP, l=L, ic=IC):
    M = mc + mp; J = ic + mp * l * l
    Mm = np.array([[M, mp * l], [mp * l, J]]); Minv = np.linalg.inv(Mm)
    # state [th, w, x, v]; generalized accel [xdd, thdd] = Minv @ ([F - b v, mp g l th])
    A = np.zeros((4, 4)); Bm = np.zeros((4, 1))
    A[0, 1] = 1; A[2, 3] = 1
    # contributions
    for row, gi in ((3, 0), (1, 1)):
        A[row, 0] = Minv[gi, 1] * mp * G * l
        A[row, 3] = Minv[gi, 0] * (-B_X)
        Bm[row, 0] = Minv[gi, 0] * TAU_MAX / R
    return A, Bm


def gains(hz=100, Q=(60, 1, 6, 1.5), Rw=1.0):
    A, B = linear()
    dt = 1 / hz
    n = 4
    Mx = np.zeros((n + 1, n + 1)); Mx[:n, :n] = A * dt; Mx[:n, n:] = B * dt
    E = expm(Mx); Ad = E[:n, :n]; Bd = E[:n, n:]
    P = solve_discrete_are(Ad, Bd, np.diag(Q), np.array([[Rw]]))
    K = np.linalg.solve(Bd.T @ P @ Bd + Rw, Bd.T @ P @ Ad)
    return K[0]


if __name__ == "__main__":
    A, B = linear()
    print(np.linalg.eigvals(A))
    K = gains()
    print("K", K)
    print("closed-loop eig", np.linalg.eigvals(A - B @ K[None, :]))
