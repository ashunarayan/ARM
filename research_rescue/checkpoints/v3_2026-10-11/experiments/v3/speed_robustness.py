"""Revision v3, item V3-7 (evaluation/PROTOCOL_V3.md): robustness of the fixed-road speed elasticities (class E).

Within-segment slope of log(y) on log(pass mean speed) with segment fixed effects (segments with >= 3 passes), by
road class, for
  raw_rms   raw vibration log RMS (the car's physical speed exponent)
  real_gbm  real-trained LightGBM (v1 ladder predictions)
  sim_v0    zero-shot V0 LightGBM
  diff      sim_v0 - real_gbm on the same passes
Designs: (a) v2 design; (b) + telematics-unit fixed effects (point estimate, alternating projections);
(c) + log within-pass speed SD as covariate; (d) + speed coefficient of variation as covariate (mechanically tied to
1/v, so it over-adjusts; reported for completeness). Intervals: 5 km-block bootstrap (B = 1000, seed 5).
Ported from review/v3_checks/c6_speed_robustness.py. Output: results/v3/speed_robustness.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v3 import OUT, RESCUE, EPS, load_lira, v1_pass_predictions  # noqa: E402
from common.features import FEATURE_NAMES  # noqa: E402


def keep3(d):
    return d[d.groupby("segment").segment.transform("size") >= 3]


def demean(d, cols, fes=("segment",), iters=1):
    out = {c: d[c].to_numpy(float).copy() for c in cols}
    for _ in range(iters):
        for fe in fes:
            g = d[fe].to_numpy()
            for c in cols:
                out[c] = out[c] - pd.Series(out[c]).groupby(g).transform("mean").to_numpy()
    return out


def slope_ci(d, ycol, control, rng, B=1000):
    d = keep3(d)
    m = demean(d, [ycol, "lv"] + ([control] if control else []))
    x, y = m["lv"], m[ycol]
    if control:
        z = m[control]
        x = x - z * (z @ x) / (z @ z); y = y - z * (z @ y) / (z @ z)
    blk = pd.factorize(d.b5)[0]
    sxy, sxx = np.bincount(blk, x * y), np.bincount(blk, x * x)
    C = len(sxy)
    bs = [(w @ sxy) / (w @ sxx) for w in (np.bincount(rng.integers(0, C, C), minlength=C) for _ in range(B))]
    return float(sxy.sum() / sxx.sum()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def slope_unit_fe(d, ycol):
    d = keep3(d)
    m = demean(d, [ycol, "lv"], fes=("segment", "unit"), iters=50)
    return float((m["lv"] * m[ycol]).sum() / (m["lv"] ** 2).sum())


def main():
    U, F = load_lira()
    VP = pd.read_csv(os.path.join(RESCUE, "results", "v2", "variants_pass_predictions.csv.gz"))
    q = VP[(VP.vid == "V0") & (VP.model == "GBM")]
    p_sim = np.full(len(U), np.nan); p_sim[q.unit.to_numpy()] = q.pred.to_numpy()
    p_real = v1_pass_predictions(U, "lira_ladder.csv", "M3 LightGBM (all features)")
    U = U.assign(raw_rms=F[:, FEATURE_NAMES.index("log_rms")].astype(float), cv=F[:, FEATURE_NAMES.index("v_cv")].astype(float),
                 lsd=np.log(U.v_std + 0.05), lv=np.log(U.v_mean), b5=U.block5,
                 real_gbm=np.log(p_real + EPS), sim_v0=np.log(p_sim + EPS))
    U["diff"] = U.sim_v0 - U.real_gbm
    rng = np.random.default_rng(5)
    rows = []
    for cls in ("urban", "motorway"):
        d = U[U.cls == cls]
        dd = demean(keep3(d), ["lv", "cv", "lsd"])
        r_cv = float(np.corrcoef(dd["lv"], dd["cv"])[0, 1]); r_sd = float(np.corrcoef(dd["lv"], dd["lsd"])[0, 1])
        for ycol in ("raw_rms", "real_gbm", "sim_v0", "diff"):
            a = slope_ci(d, ycol, None, rng)            # same call order as review check c6 (same random stream)
            b = slope_unit_fe(d, ycol)
            e = slope_ci(d, ycol, "cv", rng)
            c = slope_ci(d, ycol, "lsd", rng)
            rows.append(dict(cls=cls, quantity=ycol, base=a[0], base_lo=a[1], base_hi=a[2], unit_fe=b,
                             lsd=c[0], lsd_lo=c[1], lsd_hi=c[2], cv=e[0], cv_lo=e[1], cv_hi=e[2],
                             corr_lv_cv=r_cv, corr_lv_lsd=r_sd))
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "speed_robustness.csv"), index=False)


if __name__ == "__main__":
    main()
