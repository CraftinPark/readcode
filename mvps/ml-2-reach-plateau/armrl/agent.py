import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Normal


def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    nn.init.orthogonal_(layer.weight, std)
    nn.init.constant_(layer.bias, bias_const)
    return layer


def mlp(in_dim, hidden, out_dim, out_std, act=nn.Tanh):
    layers = []
    d = in_dim
    for h in hidden:
        layers += [layer_init(nn.Linear(d, h)), act()]
        d = h
    layers.append(layer_init(nn.Linear(d, out_dim), std=out_std))
    return nn.Sequential(*layers)


class ActorCritic(nn.Module):
    """Separate actor / critic MLPs, state independent log std.

    Actions are NOT squashed. The env clips to [-1, 1]; we keep the raw sample
    for log-probs. (We tried tanh squashing in August, see #29, slower and
    the log-det term kept blowing up near the boundary.)
    """

    def __init__(self, obs_dim, act_dim, hidden=(64, 64), init_log_std=-0.5):
        super().__init__()
        self.critic = mlp(obs_dim, hidden, 1, out_std=1.0)
        self.actor_mean = mlp(obs_dim, hidden, act_dim, out_std=0.01)
        self.actor_logstd = nn.Parameter(torch.full((1, act_dim), float(init_log_std)))

    def get_value(self, x):
        return self.critic(x).squeeze(-1)

    def dist(self, x):
        mean = self.actor_mean(x)
        logstd = self.actor_logstd.expand_as(mean)
        return Normal(mean, logstd.exp())

    def get_action_and_value(self, x, action=None):
        d = self.dist(x)
        if action is None:
            action = d.sample()
        logp = d.log_prob(action).sum(-1)
        ent = d.entropy().sum(-1)
        return action, logp, ent, self.get_value(x)

    @torch.no_grad()
    def act(self, x, deterministic=False):
        d = self.dist(x)
        return d.mean if deterministic else d.sample()
