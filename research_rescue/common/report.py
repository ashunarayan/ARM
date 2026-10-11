"""Uniform result reporting: per-model metrics with cluster-bootstrap CIs and paired differences."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import cluster_bootstrap, paired_diff, holm


def evaluate(y, preds: dict, clusters, ref: str | None = None, B: int = 2000, seed: int = 0, label: str = "") -> pd.DataFrame:
    """preds: name -> (n,) or (n_seeds, n). Returns one row per model."""
    cb = cluster_bootstrap(y, preds, clusters, B=B, seed=seed)
    rows = []
    for k, r in cb.items():
        P = np.atleast_2d(preds[k])
        row = dict(experiment=label, model=k, n_units=r["n_units"], n_clusters=r["n_clusters"], n_seeds=P.shape[0])
        for s in ("mae", "rmse", "bias", "spearman", "r2", "kappa"):
            row[s], row[s + "_lo"], row[s + "_hi"] = r[s]
        if P.shape[0] > 1:
            per_seed = [np.mean(np.abs(p - y)) for p in P]
            row["mae_seed_sd"] = float(np.std(per_seed))
        rows.append(row)
    df = pd.DataFrame(rows)
    if ref is not None and ref in preds:
        pv, diffs = {}, {}
        for k in preds:
            if k == ref:
                continue
            d = paired_diff(y, preds[k], preds[ref], clusters, "mae", B=B, seed=seed + 1)
            diffs[k] = d; pv[k] = d["p"]
        adj = holm(pv)
        df["dmae_vs_ref"] = df.model.map(lambda k: diffs[k]["diff"] if k in diffs else 0.0)
        df["dmae_lo"] = df.model.map(lambda k: diffs[k]["lo"] if k in diffs else 0.0)
        df["dmae_hi"] = df.model.map(lambda k: diffs[k]["hi"] if k in diffs else 0.0)
        df["p_holm"] = df.model.map(lambda k: adj.get(k, np.nan))
        df["reference"] = ref
    return df


def fmt(df: pd.DataFrame, cols=("mae", "rmse", "spearman", "kappa"), nd=2) -> pd.DataFrame:
    out = df[["model"]].copy()
    for c in cols:
        out[c] = [f"{a:.{nd}f} [{b:.{nd}f}, {cc:.{nd}f}]" for a, b, cc in zip(df[c], df[c + "_lo"], df[c + "_hi"])]
    if "dmae_vs_ref" in df:
        out["dMAE vs ref"] = [("ref" if m == r else f"{a:+.2f} [{b:+.2f}, {c:+.2f}] " + (f"p={p:.3f}" if p >= 0.0005 else "p<0.001"))
                              for m, r, a, b, c, p in zip(df.model, df.reference, df.dmae_vs_ref, df.dmae_lo, df.dmae_hi, df.p_holm)]
    return out
