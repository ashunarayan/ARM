"""Shared helpers for the revision-v3 analyses (evaluation/PROTOCOL_V3.md). Re-uses the v2 helpers unchanged."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
from common_v2 import (RESCUE, M, LIRA_ROUTES, EPS, CLASS, load_lira, variant_training_set, sample_blocks,  # noqa: E402,F401
                       seg_table, fit_predict_gbm, calibrate_intercept, apply_intercept, v1_pass_predictions)
from common.paths import PROCESSED  # noqa: E402

OUT = os.path.join(RESCUE, "results", "v3"); os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(PROCESSED, "v3"); os.makedirs(CACHE, exist_ok=True)
MEAS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]


def zeroshot_all_units(vid, U, F):
    """Zero-shot LightGBM (first configuration) of variant `vid` per held-out route, predicting EVERY unit (so that a
    level offset can be estimated on training-route units). Identical code path to simreal_variants.py; checked against
    the stored held-out predictions (results/v2/variants_pass_predictions.csv.gz). Cached in data/processed/v3/."""
    path = os.path.join(CACHE, f"zeroshot_allunits_{vid}.npz")
    if os.path.exists(path):
        with np.load(path) as z:
            return {R: z[R] for R in LIRA_ROUTES}
    out = {}
    for R in LIRA_ROUTES:
        m, X, ys = variant_training_set(vid, R)
        out[R] = fit_predict_gbm(X, ys, F)
    VP = pd.read_csv(os.path.join(RESCUE, "results", "v2", "variants_pass_predictions.csv.gz"))
    q = VP[(VP.vid == vid) & (VP.model == "GBM")]
    for R in LIRA_ROUTES:
        qq = q[q.fold == R]
        assert np.allclose(out[R][qq.unit.to_numpy()], qq.pred.to_numpy(), rtol=1e-6, atol=1e-6), (vid, R)
    np.savez_compressed(path, **out)
    return out


def subsample_passes(U, sub, m, rng):
    """Keep at most m units (passes) per segment among the calibration units `sub` (label-independent)."""
    if m is None:
        return sub
    seg = U.segment.to_numpy()[sub]
    keep = []
    for s in np.unique(seg):
        idx = sub[seg == s]
        keep.append(idx if len(idx) <= m else rng.choice(idx, m, replace=False))
    return np.sort(np.concatenate(keep))


def pooled_fit_predict(Xs, ys, Xr, yr, Xte):
    """v1 pooled recipe (exp_lira.part_fewshot): equal total weight for simulated and real units, first configuration."""
    w = np.concatenate([np.ones(len(ys)), np.full(len(yr), len(ys) / max(len(yr), 1))])
    g = M.GBM()
    g.fit(dict(feat=np.vstack([Xs, Xr]), y=np.concatenate([ys, yr])), weights=w)
    return g.predict(dict(feat=Xte, y=np.zeros(len(Xte))))


def real_only_predict(F, y, sub, te):
    g = M.GBM()
    g.fit(dict(feat=F[sub], y=y[sub]))
    return g.predict(dict(feat=F[te], y=np.zeros(len(te))))
