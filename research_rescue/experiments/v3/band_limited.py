"""Revision v3, item V3-3 (evaluation/PROTOCOL_V3.md): band-limited zero-shot intervention (class E).

Zero-shot LightGBM (first configuration, as for every simulation-trained model) is retrained for each measured-
profile variant V0-V8 on three fixed feature sets and evaluated on the held-out real routes (leave-one-route-out):
  full    all 13 features (must reproduce results/v2/summary_variants.csv)
  no1015  all features except log_band_10_15
  lt10    only features without content above 10 Hz: log_v_mean, v_cv, log_band_0.5_2, log_band_2_5, log_band_5_10
Question: do the level differences between sensor variants act through features that carry simulated energy above
10 Hz? Reports pooled MAE and bias, urban/motorway/mean log level, within-route Spearman, and the pooled and within-
route MAE after a level offset from 5 km of real training-route passes (shared sampler, 20 draws).
Ported from review/v3_checks/c8_band_limited.py; output results/v3/band_limited.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
from common_v2 import (RESCUE, LIRA_ROUTES, load_lira, variant_training_set, fit_predict_gbm, seg_table,  # noqa: E402
                       shape_level, sample_blocks, calibrate_intercept, apply_intercept)
from common.features import FEATURE_NAMES  # noqa: E402

OUT = os.path.join(RESCUE, "results", "v3"); os.makedirs(OUT, exist_ok=True)
SETS = {"full": list(FEATURE_NAMES),
        "no1015": [f for f in FEATURE_NAMES if f != "log_band_10_15"],
        "lt10": ["log_v_mean", "v_cv", "log_band_0.5_2", "log_band_2_5", "log_band_5_10"]}
VIDS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]


def main():
    U, F = load_lira()
    y = U.mri.to_numpy()
    rows = []
    for vid in VIDS:
        for sname, feats in SETS.items():
            tabs, cal = [], []
            for R in LIRA_ROUTES:
                te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
                m, X, ys = variant_training_set(vid, R)
                p = fit_predict_gbm(X, ys, F, features=feats)
                tabs.append(seg_table(U, te, p[te]))
                for d in range(20):
                    sub = sample_blocks(U, tr, 5, np.random.default_rng(1000 * d + 7))
                    St = seg_table(U, te, apply_intercept(p[te], calibrate_intercept(y[sub], p[sub])))
                    cal.append(dict(draw=d, fold=R, ae_sum=float(np.sum(np.abs(St.p - St.y))), n=len(St)))
            S = pd.concat(tabs, ignore_index=True)
            sl = shape_level(S)
            C = pd.DataFrame(cal)
            pooled_cal = (C.groupby("draw").ae_sum.sum() / C.groupby("draw").n.sum()).mean()
            within_cal = (C.ae_sum / C.n).groupby(C.draw).mean().mean()
            lvl = {r: sl[f"level_{r}"] for r in LIRA_ROUTES}
            rows.append(dict(vid=vid, features=sname, n_features=len(feats), mae=sl["mae"], bias=sl["bias"],
                             bias_urban=sl["bias_urban"], bias_motorway=sl["bias_motorway"],
                             rho_within=sl["rho_within_mean"], mae_within=sl["mae_within_mean"],
                             lvl_urban=float(np.mean([lvl["CPH1"], lvl["CPH6"]])),
                             lvl_motorway=float(np.mean([lvl["M3"], lvl["M13"]])),
                             lvl_mean=float(np.mean(list(lvl.values()))),
                             mae_level5km=float(pooled_cal), mae_within_level5km=float(within_cal)))
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "band_limited.csv"), index=False)
    sens = [v for v in VIDS if v != "V4"]
    for col in ("bias", "lvl_mean", "lvl_urban", "lvl_motorway"):
        q = T[T.vid.isin(sens)].groupby("features")[col].agg(lambda x: x.max() - x.min())
        print(f"spread over the eight sensor variants of {col}:", q.round(3).to_dict(),
              "| V4:", T[T.vid == "V4"].set_index("features")[col].round(3).to_dict())


if __name__ == "__main__":
    main()
