"""Revision v3, item V3-2 (evaluation/PROTOCOL_V3.md): test-route uncertainty of the calibration comparison (class E).

For k in {5, 20} km and every measured-profile variant V0-V8, two arms are compared with real-only LightGBM trained
on the same k km (same 20 draws, shared sampler):
  sim_all_cal      zero-shot LightGBM of the variant + level offset from the k km of real passes (R3)
  sim_real_pooled  LightGBM on the variant's simulated units + the k km of real passes, balanced weights (V3-1)
Per draw, segment absolute errors (segment mean of the pass predictions) on the four held-out routes; per segment, the
mean over the 20 draws of (arm - real-only). The pooled estimate is the mean over all 1,678 segments, which equals the
mean over draws of the pooled-MAE difference reported in paired_vs_real.csv. 95 % interval: bootstrap over 5 km blocks
of test segments (B = 2000, seed 3003). The interval conditions on the 20 calibration draws.
Inputs: results/v3/pooled_segpred.npz (V3-1); zero-shot predictions (common_v3.zeroshot_all_units).
Output: results/v3/calib_uncertainty.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v3 import (OUT, MEAS, LIRA_ROUTES, load_lira, sample_blocks, seg_table, calibrate_intercept,  # noqa: E402
                       apply_intercept, zeroshot_all_units, real_only_predict)

B = 2000
KS = (5, 20)


def main():
    U, F = load_lira()
    y = U.mri.to_numpy()
    segs = U.drop_duplicates("segment").set_index("segment")
    PS = np.load(os.path.join(OUT, "pooled_segpred.npz"))
    R4 = pd.read_csv(os.path.join(os.path.dirname(OUT), "v2", "value_of_simulation.csv"))
    rows = []
    for k in KS:
        subs, real_ae, seg_ids, y_seg = {}, {}, {}, {}
        for R in LIRA_ROUTES:
            te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
            A = []
            for d in range(20):
                sub = sample_blocks(U, tr, k, np.random.default_rng(1000 * d + 7))
                subs[(R, d)] = sub
                St = seg_table(U, te, real_only_predict(F, y, sub, te))
                ref = R4[(R4.arm == "real_only") & (R4.fold == R) & (R4.k_km == k) & (R4.draw == d)].seg_mae.iloc[0]
                assert abs(np.mean(np.abs(St.p - St.y)) - ref) < 1e-9, (k, R, d)    # reproduces R4 exactly
                A.append(np.abs(St.p - St.y).to_numpy())
            seg_ids[R] = St.segment.to_numpy().astype(str); y_seg[R] = St.y.to_numpy()
            assert list(seg_ids[R]) == list(PS[f"seg|{R}"])
            real_ae[R] = np.array(A)
        blk = np.concatenate([segs.loc[seg_ids[R], "block5"].to_numpy() for R in LIRA_ROUTES])
        route = np.concatenate([[R] * len(seg_ids[R]) for R in LIRA_ROUTES])
        bid = pd.factorize(blk)[0]; C = bid.max() + 1
        rng = np.random.default_rng(3003)
        W = np.stack([np.bincount(rng.integers(0, C, C), minlength=C) for _ in range(B)]).astype(float)
        cnt = np.bincount(bid, minlength=C)
        for vid in MEAS:
            Z = zeroshot_all_units(vid, U, F)
            for arm in ("sim_all_cal", "sim_real_pooled"):
                dif = []
                for R in LIRA_ROUTES:
                    te = np.where(U.route == R)[0]
                    if arm == "sim_all_cal":
                        Pm = []
                        for d in range(20):
                            sub = subs[(R, d)]
                            St = seg_table(U, te, apply_intercept(Z[R][te], calibrate_intercept(y[sub], Z[R][sub])))
                            Pm.append(St.p.to_numpy())
                        Pm = np.array(Pm)
                    else:
                        Pm = PS[f"{vid}|{R}|{k}"]
                    dif.append((np.abs(Pm - y_seg[R]) - real_ae[R]).mean(0))     # per segment, mean over draws
                dseg = np.concatenate(dif)
                sums = np.bincount(bid, weights=dseg, minlength=C)
                bs = (W @ sums) / (W @ cnt)
                row = dict(vid=vid, arm=arm, k_km=k, diff=float(dseg.mean()), lo=float(np.percentile(bs, 2.5)),
                           hi=float(np.percentile(bs, 97.5)), n_blocks=int(C), n_seg=len(dseg))
                for R in LIRA_ROUTES:
                    row[f"diff_{R}"] = float(dseg[route == R].mean())
                rows.append(row)
                print({kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in row.items()}, flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "calib_uncertainty.csv"), index=False)


if __name__ == "__main__":
    main()
