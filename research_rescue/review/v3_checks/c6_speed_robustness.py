"""Review v3 check 6 (read-only): robustness of the fixed-road speed elasticities (paper Sec. V-E, Tables S16/S17).

Within-segment slope of log(y) on log(pass mean speed) with segment fixed effects, segments with >= 3 passes, for
  lrms     raw vibration log RMS (the car's physical speed exponent; paper: urban 0.60, motorway 0.85)
  lp_real  real-trained LightGBM (v1 ladder predictions)
  lp_sim   zero-shot LightGBM V0 (results/v2/variants_pass_predictions.csv.gz)
  lp_diff  lp_sim - lp_real on the same passes (paper E8: urban +0.12 [+0.09, +0.15])
Variants of the design: (a) as in the paper; (b) + telematics-unit fixed effects (point estimate); (c) + speed
coefficient of variation as covariate (FWL); (d) + log absolute speed SD within the unit as covariate (FWL).
95 % CIs from a 5 km-block bootstrap (B = 1000). Note: v_cv = sd/mean is mechanically collinear with 1/v, so (c)
over-controls; (d) is the cleaner dynamics control.
Usage: python c6_speed_robustness.py <path to research_rescue>
"""
import sys
import numpy as np
import pandas as pd

RR = sys.argv[1]
EPS = 1e-3
U = pd.read_csv(f"{RR}/data/processed/lira/units.csv")
U["cls"] = U.route.map({"CPH1": "urban", "CPH6": "urban", "M3": "motorway", "M13": "motorway"})
F = np.load(f"{RR}/data/processed/lira/arrays.npz")["feat"]
U["lrms"] = F[:, 2].astype(float)          # feature log_rms
U["cv"] = F[:, 1].astype(float)            # feature v_cv
U["lsd"] = np.log(U.v_std + 0.05)          # log absolute speed SD within the unit (m/s)
U["lv"] = np.log(U.v_mean)
U["b5"] = U.route + "_" + U.direction + "_" + (U.start_m // 5000).astype(int).astype(str)
lad = pd.read_csv(f"{RR}/results/predictions/lira_ladder.csv")
P = lad[lad.model == "M3 LightGBM (all features)"]
p_real = np.full(len(U), np.nan)
for fold, d in P.groupby("fold", sort=False):
    te = np.where(U.route.to_numpy() == fold)[0]
    assert len(d) == len(te) and np.allclose(d.y.to_numpy(), U.mri.to_numpy()[te])
    p_real[te] = d.pred.to_numpy()
VP = pd.read_csv(f"{RR}/results/v2/variants_pass_predictions.csv.gz")
q = VP[(VP.vid == "V0") & (VP.model == "GBM")]
p_sim = np.full(len(U), np.nan); p_sim[q.unit.to_numpy()] = q.pred.to_numpy()
U["lp_real"] = np.log(p_real + EPS); U["lp_sim"] = np.log(p_sim + EPS); U["lp_diff"] = U.lp_sim - U.lp_real


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


def slope_ci(d, ycol, control=None, rng=None, B=1000):
    d = keep3(d)
    cols = [ycol, "lv"] + ([control] if control else [])
    m = demean(d, cols)
    x, y = m["lv"], m[ycol]
    if control:
        z = m[control]
        x = x - z * (z @ x) / (z @ z); y = y - z * (z @ y) / (z @ z)
    blk = pd.factorize(d.b5)[0]
    sxy, sxx = np.bincount(blk, x * y), np.bincount(blk, x * x)
    C = len(sxy)
    bs = [(w @ sxy) / (w @ sxx) for w in (np.bincount(rng.integers(0, C, C), minlength=C) for _ in range(B))]
    return sxy.sum() / sxx.sum(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def slope_unit_fe(d, ycol):
    d = keep3(d)
    m = demean(d, [ycol, "lv"], fes=("segment", "unit"), iters=50)
    return float((m["lv"] * m[ycol]).sum() / (m["lv"] ** 2).sum())


rng = np.random.default_rng(5)
fmt = lambda t: f"{t[0]:+.3f} [{t[1]:+.3f},{t[2]:+.3f}]"
for cls in ("urban", "motorway"):
    d = U[U.cls == cls]
    print(f"--- {cls}: within-segment corr(log v, v_cv) = "
          f"{np.corrcoef(*[demean(keep3(d), ['lv', 'cv'])[k] for k in ('lv', 'cv')])[0, 1]:+.2f}, "
          f"corr(log v, log speed SD) = {np.corrcoef(*[demean(keep3(d), ['lv', 'lsd'])[k] for k in ('lv', 'lsd')])[0, 1]:+.2f}")
    for ycol in ("lrms", "lp_real", "lp_sim", "lp_diff"):
        a = slope_ci(d, ycol, None, rng)
        b = slope_unit_fe(d, ycol)
        c = slope_ci(d, ycol, "cv", rng)
        e = slope_ci(d, ycol, "lsd", rng)
        print(f"{ycol:8s} paper design {fmt(a)} | +unit FE {b:+.3f} | +v_cv {fmt(c)} | +log speed SD {fmt(e)}")
