"""Post-hoc analyses of saved LiRA-CD test predictions (no retraining, no model selection):

  within-route ranking  Spearman(pred, IRI) per held-out route at segment level, and the PARTIAL Spearman controlling
                        for segment mean speed (roughness information beyond the speed shortcut)
  passes needed         segment-level MAE when averaging n randomly chosen passes per segment (crowdsourcing)
  speed bands           pass-level MAE by speed band on urban routes
Outputs: results/lira/analysis_*.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.paths import RESULTS, PROCESSED  # noqa: E402

OUT = os.path.join(RESULTS, "lira")
KEY = ["M0 constant (training median)", "M1 speed-only (LightGBM on speed features)", "M2a RMS only (alpha=0)",
       "M2c RMS/v^alpha (alpha fitted on training data)", "M3 LightGBM (all features)", "M3 LightGBM (no speed features)",
       "M4 MLP", "M5 1D-CNN", "M5 1D-CNN (no speed input)"]


def partial_spearman(x, y, z):
    """Spearman partial correlation of x and y given z (rank-based residual correlation)."""
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    Z = np.column_stack([np.ones_like(rz), rz])
    ex = rx - Z @ np.linalg.lstsq(Z, rx, rcond=None)[0]; ey = ry - Z @ np.linalg.lstsq(Z, ry, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1])


def boot(f, n, B=1000, seed=0):
    rng = np.random.default_rng(seed)
    vals = [f(rng.integers(0, n, n)) for _ in range(B)]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    P = pd.read_csv(os.path.join(RESULTS, "predictions", "lira_ladder.csv"))
    U = pd.read_csv(os.path.join(PROCESSED, "lira", "units.csv"))
    sp = U.groupby("segment").v_mean.mean()
    P = P[P.model.isin(KEY)]
    pm = P.groupby(["model", "segment", "task", "pass_id"], sort=False).agg(y=("y", "first"), pred=("pred", "mean"), fold=("fold", "first")).reset_index()
    seg = pm.groupby(["model", "segment"]).agg(y=("y", "first"), pred=("pred", "mean"), fold=("fold", "first")).reset_index()
    seg["v"] = seg.segment.map(sp)
    rows = []
    for (m, r), g in seg.groupby(["model", "fold"]):
        y, p, v = g.y.to_numpy(), g.pred.to_numpy(), g.v.to_numpy()
        rho = float(np.corrcoef(rankdata(p), rankdata(y))[0, 1]) if np.std(p) > 0 else np.nan
        prho = partial_spearman(p, y, v) if np.std(p) > 0 else np.nan
        lo, hi = boot(lambda i: partial_spearman(p[i], y[i], v[i]) if np.std(p[i]) > 0 else np.nan, len(y))
        rows.append(dict(model=m, route=r, n_segments=len(g), spearman=rho, partial_spearman_given_speed=prho, partial_lo=lo, partial_hi=hi,
                         speed_iri_spearman=float(np.corrcoef(rankdata(v), rankdata(y))[0, 1])))
    W = pd.DataFrame(rows)
    W.to_csv(os.path.join(OUT, "analysis_within_route_ranking.csv"), index=False)
    print(W.pivot(index="model", columns="route", values="partial_spearman_given_speed").reindex(KEY).round(2).to_string())
    # passes needed
    rng = np.random.default_rng(0); rows = []
    for m in ["M2c RMS/v^alpha (alpha fitted on training data)", "M3 LightGBM (all features)", "M3 LightGBM (no speed features)", "M5 1D-CNN"]:
        g = pm[pm.model == m]
        by = {s: (d.pred.to_numpy(), d.y.iloc[0], d.fold.iloc[0]) for s, d in g.groupby("segment")}
        for n in [1, 2, 3, 5, 8]:
            for rep in range(20):
                errs = {"urban": [], "motorway": []}
                for s, (pp, y, f) in by.items():
                    if len(pp) < n:
                        continue
                    errs["urban" if f.startswith("CPH") else "motorway"].append(abs(rng.choice(pp, n, replace=False).mean() - y))
                for k, e in errs.items():
                    rows.append(dict(model=m, n_passes=n, rep=rep, road=k, mae=float(np.mean(e)), n_segments=len(e)))
    N = pd.DataFrame(rows).groupby(["model", "road", "n_passes"]).agg(mae=("mae", "mean"), sd=("mae", "std"), n_segments=("n_segments", "mean")).reset_index()
    N.to_csv(os.path.join(OUT, "analysis_passes_needed.csv"), index=False)
    print(N.round(3).to_string(index=False))
    # speed bands (urban, pass level)
    pm["v"] = pm.merge(U[["segment", "task", "pass_id", "v_mean"]].drop_duplicates(["segment", "task", "pass_id"]),
                       on=["segment", "task", "pass_id"], how="left").v_mean.to_numpy()
    ur = pm[pm.fold.str.startswith("CPH")].copy()
    ur["band"] = pd.cut(3.6 * ur.v, [0, 20, 30, 40, 50, 60, 80, 200])
    S = ur.groupby(["model", "band"], observed=True).apply(lambda d: pd.Series(dict(mae=np.mean(np.abs(d.pred - d.y)), bias=np.mean(d.pred - d.y), n=len(d))), include_groups=False).reset_index()
    S.to_csv(os.path.join(OUT, "analysis_urban_speed_bands.csv"), index=False)


if __name__ == "__main__":
    main()
