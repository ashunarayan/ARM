"""PyTorch re-implementation of the rejected paper's full recipe (ml_model/iri_v3), used to measure how much
of its reported performance survives a clean protocol. Differences from the Keras original are limited to
framework defaults (weight initialisation); BatchNorm momentum is set to match Keras (0.99)."""
from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn as nn
from sklearn.isotonic import IsotonicRegression

from .legacy_recipe import compute_2d_sample_weights

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class _LegacyNet(nn.Module):
    def __init__(self):
        super().__init__()
        bn = lambda c: nn.BatchNorm1d(c, momentum=0.01, eps=1e-3)
        self.conv = nn.Sequential(
            nn.Conv1d(6, 12, 5, padding=2, groups=6), nn.ReLU(), bn(12), nn.MaxPool1d(2),
            nn.Conv1d(12, 48, 5, padding=2), nn.ReLU(), bn(48), nn.MaxPool1d(2),
            nn.Conv1d(48, 64, 3, padding=1), nn.ReLU(), bn(64))
        self.drop = nn.Dropout(0.3)
        self.ctx = nn.Sequential(nn.Linear(13, 32), nn.ReLU(), bn(32), nn.Dropout(0.2))
        self.head = nn.Sequential(nn.Linear(160, 64), nn.ReLU(), nn.Dropout(0.2), nn.Linear(64, 32), nn.ReLU(),
                                  nn.Linear(32, 1), nn.Softplus())

    def forward(self, s, c):
        h = self.conv(s.transpose(1, 2))
        h = self.drop(torch.cat([h.mean(-1), h.amax(-1)], 1))
        return self.head(torch.cat([h, self.ctx(c)], 1)).squeeze(-1)


def asym_huber(y, p, delta=2.0, ratio=4.0):
    e = y - p
    a = e.abs()
    q = torch.clamp(a, max=delta)
    base = 0.5 * q ** 2 + delta * (a - q)
    w = torch.where(e > 0, torch.full_like(e, ratio), torch.ones_like(e))
    return (w * base).mean()


class LegacyRecipe:
    name = "Legacy recipe (KN + asym. Huber + 2-D weights + oversampling + isotonic)"

    def __init__(self, seeds=(0, 1, 2, 3, 4), use_pica=True, batch=64, max_epochs=150, patience=15, faithful_weighting=True):
        # faithful_weighting=True reproduces a property of the original Keras code: the custom asymmetric loss
        # reduces to a scalar before Keras applies sample weights, so the 2-D weights only rescale each batch
        # loss by the batch-mean weight (verified in TF 2.10, see results/legacy_weighting_check.txt).
        self.seeds, self.use_pica, self.batch, self.max_epochs, self.patience = seeds, use_pica, batch, max_epochs, patience
        self.faithful_weighting = faithful_weighting

    def fit(self, S, C, y, S_val, C_val, y_val):
        # oversample IRI > 10 then 2-D inverse-frequency weights (exactly as trainer.py)
        sev = np.where(y > 10.0)[0]
        S = np.concatenate([S, S[sev]]); C = np.concatenate([C, C[sev]]); y = np.concatenate([y, y[sev]])
        w = compute_2d_sample_weights(C[:, 0], y)
        St, Ct = torch.tensor(S, dtype=torch.float32, device=DEVICE), torch.tensor(C, dtype=torch.float32, device=DEVICE)
        yt = torch.tensor(np.log1p(y), dtype=torch.float32, device=DEVICE); wt = torch.tensor(w, dtype=torch.float32, device=DEVICE)
        Sv, Cv = torch.tensor(S_val, dtype=torch.float32, device=DEVICE), torch.tensor(C_val, dtype=torch.float32, device=DEVICE)
        yv = torch.tensor(np.log1p(y_val), dtype=torch.float32, device=DEVICE)
        self.nets, self.isos = [], []
        for seed in self.seeds:
            torch.manual_seed(seed); np.random.seed(seed)
            net = _LegacyNet().to(DEVICE)
            opt = torch.optim.Adam(net.parameters(), lr=1e-3)
            sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=5)
            best, best_state, bad = np.inf, None, 0
            g = torch.Generator().manual_seed(seed)
            for ep in range(self.max_epochs):
                net.train()
                perm = torch.randperm(len(y), generator=g).to(DEVICE)
                for i in range(0, len(perm), self.batch):
                    b = perm[i:i + self.batch]
                    if len(b) < 2:
                        continue
                    opt.zero_grad()
                    p = net(St[b], Ct[b])
                    e = yt[b] - p; a = e.abs(); q = torch.clamp(a, max=2.0)
                    base = 0.5 * q ** 2 + 2.0 * (a - q)
                    per = torch.where(e > 0, 4.0 * base, base)
                    loss = per.mean() * wt[b].mean() if self.faithful_weighting else (wt[b] * per).mean()
                    loss.backward(); opt.step()
                net.eval()
                with torch.no_grad():
                    vl = float(asym_huber(yv, net(Sv, Cv)))
                sched.step(vl)
                if vl < best - 1e-6:
                    best, best_state, bad = vl, copy.deepcopy(net.state_dict()), 0
                else:
                    bad += 1
                    if bad >= self.patience:
                        break
            net.load_state_dict(best_state)
            self.nets.append(net)
            iso = None
            if self.use_pica:
                iso = IsotonicRegression(out_of_bounds="clip").fit(self._raw(net, S_val, C_val), y_val)
            self.isos.append(iso)
        return self

    def _raw(self, net, S, C):
        net.eval()
        with torch.no_grad():
            out = []
            for i in range(0, len(S), 4096):
                out.append(net(torch.tensor(S[i:i + 4096], dtype=torch.float32, device=DEVICE),
                               torch.tensor(C[i:i + 4096], dtype=torch.float32, device=DEVICE)).cpu().numpy())
        return np.expm1(np.concatenate(out))

    def predict_seeds(self, S, C, calibrated=True):
        out = []
        for net, iso in zip(self.nets, self.isos):
            r = self._raw(net, S, C)
            out.append(iso.predict(r) if (calibrated and iso is not None) else r)
        return np.array(out)
