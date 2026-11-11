"""How policy/policy.pt was made (not shipped to the player): behaviour cloning of an LQR teacher designed on
the training sim's linearised model at 100 Hz, over a broad state distribution. The result behaves like a
saturated linear state-feedback policy, as a well-trained balance policy does near upright.

    python _key/train_policy.py
"""
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import lqr  # noqa: E402
from policy.net import OBS_SCALE, PolicyNet  # noqa: E402

torch.manual_seed(0)
rng = np.random.default_rng(0)
K = lqr.gains()
N = 200_000
S = np.stack([rng.normal(0, 0.12, N), rng.normal(0, 1.2, N), rng.normal(0, 0.25, N), rng.normal(0, 0.5, N)], 1)
S[: N // 4] *= 0.15  # dense near upright
Y = np.tanh(-(S @ K))
X = torch.tensor((S / OBS_SCALE).astype(np.float32))
Yt = torch.tensor(Y.astype(np.float32))[:, None]
net = PolicyNet()
opt = torch.optim.Adam(net.parameters(), lr=3e-3)
for it in range(4000):
    i = torch.randint(0, N, (2048,))
    loss = ((net(X[i]) - Yt[i]) ** 2).mean()
    opt.zero_grad(); loss.backward(); opt.step()
    if it == 3000:
        for g in opt.param_groups:
            g["lr"] = 5e-4
    if it % 1000 == 0:
        print(it, float(loss))
with torch.no_grad():
    err = (net(X[:20000]) - Yt[:20000]).abs()
print("mean abs err", float(err.mean()), "max", float(err.max()))
torch.save(net.state_dict(), os.path.join(ROOT, "policy", "policy.pt"))
print("saved")
