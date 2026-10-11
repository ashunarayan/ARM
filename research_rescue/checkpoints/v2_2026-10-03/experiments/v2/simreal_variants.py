"""Revision v2: R3 shape/level decomposition and calibration, E1 zero-shot variant matrix, E2 sensor factorial
(PROTOCOL_V2.md, Sections 3-5). For every simulator variant V0-V10 (and the BeamNG-trained models) and every outer
fold: zero-shot LightGBM (first configuration) and vibration index trained on simulated units of the training
routes' profiles only; shape/level summary on the held-out route; intercept-only and affine calibration from
k km of REAL TRAINING-ROUTE data (v1 block sampler, 20 draws) applied to the held-out route.

Outputs (results/v2/):
  variants_zeroshot.csv        one row per (variant, model): MAE, bias, within-route rho, scale b, level per route
  variants_calibration.csv     one row per (variant, model, fold, k, draw, calibration kind)
  variants_pass_predictions.csv.gz   pass-level zero-shot predictions on the held-out routes (for R5 / R6)
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import (OUT, VARIANTS, LIRA_ROUTES, EPS, load_lira, variant_training_set, sample_blocks, v1_pass_predictions,  # noqa: E402
                       fit_predict_gbm, fit_predict_index, seg_table, shape_level, calibrate_intercept,
                       calibrate_affine, apply_intercept, apply_affine)
from common.paths import PROCESSED, RESULTS  # noqa: E402

KS = [1, 2, 5, 10, 20]
DRAWS = 20
VIDS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V7full", "V8full", "V9", "V10", "B_corr", "B_raw"]


def beamng_training_set(label):
    bm = pd.read_csv(os.path.join(PROCESSED, "beamng", "meta.csv"))
    with np.load(os.path.join(PROCESSED, "beamng", "arrays.npz")) as A:
        feat = A["feat"]
    ok = bm[label].notna().to_numpy()
    return feat[ok], bm[label].to_numpy()[ok]


def main():
    t0 = time.time()
    U, F = load_lira()
    y = U.mri.to_numpy()
    zs_tabs, cal_rows, pred_parts = {}, [], []
    for vid in VIDS:
        for R in LIRA_ROUTES:
            te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
            if vid.startswith("B_"):
                X, ys = beamng_training_set("iri_corr" if vid == "B_corr" else "iri_raw")
                n_units = len(ys)
            else:
                m, X, ys = variant_training_set(vid, R)
                n_units = len(m)
            P = {"GBM": fit_predict_gbm(X, ys, F), "INDEX": fit_predict_index(X, ys, F)}
            for model, p in P.items():
                S = seg_table(U, te, p[te])
                zs_tabs.setdefault((vid, model), []).append(S)
                pred_parts.append(pd.DataFrame(dict(vid=vid, model=model, fold=R, unit=te, pred=p[te].astype(np.float32))))
                for k in KS:
                    for d in range(DRAWS):
                        rng = np.random.default_rng(1000 * d + 7)          # v1 few-shot sampler and seeds
                        sub = sample_blocks(U, tr, k, rng)
                        c = calibrate_intercept(y[sub], p[sub])
                        ab = calibrate_affine(seg_table(U, sub, p[sub]))
                        for kind, pt in (("intercept", apply_intercept(p[te], c)), ("affine", apply_affine(p[te], ab))):
                            St = seg_table(U, te, pt)
                            cal_rows.append(dict(vid=vid, model=model, fold=R, k_km=k, draw=d, calib=kind,
                                                 seg_mae=float(np.mean(np.abs(St.p - St.y))),
                                                 seg_bias=float(np.mean(St.p - St.y)), n_seg=len(St),
                                                 offset=c if kind == "intercept" else np.nan,
                                                 a=ab[0] if kind == "affine" else np.nan,
                                                 b=ab[1] if kind == "affine" else np.nan,
                                                 n_cal_units=len(sub)))
            print(f"{vid:7s} {R:5s} n_sim_units={n_units:6d} zero-shot GBM MAE="
                  f"{np.mean(np.abs(zs_tabs[(vid, 'GBM')][-1].p - zs_tabs[(vid, 'GBM')][-1].y)):.3f} ({time.time() - t0:.0f}s)",
                  flush=True)

    # real-trained reference (v1 ladder predictions, M3 LightGBM and M2c index), same summaries
    for mname, tag in (("M3 LightGBM (all features)", "GBM"), ("M2c RMS/v^alpha (alpha fitted on training data)", "INDEX")):
        p = v1_pass_predictions(U, "lira_ladder.csv", mname)
        idx = np.where(np.isfinite(p))[0]
        zs_tabs[("REAL", tag)] = [seg_table(U, idx, p[idx])]

    rows = []
    for (vid, model), tabs in zs_tabs.items():
        S = pd.concat(tabs, ignore_index=True)
        desc = VARIANTS[vid][2] if vid in VARIANTS else {"B_corr": "BeamNG corpus, legacy labels",
                                                           "B_raw": "BeamNG corpus, raw-profile labels",
                                                           "REAL": "trained on real data of the other routes (v1)"}[vid]
        rows.append(dict(vid=vid, model=model, desc=desc, n_seg=len(S), **shape_level(S)))
    Z = pd.DataFrame(rows)
    Z.to_csv(os.path.join(OUT, "variants_zeroshot.csv"), index=False)
    C = pd.DataFrame(cal_rows)
    C.to_csv(os.path.join(OUT, "variants_calibration.csv"), index=False)
    pd.concat(pred_parts, ignore_index=True).to_csv(os.path.join(OUT, "variants_pass_predictions.csv.gz"), index=False)

    # console summary: zero-shot and calibrated (pooled, segment-weighted per draw, mean over draws)
    C["w"] = C.seg_mae * C.n_seg
    agg = C.groupby(["vid", "model", "calib", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    agg["mae"] = agg.w / agg.n
    piv = agg.groupby(["vid", "model", "calib", "k_km"]).mae.mean().unstack("k_km")
    print(Z[["vid", "model", "mae", "bias", "mae_urban", "mae_motorway", "scale_b", "rho_within_mean", "prho_within_mean"]]
          .round(3).to_string(index=False))
    print(piv.round(3).to_string())


if __name__ == "__main__":
    main()
