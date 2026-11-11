"""PPO-clip update. Started from the cleanrl single-file version, split up in
the 2026-10 refactor.
"""
import numpy as np
import torch
import torch.nn as nn


def explained_variance(y_pred, y_true):
    var_y = np.var(y_true)
    return np.nan if var_y == 0 else 1.0 - np.var(y_true - y_pred) / var_y


class PPO:
    def __init__(self, agent, cfg):
        self.agent = agent
        self.cfg = cfg
        self.optimizer = torch.optim.Adam(agent.parameters(), lr=cfg.lr, eps=1e-5)

    def set_lr(self, lr):
        for g in self.optimizer.param_groups:
            g["lr"] = lr

    def update(self, buf):
        cfg = self.cfg
        if cfg.norm_adv:
            # once over the whole batch instead of per minibatch (see changelog)
            buf.normalize_advantages()
        b = buf.flat()
        if cfg.verbose > 1:
            print("  dbg adv %.3f +- %.3f  ret %.3f  v %.3f" % (
                b["advantages"].mean(), b["advantages"].std(), b["returns"].mean(), b["values"].mean()))
        B = b["obs"].shape[0]
        mb_size = B // cfg.n_minibatches
        idxs = np.arange(B)

        clipfracs = []
        stats = {}
        approx_kl = torch.tensor(0.0)
        for epoch in range(cfg.update_epochs):
            np.random.shuffle(idxs)
            for start in range(0, B, mb_size):
                mb = idxs[start:start + mb_size]

                _, newlogp, entropy, newvalue = self.agent.get_action_and_value(
                    b["obs"][mb], b["actions"][mb]
                )
                logratio = newlogp - b["logprobs"][mb]
                ratio = logratio.exp()

                with torch.no_grad():
                    # http://joschu.net/blog/kl-approx.html
                    approx_kl = ((ratio - 1) - logratio).mean()
                    clipfracs.append(((ratio - 1.0).abs() > cfg.clip_coef).float().mean().item())

                mb_adv = b["advantages"][mb]

                pg_loss1 = -mb_adv * ratio
                pg_loss2 = -mb_adv * torch.clamp(ratio, 1 - cfg.clip_coef, 1 + cfg.clip_coef)
                pg_loss = torch.max(pg_loss1, pg_loss2).mean()

                if cfg.clip_vloss:
                    v_unclipped = (newvalue - b["returns"][mb]) ** 2
                    v_clipped = b["values"][mb] + torch.clamp(
                        newvalue - b["values"][mb], -cfg.clip_coef, cfg.clip_coef
                    )
                    v_loss = 0.5 * torch.max(v_unclipped, (v_clipped - b["returns"][mb]) ** 2).mean()
                else:
                    v_loss = 0.5 * ((newvalue - b["returns"][mb]) ** 2).mean()

                ent_loss = entropy.mean()
                loss = pg_loss - cfg.ent_coef * ent_loss + cfg.vf_coef * v_loss

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.agent.parameters(), cfg.max_grad_norm)
                self.optimizer.step()

            if cfg.target_kl is not None and approx_kl > cfg.target_kl:
                break

        y_pred = b["values"].numpy()
        y_true = b["returns"].numpy()
        stats["loss/policy"] = pg_loss.item()
        stats["loss/value"] = v_loss.item()
        stats["loss/entropy"] = ent_loss.item()
        stats["approx_kl"] = approx_kl.item()
        stats["clipfrac"] = float(np.mean(clipfracs))
        stats["explained_var"] = float(explained_variance(y_pred, y_true))
        stats["epochs_run"] = epoch + 1
        return stats
