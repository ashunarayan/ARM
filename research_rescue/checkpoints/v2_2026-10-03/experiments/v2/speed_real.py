"""Revision v2, R5: speed dependence of estimators on REAL cars (PROTOCOL_V2.md, Section 4).

(a) Within-segment speed elasticity: pass-level log(prediction) regressed on log(pass mean speed) with segment fixed
    effects (segments with >= 3 passes). The road (and its IRI) is identical for all passes of a segment, so a
    roughness estimator should have elasticity 0; the v1 +-10 % criterion over 40-100 km/h corresponds to
    |elasticity| <= ln(1.1)/ln(2.5) = 0.104. For raw log RMS the elasticity is the car's physical speed exponent on a
    fixed road. 95 % CI: 1 km-block bootstrap (B = 2000).
(b) Between-segment elasticity (reviewer's design): log(prediction) on route dummies + log(IRI) + log(speed).
(c) Within-route MAE and Spearman by pass-speed tercile (segment-level aggregation within each tercile).

Inputs: held-out (test-route) pass predictions of the v1 models and, if present, of the v2 simulator variants
(results/v2/variants_pass_predictions.csv.gz). Output: results/v2/speed_real.csv, speed_real_terciles.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, EPS, LIRA_ROUTES, load_lira, v1_pass_predictions  # noqa: E402
from common.paths import RESULTS  # noqa: E402

B = 2000
V1_MODELS = {"M3 LightGBM (all features)": "REAL_GBM", "M3 LightGBM (no speed features)": "REAL_GBM_nospeed",
             "M2c RMS/v^alpha (alpha fitted on training data)": "REAL_INDEX", "M2a RMS only (alpha=0)": "REAL_RMS_index",
             "M1 speed-only (LightGBM on speed features)": "REAL_SPEED", "M4 MLP": "REAL_MLP", "M5 1D-CNN": "REAL_CNN"}


def pass_predictions(U):
    """Dict name -> pass-level predictions aligned with U (NaN where the unit is not a test unit)."""
    out = {}
    for m, name in V1_MODELS.items():
        out[name] = v1_pass_predictions(U, "lira_ladder.csv", m)          # seed average for the neural nets
    out["RAW_RMS"] = U.a_rms.to_numpy()                     # physical vibration level (not an IRI estimate)
    vp = os.path.join(OUT, "variants_pass_predictions.csv.gz")
    if os.path.exists(vp):
        V = pd.read_csv(vp)
        for (vid, model), d in V.groupby(["vid", "model"]):
            p = np.full(len(U), np.nan); p[d.unit.to_numpy()] = d.pred.to_numpy()
            out[f"SIM_{vid}_{model}"] = p
    return out


def within_elasticity(lp, lv, seg, blk):
    """Slope of lp on lv with segment fixed effects; block bootstrap via per-block sums of demeaned products."""
    df = pd.DataFrame(dict(lp=lp, lv=lv, seg=seg, blk=blk)).dropna()
    n = df.groupby("seg").lp.transform("size")
    df = df[n >= 3]
    df["x"] = df.lv - df.groupby("seg").lv.transform("mean")
    df["y"] = df.lp - df.groupby("seg").lp.transform("mean")
    g = df.assign(sxy=df.x * df.y, sxx=df.x * df.x).groupby("blk")[["sxy", "sxx"]].sum()
    beta = g.sxy.sum() / g.sxx.sum()
    rng = np.random.default_rng(11)
    C = len(g)
    W = np.stack([np.bincount(rng.integers(0, C, C), minlength=C) for _ in range(B)]).astype(float)
    bs = (W @ g.sxy.to_numpy()) / (W @ g.sxx.to_numpy())
    return float(beta), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), int(df.seg.nunique()), \
        float(df.groupby("seg").lv.std().median())


def main():
    U, _ = load_lira()
    P = pass_predictions(U)
    lv = np.log(U.v_mean.to_numpy())
    rows, terc = [], []
    for name, p in P.items():
        lp = np.log(np.asarray(p, float) + EPS)
        for scope, m in (("pooled", np.ones(len(U), bool)), ("urban", (U.cls == "urban").to_numpy()),
                         ("motorway", (U.cls == "motorway").to_numpy())):
            ok = m & np.isfinite(lp)
            b, lo, hi, nseg, sd_lv = within_elasticity(lp[ok], lv[ok], U.segment.to_numpy()[ok], U.block.to_numpy()[ok])
            # (b) between-segment design with route fixed effects and log(IRI)
            d = pd.DataFrame(dict(lp=lp[ok], lv=lv[ok], ly=np.log(U.mri.to_numpy()[ok] + EPS), route=U.route.to_numpy()[ok]))
            X = np.column_stack([pd.get_dummies(d.route).to_numpy(float), d.ly, d.lv])
            coef = np.linalg.lstsq(X, d.lp, rcond=None)[0]
            rows.append(dict(model=name, scope=scope, within_elasticity=b, within_lo=lo, within_hi=hi,
                             change_40_100_pct=100 * (2.5 ** b - 1), change_lo_pct=100 * (2.5 ** lo - 1),
                             change_hi_pct=100 * (2.5 ** hi - 1), passes_criterion=bool(abs(lo) <= 0.104 and abs(hi) <= 0.104),
                             n_segments=nseg, median_within_seg_sd_logv=sd_lv,
                             between_iri_coef=float(coef[-2]), between_speed_coef=float(coef[-1])))
        # (c) speed terciles within route (pass level -> segment mean within the tercile)
        if name == "RAW_RMS":
            continue
        for r in LIRA_ROUTES:
            m = (U.route == r).to_numpy() & np.isfinite(p)
            q = pd.DataFrame(dict(seg=U.segment.to_numpy()[m], y=U.mri.to_numpy()[m], p=p[m], v=U.v_mean.to_numpy()[m]))
            q["t"] = pd.qcut(q.v, 3, labels=["low", "mid", "high"])
            for t, g in q.groupby("t", observed=True):
                s = g.groupby("seg").agg(y=("y", "first"), p=("p", "mean"))
                terc.append(dict(model=name, route=r, tercile=str(t), v_kmh=float(3.6 * g.v.mean()), n_seg=len(s),
                                 mae=float(np.mean(np.abs(s.p - s.y))), rho=float(spearmanr(s.p, s.y)[0]),
                                 bias=float(np.mean(s.p - s.y))))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "speed_real.csv"), index=False)
    pd.DataFrame(terc).to_csv(os.path.join(OUT, "speed_real_terciles.csv"), index=False)
    show = T[T.model.isin(["RAW_RMS", "REAL_GBM", "REAL_GBM_nospeed", "REAL_INDEX", "REAL_SPEED", "REAL_MLP", "REAL_CNN"])
             | T.model.str.contains("_GBM$|_INDEX$", regex=True)]
    print(show.pivot_table(index="model", columns="scope", values=["within_elasticity", "change_40_100_pct"]).round(3).to_string())


if __name__ == "__main__":
    main()
