"""Revision v2, E9 (PROTOCOL_V2.md, Section 8): real-only vibration index (M2c) on the same k km draws as R4.

With very little paired data a three-parameter index log IRI = a + b log(RMS / v^alpha) may be a stronger real-only
comparator than LightGBM. Same sampler, folds, k and draws as value_of_simulation.py (R4), so it pairs draw by draw
with every simulation arm. Output: results/v2/value_real_index.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, LIRA_ROUTES, load_lira, sample_blocks, fit_predict_index, seg_table  # noqa: E402

KS = [1, 2, 5, 10, 20, 40]
DRAWS = 20


def main():
    U, F = load_lira()
    y = U.mri.to_numpy()
    rows = []
    for R in LIRA_ROUTES:
        te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
        for k in KS:
            for d in range(DRAWS):
                rng = np.random.default_rng(1000 * d + 7)              # identical blocks to R4 / E5 / R3
                sub = sample_blocks(U, tr, k, rng)
                p = fit_predict_index(F[sub], y[sub], F[te])
                St = seg_table(U, te, p)
                rows.append(dict(fold=R, k_km=k, draw=d, arm="real_only_index", seg_mae=float(np.mean(np.abs(St.p - St.y))),
                                 seg_bias=float(np.mean(St.p - St.y)), n_seg=len(St), n_real_units=len(sub)))
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, "value_real_index.csv"), index=False)
    D["w"] = D.seg_mae * D.n_seg
    a = D.groupby(["k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    a["mae"] = a.w / a.n
    print(a.groupby("k_km").mae.agg(["mean", "median", lambda x: np.percentile(x, 2.5), lambda x: np.percentile(x, 97.5)]).round(3))


if __name__ == "__main__":
    main()
