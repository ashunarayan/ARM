"""Baseline ladder M0-M6 with a common interface.

All models predict IRI (m/km) and are trained on log(IRI) where applicable. Inputs:
  D["feat"]  (N, F) engineered window features (common/features.py, names in D["feature_names"])
  D["seq"]   (N, 400, 1) spatially resampled dynamic vertical acceleration (100 m window)
  D["y"]     (N,) IRI labels, D["group"] (N,) segment identifiers for grouped inner splits
"""
from __future__ import annotations

import copy
import json
import os

import numpy as np
import torch
import torch.nn as nn
from lightgbm import LGBMRegressor

from .features import FEATURE_NAMES

EPS = 1e-3
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "models.json")
CFG = json.load(open(CFG_PATH)) if os.path.exists(CFG_PATH) else {}
FI = {n: i for i, n in enumerate(FEATURE_NAMES)}
SPEED_FEATS = ["log_v_mean", "v_cv"]


def ly(y):
    return np.log(np.asarray(y, float) + EPS)


def iy(z):
    return np.clip(np.exp(z) - EPS, 0.0, None)


# ----------------------------------------------------------------------------------------------
class Constant:
    name = "M0 constant (training median)"

    def fit(self, D, inner=None):
        self.c = float(np.median(D["y"])); return self

    def predict(self, D):
        return np.full(len(D["y"]), self.c)


class PhysicsIndex:
    """log IRI = a + b * log(RMS) - b*alpha*log(v); alpha fixed or fitted (alpha=None)."""

    def __init__(self, alpha=None, feature="log_rms", label=None):
        self.alpha, self.feature = alpha, feature
        self.name = label or ("M2 physics index, alpha fitted" if alpha is None else f"M2 physics index, alpha={alpha:g}")

    def _X(self, D):
        lr = D["feat"][:, FI[self.feature]]; lv = D["feat"][:, FI["log_v_mean"]]
        if self.alpha is None:
            return np.column_stack([np.ones(len(lr)), lr, lv])
        return np.column_stack([np.ones(len(lr)), lr - self.alpha * lv])

    def fit(self, D, inner=None):
        X = self._X(D)
        self.coef, *_ = np.linalg.lstsq(X, ly(D["y"]), rcond=None)
        self.alpha_hat = float(-self.coef[2] / self.coef[1]) if self.alpha is None and abs(self.coef[1]) > 1e-9 else self.alpha
        return self

    def predict(self, D):
        return iy(self._X(D) @ self.coef)

    def recalibrate_intercept(self, D):
        """Keep slope/alpha (e.g. learned in simulation); refit only the intercept on (few) real data."""
        resid = ly(D["y"]) - self._X(D)[:, 1:] @ self.coef[1:]
        self.coef = self.coef.copy(); self.coef[0] = float(np.median(resid))
        return self


class GBM:
    def __init__(self, features=None, label="M3 LightGBM (all features)", grid=None):
        self.features = features or list(FEATURE_NAMES)
        self.name = label
        self.grid = grid or CFG.get("gbm_grid", [dict(num_leaves=nl, min_child_samples=mc) for nl in (7, 15, 31) for mc in (20, 60)])

    def _make(self, p):
        return LGBMRegressor(n_estimators=400, learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.9,
                             reg_lambda=1.0, verbose=-1, random_state=0, **p)

    def _X(self, D):
        return D["feat"][:, [FI[f] for f in self.features]]

    def fit(self, D, inner=None, weights=None):
        """inner: list of (train_idx, val_idx) for config selection (grouped); None -> first config."""
        best, self.inner_scores = self.grid[0], {}
        if inner and len(self.grid) > 1:
            for k, p in enumerate(self.grid):
                errs = []
                for tr, va in inner:
                    m = self._make(p).fit(self._X(D)[tr], ly(D["y"][tr]))
                    errs.append(np.mean(np.abs(iy(m.predict(self._X(D)[va])) - D["y"][va])))
                self.inner_scores[k] = float(np.mean(errs))
            best = self.grid[min(self.inner_scores, key=self.inner_scores.get)]
        self.params = best
        self.m = self._make(best).fit(self._X(D), ly(D["y"]), sample_weight=weights)
        return self

    def predict(self, D):
        return iy(self.m.predict(self._X(D)))


class SpeedOnly(GBM):
    def __init__(self):
        super().__init__(features=SPEED_FEATS, label="M1 speed-only (LightGBM on speed features)")


# ----------------------------------------------------------------------------------------------
class _MLP(nn.Module):
    def __init__(self, d_in, h=(64, 32), drop=0.1):
        super().__init__()
        layers, d = [], d_in
        for k in h:
            layers += [nn.Linear(d, k), nn.ReLU(), nn.Dropout(drop)]; d = k
        layers += [nn.Linear(d, 1)]
        self.net = nn.Sequential(*layers)

    def forward(self, x, s=None, c=None):
        return self.net(x).squeeze(-1)


class _CNN(nn.Module):
    """Legacy dual-branch architecture (depthwise conv -> 48 -> 64 filters, GAP+GMP, context MLP)."""

    def __init__(self, c_in=1, d_ctx=2, use_ctx=True):
        super().__init__()
        self.use_ctx = use_ctx and d_ctx > 0
        self.conv = nn.Sequential(
            nn.Conv1d(c_in, 2 * c_in, 5, padding=2, groups=c_in), nn.ReLU(), nn.BatchNorm1d(2 * c_in), nn.MaxPool1d(2),
            nn.Conv1d(2 * c_in, 48, 5, padding=2), nn.ReLU(), nn.BatchNorm1d(48), nn.MaxPool1d(2),
            nn.Conv1d(48, 64, 3, padding=1), nn.ReLU(), nn.BatchNorm1d(64))
        self.drop = nn.Dropout(0.3)
        d = 128
        if self.use_ctx:
            self.ctx = nn.Sequential(nn.Linear(d_ctx, 32), nn.ReLU(), nn.BatchNorm1d(32), nn.Dropout(0.2)); d += 32
        self.head = nn.Sequential(nn.Linear(d, 64), nn.ReLU(), nn.Dropout(0.2), nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x, s, c):
        h = self.conv(s.transpose(1, 2))
        h = self.drop(torch.cat([h.mean(-1), h.amax(-1)], 1))
        if self.use_ctx:
            h = torch.cat([h, self.ctx(c)], 1)
        return self.head(h).squeeze(-1)


class TorchModel:
    """Shared trainer: Huber loss on log IRI, Adam, grouped early stopping, n seeds averaged at predict."""

    def __init__(self, kind="cnn", use_speed=True, seeds=(0, 1, 2, 3, 4), label=None, max_epochs=150, patience=15,
                 lr=1e-3, wd=1e-4, batch=128, mlp_hidden=(64, 32), features=None):
        self.kind, self.use_speed, self.seeds = kind, use_speed, tuple(seeds)
        self.max_epochs, self.patience, self.lr, self.wd, self.batch = max_epochs, patience, lr, wd, batch
        self.mlp_hidden = mlp_hidden
        self.features = features or (list(FEATURE_NAMES) if use_speed else [f for f in FEATURE_NAMES if f not in SPEED_FEATS])
        self.name = label or {"cnn": "M5 1D-CNN" + ("" if use_speed else " (no speed input)"),
                              "mlp": "M4 MLP" + ("" if use_speed else " (no speed input)")}[kind]
        self.models = []

    # ---- tensors ------------------------------------------------------------------------------
    def _tensors(self, D):
        X = (D["feat"][:, [FI[f] for f in self.features]] - self.mu_x) / self.sd_x
        S = D["seq"][:, :, :1] / self.sd_s
        C = (D["feat"][:, [FI[f] for f in SPEED_FEATS]] - self.mu_c) / self.sd_c
        return [torch.tensor(a, dtype=torch.float32) for a in (X, S, C)]

    def _norm(self, D):
        X = D["feat"][:, [FI[f] for f in self.features]]
        self.mu_x, self.sd_x = X.mean(0), X.std(0) + 1e-6
        self.sd_s = float(np.std(D["seq"][:, :, 0])) + 1e-9
        C = D["feat"][:, [FI[f] for f in SPEED_FEATS]]
        self.mu_c, self.sd_c = C.mean(0), C.std(0) + 1e-6

    def _new(self):
        if self.kind == "mlp":
            return _MLP(len(self.features), self.mlp_hidden)
        return _CNN(1, len(SPEED_FEATS), use_ctx=self.use_speed)

    def _train_one(self, seed, T, y, tr, va, init_state=None, epochs=None, lr=None):
        torch.manual_seed(seed); np.random.seed(seed)
        net = self._new().to(DEVICE)
        if init_state is not None:
            net.load_state_dict(init_state)
        opt = torch.optim.Adam(net.parameters(), lr=lr or self.lr, weight_decay=self.wd)
        sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=5)
        lossf = nn.HuberLoss(delta=0.5)
        Xt, St, Ct = [t.to(DEVICE) for t in T]
        yt = torch.tensor(ly(y), dtype=torch.float32, device=DEVICE)
        best, best_state, bad = np.inf, None, 0
        g = torch.Generator(device="cpu").manual_seed(seed)
        n_ep = epochs or self.max_epochs
        for ep in range(n_ep):
            net.train()
            perm = tr[torch.randperm(len(tr), generator=g).numpy()]
            for i in range(0, len(perm), self.batch):
                b = perm[i:i + self.batch]
                if len(b) < 2:
                    continue
                opt.zero_grad()
                loss = lossf(net(Xt[b], St[b], Ct[b]), yt[b])
                loss.backward(); opt.step()
            if va is None or len(va) == 0:
                continue
            net.eval()
            with torch.no_grad():
                vl = float(lossf(net(Xt[va], St[va], Ct[va]), yt[va]))
            sched.step(vl)
            if vl < best - 1e-5:
                best, best_state, bad = vl, copy.deepcopy(net.state_dict()), 0
            else:
                bad += 1
                if bad >= self.patience:
                    break
        if best_state is not None:
            net.load_state_dict(best_state)
        return net

    def fit(self, D, inner=None, val_frac=0.2, init_states=None, epochs=None, lr=None, keep_norm=False, val_idx=None):
        if not keep_norm:
            self._norm(D)
        T = self._tensors(D)
        n = len(D["y"])
        if val_idx is not None:  # explicit inner-validation units (e.g. held-out trips)
            va = np.asarray(val_idx); tr = np.setdiff1d(np.arange(n), va)
        elif epochs is None:   # grouped early-stopping split
            rng = np.random.default_rng(12345)
            groups = np.unique(D["group"])
            va_g = set(rng.choice(groups, max(1, int(round(val_frac * len(groups)))), replace=False).tolist())
            va = np.array([i for i in range(n) if D["group"][i] in va_g]); tr = np.array([i for i in range(n) if D["group"][i] not in va_g])
        else:
            tr, va = np.arange(n), None
        self.models = []
        for k, s in enumerate(self.seeds):
            init = init_states[k] if init_states is not None else None
            self.models.append(self._train_one(s, T, D["y"], tr, va, init_state=init, epochs=epochs, lr=lr))
        return self

    def predict_seeds(self, D):
        T = [t.to(DEVICE) for t in self._tensors(D)]
        out = []
        for net in self.models:
            net.eval()
            with torch.no_grad():
                z = torch.cat([net(T[0][i:i + 4096], T[1][i:i + 4096], T[2][i:i + 4096]) for i in range(0, len(D["y"]), 4096)])
            out.append(iy(z.cpu().numpy()))
        return np.array(out)

    def predict(self, D):
        return self.predict_seeds(D).mean(0)

    def states(self):
        return [copy.deepcopy(m.state_dict()) for m in self.models]


def standard_ladder(fast: bool = False):
    """Models evaluated in every domain (fast=True drops the neural models)."""
    L = [Constant(), SpeedOnly(), PhysicsIndex(0.0, label="M2a RMS only (alpha=0)"),
         PhysicsIndex(0.5, label="M2b RMS/v^0.5"), PhysicsIndex(None, label="M2c RMS/v^alpha (alpha fitted on training data)"),
         PhysicsIndex(2.0, label="M2d RMS*(v_ref/v)^2 (legacy exponent, gravity removed)"),
         GBM(), GBM(features=[f for f in FEATURE_NAMES if f not in SPEED_FEATS], label="M3 LightGBM (no speed features)")]
    if not fast:
        L += [TorchModel("mlp"), TorchModel("cnn"), TorchModel("cnn", use_speed=False)]
    return L
