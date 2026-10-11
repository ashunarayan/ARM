"""Paired comparisons across LiRA-CD experiments on identical held-out units (saved predictions only).

Family Z (Holm within family): every simulation-only model vs. the real-data LightGBM reference
('M3 LightGBM (all features)') and vs. the real-data speed-only model, segment level, cluster bootstrap over segments.
Output: results/lira/compare_zeroshot_vs_real.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.stats import paired_diff, holm, metrics  # noqa: E402
from common.paths import RESULTS  # noqa: E402

REFS = ["M3 LightGBM (all features)", "M1 speed-only (LightGBM on speed features)", "M2c RMS/v^alpha (alpha fitted on training data)"]


def seg_preds(path, models=None):
    P = pd.read_csv(path)
    if models is not None:
        P = P[P.model.isin(models)]
    s = P.groupby(["model", "segment", "seed"]).agg(pred=("pred", "mean"), y=("y", "first"), fold=("fold", "first")).reset_index()
    return s.groupby(["model", "segment"]).agg(pred=("pred", "mean"), y=("y", "first"), fold=("fold", "first")).reset_index()


def main():
    L = seg_preds(os.path.join(RESULTS, "predictions", "lira_ladder.csv"), REFS)
    Z = seg_preds(os.path.join(RESULTS, "predictions", "lira_zeroshot.csv"))
    allp = pd.concat([L, Z])
    wide = allp.pivot_table(index="segment", columns="model", values="pred")
    y = allp.groupby("segment").y.first().reindex(wide.index).to_numpy()
    fold = allp.groupby("segment").fold.first().reindex(wide.index).to_numpy()
    rows = []
    for ref in REFS:
        pv = {}
        for m in Z.model.unique():
            d = paired_diff(y, wide[m].to_numpy(), wide[ref].to_numpy(), wide.index.to_numpy(), "mae", B=2000)
            pv[m] = d["p"]
            rows.append(dict(model=m, reference=ref, mae_model=metrics(y, wide[m].to_numpy())["mae"],
                             mae_ref=metrics(y, wide[ref].to_numpy())["mae"], **{f"dmae_{k}": v for k, v in d.items()}))
        adj = holm(pv)
        for r in rows:
            if r["reference"] == ref:
                r["p_holm"] = adj[r["model"]]
    C = pd.DataFrame(rows)
    # per road class (urban / motorway) point estimates
    for cls, m in [("urban", np.char.startswith(fold.astype(str), "CPH")), ("motorway", ~np.char.startswith(fold.astype(str), "CPH"))]:
        C[f"mae_model_{cls}"] = [metrics(y[m], wide[r.model].to_numpy()[m])["mae"] for r in C.itertuples()]
        C[f"mae_ref_{cls}"] = [metrics(y[m], wide[r.reference].to_numpy()[m])["mae"] for r in C.itertuples()]
    C.to_csv(os.path.join(RESULTS, "lira", "compare_zeroshot_vs_real.csv"), index=False)
    show = C[C.reference == REFS[0]][["model", "mae_model", "mae_ref", "dmae_diff", "dmae_lo", "dmae_hi", "p_holm", "mae_model_urban", "mae_model_motorway"]]
    print(show.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
