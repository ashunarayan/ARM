"""Revision v2, E5/E6 summary (PROTOCOL_V2.md, Section 8): paired per-draw comparison with real-only training.

For every k and draw d the v1 block sampler picks the same k km of training-route blocks in R3 (simreal_variants.py),
R4 (value_of_simulation.py) and E5 (value_of_simulation_variants.py), so each simulation arm can be paired with
`real_only` (LightGBM on the real passes over those blocks) draw by draw. Pooled segment MAE per draw = n_seg-weighted
mean over the four held-out routes.

Arms:  sim_all_cal  simulation on all training-route profiles + level offset from the k km of real passes (R3, E6)
       sim_all_aff  same with an affine map (R3)
       sim_same     simulation on the profiles of the same k km only (R4 for V0, E5 for V1-V8)
       sim_same_cal sim_same + level offset from the same k km of real passes
Every arm is also paired with `real_only_index` (E9: the three-parameter vibration index fitted on the same k km,
value_real_index.py), a comparator that suits very small samples better than LightGBM.
Output: results/v2/paired_vs_real.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT  # noqa: E402


def pooled(D, keys):
    D = D.assign(w=D.seg_mae * D.n_seg, wb=D.seg_bias * D.n_seg)
    a = D.groupby(keys + ["draw"]).agg(w=("w", "sum"), wb=("wb", "sum"), n=("n_seg", "sum"), nf=("fold", "nunique")).reset_index()
    assert (a.nf == 4).all(), "every draw must cover the four held-out routes"
    a["mae"] = a.w / a.n; a["bias"] = a.wb / a.n
    return a.drop(columns=["w", "wb", "n", "nf"])


def main():
    R4 = pd.read_csv(os.path.join(OUT, "value_of_simulation.csv"))
    real = pooled(R4[R4.arm == "real_only"], ["k_km"]).rename(columns={"mae": "real_mae", "bias": "real_bias"})
    parts = []
    C = pd.read_csv(os.path.join(OUT, "variants_calibration.csv"))
    C = C[C.model == "GBM"].copy()
    C["arm"] = C.calib.map({"intercept": "sim_all_cal", "affine": "sim_all_aff"})
    parts.append(pooled(C, ["vid", "arm", "k_km"]))
    v0 = R4[R4.arm.isin(["sim_same", "sim_same_cal"])].assign(vid="V0")
    parts.append(pooled(v0, ["vid", "arm", "k_km"]))
    f5 = os.path.join(OUT, "value_of_simulation_variants.csv")
    if os.path.exists(f5):
        parts.append(pooled(pd.read_csv(f5), ["vid", "arm", "k_km"]))
    else:
        print("E5 file missing - sim_same of V1-V8 not included")
    A = pd.concat(parts, ignore_index=True).merge(real, on=["k_km", "draw"], how="inner", validate="many_to_one")
    A["diff"] = A.mae - A.real_mae
    fi = os.path.join(OUT, "value_real_index.csv")
    if os.path.exists(fi):
        ridx = pooled(pd.read_csv(fi), ["k_km"]).rename(columns={"mae": "real_idx_mae", "bias": "real_idx_bias"})
        A = A.merge(ridx, on=["k_km", "draw"], how="left", validate="many_to_one")
        A["diff_idx"] = A.mae - A.real_idx_mae
    else:
        print("E9 file missing - no comparison with the real-only index")
        A["real_idx_mae"] = np.nan; A["diff_idx"] = np.nan
    rows = []
    for (vid, arm, k), g in A.groupby(["vid", "arm", "k_km"]):
        rows.append(dict(vid=vid, arm=arm, k_km=int(k), n_draws=len(g), mae=g.mae.mean(), mae_lo=np.percentile(g.mae, 2.5),
                         mae_hi=np.percentile(g.mae, 97.5), bias=g.bias.mean(), real_mae=g.real_mae.mean(),
                         diff=g["diff"].mean(), diff_lo=np.percentile(g["diff"], 2.5), diff_hi=np.percentile(g["diff"], 97.5),
                         n_better=int((g["diff"] < 0).sum()), real_idx_mae=g.real_idx_mae.mean(),
                         diff_idx=g.diff_idx.mean(), n_better_idx=int((g.diff_idx < 0).sum())))
    S = pd.DataFrame(rows)
    S.to_csv(os.path.join(OUT, "paired_vs_real.csv"), index=False)
    by_route(R4)
    with pd.option_context("display.width", 200):
        for arm in ("sim_all_cal", "sim_same", "sim_same_cal"):
            q = S[S.arm == arm]
            print(arm); print(q.pivot(index="vid", columns="k_km", values="diff").round(3).to_string())
            print(q.pivot(index="vid", columns="k_km", values="n_better").to_string())


def by_route(R4):
    """Per held-out route: mean over draws of (simulation + level offset) minus real-only LightGBM, and the number of
    draws in which the simulation arm is better. Output: results/v2/paired_vs_real_by_route.csv"""
    C = pd.read_csv(os.path.join(OUT, "variants_calibration.csv"))
    C = C[(C.model == "GBM") & (C.calib == "intercept")]
    real = R4[R4.arm == "real_only"][["fold", "k_km", "draw", "seg_mae"]].rename(columns={"seg_mae": "real_mae"})
    m = C.merge(real, on=["fold", "k_km", "draw"], how="inner", validate="many_to_one")
    m["diff"] = m.seg_mae - m.real_mae
    out = m.groupby(["vid", "k_km", "fold"]).agg(diff=("diff", "mean"), n_better=("diff", lambda x: int((x < 0).sum())),
                                                 n_draws=("diff", "size")).reset_index()
    out.to_csv(os.path.join(OUT, "paired_vs_real_by_route.csv"), index=False)


if __name__ == "__main__":
    main()
