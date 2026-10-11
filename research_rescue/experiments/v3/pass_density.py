"""Revision v3, item V3-10 (evaluation/PROTOCOL_V3.md): pass density of the calibration data (class E).

At k = 5 km (shared sampler, draws 0..19), each segment of the k km keeps at most m of its real passes (m in {1, 2, 5};
random, `default_rng(100000 + 1000 * d + m)`, independent of the labels). Arms, paired by draw:
  real_only        LightGBM (first configuration) on the kept passes
  sim_all_cal      zero-shot LightGBM of the variant + level offset from the kept passes (V0-V8)
  sim_real_pooled  LightGBM on the variant's simulated units + the kept passes, balanced weights (V0-V8)
The unrestricted density (all passes, about 9.7 per segment) is in results/v2/value_of_simulation.csv,
variants_calibration.csv and results/v3/pooled_vs_real.csv.
Output: results/v3/pass_density.csv (one row per arm, variant, fold, draw, m)
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v3 import (OUT, MEAS, LIRA_ROUTES, load_lira, variant_training_set, sample_blocks, seg_table,  # noqa: E402
                       calibrate_intercept, apply_intercept, zeroshot_all_units, subsample_passes, real_only_predict,
                       pooled_fit_predict)

K = 5
MS = (1, 2, 5)


def row(arm, vid, R, d, m, St, n_real):
    return dict(arm=arm, vid=vid, fold=R, draw=d, m=m, seg_mae=float(np.mean(np.abs(St.p - St.y))),
                seg_bias=float(np.mean(St.p - St.y)), n_seg=len(St), n_real=int(n_real))


def main():
    t0 = time.time()
    U, F = load_lira()
    y = U.mri.to_numpy()
    rows = []
    subs = {}
    for R in LIRA_ROUTES:
        te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
        for d in range(20):
            sub = sample_blocks(U, tr, K, np.random.default_rng(1000 * d + 7))
            for m in MS:
                sm = subsample_passes(U, sub, m, np.random.default_rng(100000 + 1000 * d + m))
                subs[(R, d, m)] = sm
                rows.append(row("real_only", "-", R, d, m, seg_table(U, te, real_only_predict(F, y, sm, te)), len(sm)))
    print(f"real-only done ({time.time() - t0:.0f}s)", flush=True)
    for vid in MEAS:
        Z = zeroshot_all_units(vid, U, F)
        for R in LIRA_ROUTES:
            te = np.where(U.route == R)[0]
            mm, Xs, ys = variant_training_set(vid, R)
            for d in range(20):
                for m in MS:
                    sm = subs[(R, d, m)]
                    p = apply_intercept(Z[R][te], calibrate_intercept(y[sm], Z[R][sm]))
                    rows.append(row("sim_all_cal", vid, R, d, m, seg_table(U, te, p), len(sm)))
                    p = pooled_fit_predict(Xs, ys, F[sm], y[sm], F[te])
                    rows.append(row("sim_real_pooled", vid, R, d, m, seg_table(U, te, p), len(sm)))
            print(f"{vid} {R} done ({time.time() - t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(os.path.join(OUT, "pass_density.csv"), index=False)       # checkpoint
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, "pass_density.csv"), index=False)
    D["w"] = D.seg_mae * D.n_seg
    a = D.groupby(["arm", "vid", "m", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    a["mae"] = a.w / a.n
    print(a.groupby(["arm", "vid", "m"]).mae.mean().round(3).unstack("m").to_string())


if __name__ == "__main__":
    main()
