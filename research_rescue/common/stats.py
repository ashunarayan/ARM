"""Metrics and cluster-bootstrap inference (see evaluation/FINAL_EVALUATION_PROTOCOL.md)."""
from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr, rankdata

FHWA_BANDS = (1.50, 2.68)   # m/km; good < 1.50 <= fair < 2.68 <= poor  (23 CFR 490 thresholds 95 / 170 in/mi)


def bands(x, cuts=FHWA_BANDS):
    return np.digitize(np.asarray(x, float), cuts)


def quadratic_kappa(a, b, k=3):
    a = np.asarray(a, int); b = np.asarray(b, int)
    O = np.zeros((k, k))
    np.add.at(O, (a, b), 1)
    w = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)], float) / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / max(O.sum(), 1)
    den = (w * E).sum()
    return float(1 - (w * O).sum() / den) if den > 0 else float("nan")


def _spearman(y, p):
    if np.std(y) == 0 or np.std(p) == 0:
        return float("nan")
    return float(np.corrcoef(rankdata(y), rankdata(p))[0, 1])


def metrics(y, p) -> dict:
    y = np.asarray(y, float); p = np.asarray(p, float)
    e = p - y
    ss = np.sum((y - y.mean()) ** 2)
    by, bp = bands(y), bands(p)
    return dict(n=int(len(y)), mae=float(np.mean(np.abs(e))), rmse=float(np.sqrt(np.mean(e ** 2))),
                bias=float(np.mean(e)), spearman=_spearman(y, p),
                r2=float(1 - np.sum(e ** 2) / ss) if ss > 0 else float("nan"),
                band_acc=float(np.mean(by == bp)), kappa=quadratic_kappa(by, bp))


def _cluster_index(clusters):
    u, inv = np.unique(np.asarray(clusters), return_inverse=True)
    members = [np.where(inv == c)[0] for c in range(len(u))]
    return members


def cluster_bootstrap(y, preds, clusters, B=2000, seed=0, stats=("mae", "rmse", "bias", "spearman", "r2", "kappa")):
    """preds: dict name -> array (n,) or (n_seeds, n). Returns dict name -> {stat: (point, lo, hi)}.
    For multi-seed arrays the statistic is averaged over seeds inside every resample."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, float)
    members = _cluster_index(clusters)
    C = len(members)
    P = {k: (np.atleast_2d(v)) for k, v in preds.items()}
    out = {k: {s: [] for s in stats} for k in P}
    point = {k: {s: float(np.mean([metrics(y, pp)[s] for pp in v])) for s in stats} for k, v in P.items()}
    for _ in range(B):
        idx = np.concatenate([members[c] for c in rng.integers(0, C, C)])
        for k, v in P.items():
            ms = [metrics(y[idx], pp[idx]) for pp in v]
            for s in stats:
                out[k][s].append(np.mean([m[s] for m in ms]))
    res = {}
    for k in P:
        res[k] = {s: (point[k][s], float(np.nanpercentile(out[k][s], 2.5)), float(np.nanpercentile(out[k][s], 97.5)))
                  for s in stats}
        res[k]["n_units"] = int(len(y)); res[k]["n_clusters"] = int(C)
    return res


def paired_diff(y, pa, pb, clusters, stat="mae", B=2000, seed=0):
    """Bootstrap CI and two-sided p-value for stat(pa) - stat(pb) with shared cluster resamples."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, float)
    pa, pb = np.atleast_2d(pa), np.atleast_2d(pb)
    members = _cluster_index(clusters)
    C = len(members)
    f = lambda idx, P: np.mean([metrics(y[idx], p[idx])[stat] for p in P])
    full = np.arange(len(y))
    d0 = f(full, pa) - f(full, pb)
    ds = []
    for _ in range(B):
        idx = np.concatenate([members[c] for c in rng.integers(0, C, C)])
        ds.append(f(idx, pa) - f(idx, pb))
    ds = np.array(ds)
    p = 2 * min(np.mean(ds <= 0), np.mean(ds >= 0))
    return dict(diff=float(d0), lo=float(np.percentile(ds, 2.5)), hi=float(np.percentile(ds, 97.5)), p=float(min(p, 1.0)))


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items); out = {}; running = 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)
        out[k] = running
    return out


def fmt_ci(t, nd=2):
    return f"{t[0]:.{nd}f} [{t[1]:.{nd}f}, {t[2]:.{nd}f}]"
