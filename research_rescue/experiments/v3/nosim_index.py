"""Revision v3, item V3-9 (evaluation/PROTOCOL_V3.md): no-simulator comparator (class E).

Does simulation contribute more than a speed exponent and a slope? On the shared draws (k in {1, 2, 5, 10, 20}),
indices calibrated only on the k km of real training-route passes:
  idx05_level    log IRI = c + log(RMS / v^0.5)                       (level offset: median log ratio over the passes)
  idx05_affine   log IRI = c + b log(RMS / v^0.5)                     (OLS on calibration segments)
  idxcar_affine  log IRI = c + b log(RMS / v^alpha_car); alpha_car = label-free within-segment speed exponent of the
                 car's raw RMS on the training routes' repeated passes (no labels used)
and, for reference, the three-parameter index fitted on V0 simulated units + level offset (simidx_level).
Ported from review/v3_checks/c2_minimal_calibration.py. Output: results/v3/nosim_index.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v3 import OUT, EPS, LIRA_ROUTES, load_lira, sample_blocks, seg_table, variant_training_set  # noqa: E402
from common.features import FEATURE_NAMES  # noqa: E402

FI = {n: i for i, n in enumerate(FEATURE_NAMES)}
KS = [1, 2, 5, 10, 20]


def seg_means(U, idx, x, y):
    d = pd.DataFrame(dict(seg=U.segment.to_numpy()[idx], y=y[idx], x=x))
    return d.groupby("seg").agg(y=("y", "first"), x=("x", "mean"))


def alpha_car(U, lrms, lv, tr_idx):
    d = pd.DataFrame(dict(seg=U.segment.to_numpy()[tr_idx], r=lrms[tr_idx], v=lv[tr_idx]))
    d = d[d.groupby("seg").r.transform("size") >= 3]
    dr = d.r - d.groupby("seg").r.transform("mean"); dv = d.v - d.groupby("seg").v.transform("mean")
    return float((dr * dv).sum() / (dv * dv).sum())


def main():
    U, F = load_lira()
    F = F.astype(float)
    y = U.mri.to_numpy()
    lrms, lv = F[:, FI["log_rms"]], F[:, FI["log_v_mean"]]
    rows, info = [], []
    for R in LIRA_ROUTES:
        te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
        a_car = alpha_car(U, lrms, lv, tr)
        ms, Xs, ys = variant_training_set("V0", R)
        Xs = Xs.astype(float)
        A = np.column_stack([np.ones(len(ys)), Xs[:, FI["log_rms"]], Xs[:, FI["log_v_mean"]]])
        coef = np.linalg.lstsq(A, np.log(ys + EPS), rcond=None)[0]
        lp_sim = np.column_stack([np.ones(len(U)), lrms, lv]) @ coef
        info.append(dict(fold=R, alpha_car=a_car, alpha_sim=float(-coef[2] / coef[1])))
        s05, scar = lrms - 0.5 * lv, lrms - a_car * lv
        for k in KS:
            for d in range(20):
                sub = sample_blocks(U, tr, k, np.random.default_rng(1000 * d + 7))
                c05 = np.median(np.log(y[sub] + EPS) - s05[sub])
                S5 = seg_means(U, sub, s05[sub], y); b5, a5 = np.polyfit(S5.x, np.log(S5.y + EPS), 1)
                Sc = seg_means(U, sub, scar[sub], y); bc, ac = np.polyfit(Sc.x, np.log(Sc.y + EPS), 1)
                csim = np.median(np.log(y[sub] + EPS) - lp_sim[sub])
                for arm, lp, slope in (("idx05_level", c05 + s05[te], np.nan), ("idx05_affine", a5 + b5 * s05[te], b5),
                                       ("idxcar_affine", ac + bc * scar[te], bc), ("simidx_level", lp_sim[te] + csim, np.nan)):
                    St = seg_table(U, te, np.clip(np.exp(lp) - EPS, 0, None))
                    rows.append(dict(fold=R, k_km=k, draw=d, arm=arm, seg_mae=float(np.mean(np.abs(St.p - St.y))),
                                     seg_bias=float(np.mean(St.p - St.y)), n_seg=len(St), slope=slope))
        print(info[-1], flush=True)
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, "nosim_index.csv"), index=False)
    pd.DataFrame(info).to_csv(os.path.join(OUT, "nosim_index_alpha.csv"), index=False)
    D["w"] = D.seg_mae * D.n_seg
    a = D.groupby(["arm", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    a["mae"] = a.w / a.n
    print(a.groupby(["arm", "k_km"]).mae.mean().round(3).unstack("k_km").to_string())


if __name__ == "__main__":
    main()
