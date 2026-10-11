"""Revision v2, R4: value of simulation at EQUAL profile budget (PROTOCOL_V2.md, Section 4).

For held-out route R, k km of 1 km blocks drawn from the training routes (v1 sampler, draws d = 0..19, identical for
all arms):
  real_only        LightGBM trained on the real passes of the k km (needs profiles AND paired car drives)
  sim_same         LightGBM trained on V0 simulated passes over the SAME k km of P79 profiles (needs profiles only)
  sim_same_cal     sim_same + intercept calibration on the real passes of the same k km (profiles + paired drives)
  sim_all          V0 on all training-route profiles (~120-150 km; constant over k), zero-shot
  sim_all_cal      sim_all + intercept calibration on the real passes of the k km
LightGBM first configuration throughout (no inner validation, as in v1 zero/few-shot).

Output: results/v2/value_of_simulation.csv (one row per fold, k, draw, arm) and a console summary.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import (OUT, LIRA_ROUTES, load_lira, load_sim_feat, sample_blocks, fit_predict_gbm, seg_table,  # noqa: E402
                       calibrate_intercept, apply_intercept)

KS = [1, 2, 5, 10, 20, 40]
DRAWS = 20


def main():
    t0 = time.time()
    U, F = load_lira()
    y = U.mri.to_numpy()
    m0, X0 = load_sim_feat("p79_train")
    y0 = m0.mri.to_numpy()
    rows = []
    for R in LIRA_ROUTES:
        te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
        sel_all = (m0.route != R).to_numpy()
        p_all = fit_predict_gbm(X0[sel_all], y0[sel_all], F)                  # V0, all training-route profiles
        S = seg_table(U, te, p_all[te])
        mae_all = float(np.mean(np.abs(S.p - S.y)))
        for k in KS:
            for d in range(DRAWS):
                rng = np.random.default_rng(1000 * d + 7)
                sub = sample_blocks(U, tr, k, rng)
                chosen = np.unique(U.block.to_numpy()[sub])
                ssel = (m0.block.isin(chosen) & (m0.route != R)).to_numpy()
                km_real = len(np.unique(U.segment.to_numpy()[sub])) / 10.0
                km_prof = len(np.unique(m0.segment.to_numpy()[ssel])) / 10.0
                p_real = fit_predict_gbm(F[sub], y[sub], F[te])
                p_same = fit_predict_gbm(X0[ssel], y0[ssel], F)
                c_same = calibrate_intercept(y[sub], p_same[sub])
                c_all = calibrate_intercept(y[sub], p_all[sub])
                arms = {"real_only": p_real, "sim_same": p_same[te], "sim_same_cal": apply_intercept(p_same[te], c_same),
                        "sim_all": p_all[te], "sim_all_cal": apply_intercept(p_all[te], c_all)}
                for arm, p in arms.items():
                    St = seg_table(U, te, p)
                    rows.append(dict(fold=R, k_km=k, draw=d, arm=arm, seg_mae=float(np.mean(np.abs(St.p - St.y))),
                                     seg_bias=float(np.mean(St.p - St.y)), n_seg=len(St), km_real=km_real,
                                     km_profiles=km_prof, n_real_units=len(sub), n_sim_units=int(ssel.sum())))
            print(f"{R:5s} k={k:3d}  sim_all={mae_all:.3f}  ({time.time() - t0:.0f}s)", flush=True)
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, "value_of_simulation.csv"), index=False)
    D["w"] = D.seg_mae * D.n_seg
    a = D.groupby(["arm", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    a["mae"] = a.w / a.n
    s = a.groupby(["arm", "k_km"]).mae.agg(["mean", lambda x: np.percentile(x, 2.5), lambda x: np.percentile(x, 97.5)])
    s.columns = ["mean", "lo", "hi"]
    print(s.round(3).unstack("arm").to_string())


if __name__ == "__main__":
    main()
