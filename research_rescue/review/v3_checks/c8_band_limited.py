"""Review v3 check 8 (read-only, class E): interventional test of the ">10 Hz deficit" explanation of the zero-shot level.

Zero-shot LightGBM (first configuration, as in the paper) is retrained for every measured-profile variant V0-V8 on
three feature sets and evaluated on the held-out real routes (leave-one-route-out):
  full    all 13 features (sanity check: must reproduce results/v2/summary_variants.csv)
  no1015  all features except log_band_10_15
  lt10    only features without content above 10 Hz: log_v_mean, v_cv, log_band_0.5_2, log_band_2_5, log_band_5_10
If the variants' different levels come from simulated energy above 10 Hz, the bias spread across variants should
shrink with `lt10` (a common offset from the shared 2-5 Hz deficit may remain). Also reports MAE after a level offset
from 5 km of real training-route passes (paper sampler, 20 draws).
Usage: python c8_band_limited.py <path to research_rescue> <output csv>
"""
import os
import sys

import numpy as np
import pandas as pd

RR, OUTF = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(RR, "experiments", "v2"))
from common_v2 import (load_lira, variant_training_set, fit_predict_gbm, seg_table, shape_level,  # noqa: E402
                       sample_blocks, calibrate_intercept, apply_intercept, LIRA_ROUTES)
from common.features import FEATURE_NAMES  # noqa: E402

SETS = {"full": list(FEATURE_NAMES),
        "no1015": [f for f in FEATURE_NAMES if f != "log_band_10_15"],
        "lt10": ["log_v_mean", "v_cv", "log_band_0.5_2", "log_band_2_5", "log_band_5_10"]}

U, F = load_lira()
y = U.mri.to_numpy()
rows = []
for vid in ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]:
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
                cal.append(dict(draw=d, w=float(np.sum(np.abs(St.p - St.y))), n=len(St)))
        S = pd.concat(tabs, ignore_index=True)
        sl = shape_level(S)
        C = pd.DataFrame(cal).groupby("draw").sum()
        lvl = {r: sl[f"level_{r}"] for r in LIRA_ROUTES}
        rows.append(dict(vid=vid, features=sname, mae=sl["mae"], bias=sl["bias"], bias_urban=sl["bias_urban"],
                         bias_motorway=sl["bias_motorway"], rho_within=sl["rho_within_mean"],
                         lvl_urban=np.mean([lvl["CPH1"], lvl["CPH6"]]), lvl_motorway=np.mean([lvl["M3"], lvl["M13"]]),
                         mae_level5km=float((C.w / C.n).mean())))
        print(rows[-1], flush=True)
T = pd.DataFrame(rows)
T.to_csv(OUTF, index=False)
pd.set_option("display.width", 200)
for col in ("bias", "mae", "mae_level5km", "lvl_motorway"):
    print(f"\n{col}:\n" + T.pivot(index="vid", columns="features", values=col).round(3).to_string())
print("\nrange over V0-V8 of the pooled zero-shot bias:")
print(T.groupby("features").bias.agg(lambda x: f"{x.min():+.3f} .. {x.max():+.3f} (spread {x.max() - x.min():.3f})"))
