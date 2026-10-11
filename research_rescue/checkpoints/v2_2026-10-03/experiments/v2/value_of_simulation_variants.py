"""Revision v2, E5 (PROTOCOL_V2.md, Section 8): the equal-profile-budget arms of R4 for every measured-profile variant.

R4 (value_of_simulation.py) compared, for the same k km of training-route blocks, LightGBM trained on the real passes
over the blocks (real_only) with LightGBM trained on V0 simulated passes over the profiles of the same blocks
(sim_same). V0's zero-shot level happens to be close to the real one, so this script repeats sim_same and
sim_same_cal for V1-V8 (training sets exactly as in E1 / simreal_variants.py, restricted to the same blocks; same
sampler and draws, so real_only of R4 is the paired comparator). V9/V10 are excluded (synthetic profiles are not part
of the k km budget). Added after the V0 results were known: class E, all variants reported.

Output: results/v2/value_of_simulation_variants.csv (one row per variant, fold, k, draw, arm).
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import (OUT, LIRA_ROUTES, load_lira, variant_training_set, sample_blocks, fit_predict_gbm, seg_table,  # noqa: E402
                       calibrate_intercept, apply_intercept)

KS = [1, 2, 5, 10, 20, 40]
DRAWS = 20
VIDS = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]


def main(vids=None):
    vids = vids or VIDS
    tag = "" if vids == VIDS else "_" + "-".join(vids)
    t0 = time.time()
    U, F = load_lira()
    y = U.mri.to_numpy()
    blocks_u = U.block.to_numpy()
    rows = []
    for vid in vids:
        for R in LIRA_ROUTES:
            te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
            m, X, ys = variant_training_set(vid, R)
            assert "block" in m and not (m.route == R).any()
            mb = m.block.to_numpy()
            for k in KS:
                for d in range(DRAWS):
                    rng = np.random.default_rng(1000 * d + 7)          # R4 / v1 sampler: identical blocks to real_only
                    sub = sample_blocks(U, tr, k, rng)
                    chosen = np.unique(blocks_u[sub])
                    ssel = np.isin(mb, chosen)
                    p = fit_predict_gbm(X[ssel], ys[ssel], F)
                    c = calibrate_intercept(y[sub], p[sub])
                    for arm, pp in (("sim_same", p[te]), ("sim_same_cal", apply_intercept(p[te], c))):
                        St = seg_table(U, te, pp)
                        rows.append(dict(vid=vid, fold=R, k_km=k, draw=d, arm=arm,
                                         seg_mae=float(np.mean(np.abs(St.p - St.y))), seg_bias=float(np.mean(St.p - St.y)),
                                         n_seg=len(St), n_real_units=len(sub), n_sim_units=int(ssel.sum()),
                                         km_profiles=len(np.unique(m.segment.to_numpy()[ssel])) / 10.0))
            print(f"{vid} {R:5s} done ({time.time() - t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(os.path.join(OUT, f"value_of_simulation_variants{tag}.csv"), index=False)   # checkpoint
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, f"value_of_simulation_variants{tag}.csv"), index=False)
    D["w"] = D.seg_mae * D.n_seg
    a = D.groupby(["vid", "arm", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    a["mae"] = a.w / a.n
    print(a.groupby(["vid", "arm", "k_km"]).mae.mean().round(3).unstack("k_km").to_string())


def merge():
    """Concatenate the per-variant parts written by parallel runs (python ... V1 V2; python ... V3 V4; ...)."""
    import glob
    parts = sorted(glob.glob(os.path.join(OUT, "value_of_simulation_variants_V*.csv")))
    D = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    assert sorted(D.vid.unique()) == sorted(VIDS), D.vid.unique()
    D.to_csv(os.path.join(OUT, "value_of_simulation_variants.csv"), index=False)
    for p in parts:
        os.remove(p)
    print(len(D), "rows merged from", len(parts), "parts")


if __name__ == "__main__":
    if sys.argv[1:] == ["merge"]:
        merge()
    else:
        main(sys.argv[1:] or None)
