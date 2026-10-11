"""Shared helpers for the revision-v2 analyses (PROTOCOL_V2.md). Re-uses the v1 data layout and block sampler."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata

RESCUE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RESCUE)
from common import models as M  # noqa: E402,F401
from common.features import FEATURE_NAMES  # noqa: E402
from common.paths import PROCESSED, RESULTS, LIRA_ROUTES  # noqa: E402

OUT = os.path.join(RESULTS, "v2"); os.makedirs(OUT, exist_ok=True)
EPS = 1e-3
CLASS = {"CPH1": "urban", "CPH6": "urban", "M3": "motorway", "M13": "motorway"}
FI = {n: i for i, n in enumerate(FEATURE_NAMES)}

# simulator variant matrix (PROTOCOL_V2.md, Section 3): id -> (dataset name, row filter, description)
VARIANTS = {
    "V0": ("p79_train", None, "primary 50/50 sensor mixture"),
    "V1": ("p79_train", ("sensor", "autopi"), "telematics-like half of V0"),
    "V2": ("p79_train", ("sensor", "phone"), "phone-like half of V0"),
    "V3": ("p79_train_idealsensor", None, "ideal sensor"),
    "V4": ("p79_train_fixedvehicle", None, "one mid-range vehicle"),
    "V5": ("p79_train_measuredsensor", None, "single telematics sensor matched to LiRA-CD statistics"),
    "V6": ("p79_train_measuredmix", None, "matched telematics half + phone-like half"),
    "V7": ("p79_train_telecompliant", ("half", 7), "telematics-like + holder resonance (random half)"),
    "V8": ("p79_train_phonerigid", ("half", 7), "phone-like without holder resonance (random half)"),
    "V7full": ("p79_train_telecompliant", None, "telematics-like + holder resonance (full)"),
    "V8full": ("p79_train_phonerigid", None, "phone-like without holder resonance (full)"),
    "V9": ("iso_train", None, "synthetic ISO-type profiles only"),
    "V10": (("p79_train", "iso_train"), None, "measured + synthetic profiles"),
}


def v1_pass_predictions(U, file, model, average_seeds=True):
    """Pass-level predictions of a v1 model aligned with the rows of U (NaN for units never predicted).
    v1 wrote predictions fold by fold in the order of te = np.where(U.route == fold)[0] (exp_lira.write_preds), one
    block of rows per seed; (segment, task, pass_id) is NOT unique (a ring-road pass can cover a segment twice), so the
    alignment is positional and checked against the labels."""
    from common.paths import RESULTS as _R
    P = pd.read_csv(os.path.join(_R, "predictions", file))
    P = P[P.model == model]
    out = np.full((max(1, P.seed.nunique()), len(U)), np.nan)
    for fold, d in P.groupby("fold", sort=False):
        te = np.where(U.route.to_numpy() == fold)[0]
        for j, (s, ds) in enumerate(d.groupby("seed", sort=True)):
            assert len(ds) == len(te), (file, model, fold, s, len(ds), len(te))
            assert np.allclose(ds.y.to_numpy(), U.mri.to_numpy()[te]), (file, model, fold)
            out[j, te] = ds.pred.to_numpy()
    return np.nanmean(out, 0) if average_seeds else out


def block_id(df, L=1000):
    return df.route.astype(str) + "_" + df.direction.astype(str) + "_" + (df.start_m // L).astype(int).astype(str)


def load_lira():
    U = pd.read_csv(os.path.join(PROCESSED, "lira", "units.csv"))
    U["task"] = U.task.astype(str)
    A = np.load(os.path.join(PROCESSED, "lira", "arrays.npz"))
    assert list(A["feature_names"]) == list(FEATURE_NAMES)
    U["block"] = block_id(U)                       # identical to exp_lira.load_lira
    U["block5"] = block_id(U, 5000)
    U["cls"] = U.route.map(CLASS)
    return U, A["feat"]


_SIM = {}


def load_sim_feat(name):
    if name not in _SIM:
        m = pd.read_csv(os.path.join(PROCESSED, "sim", f"{name}_meta.csv"))
        with np.load(os.path.join(PROCESSED, "sim", f"{name}_arrays.npz")) as A:
            feat = A["feat"]
        if "direction" in m:
            m["block"] = block_id(m)
        _SIM[name] = (m, feat)
    return _SIM[name]


def pass_key(m):
    """Simulated pass identity: (route, direction, vehicle, sensor-draw order). Units of one simulated traversal share
    route, direction and vehicle; v0_kmh identifies the traversal (drawn per pass)."""
    return m.route.astype(str) + "|" + m.direction.astype(str) + "|" + m.vehicle.astype(str) + "|" + m.v0_kmh.round(6).astype(str)


def variant_training_set(vid, test_route=None):
    """(meta, feat, y) of variant `vid` restricted to profiles of routes other than `test_route`."""
    name, filt, _ = VARIANTS[vid]
    names = name if isinstance(name, tuple) else (name,)
    ms, fs = [], []
    for nm in names:
        m, f = load_sim_feat(nm)
        sel = np.ones(len(m), bool)
        if test_route is not None and not nm.startswith("iso"):
            sel &= (m.route != test_route).to_numpy()
        if filt is not None:
            if filt[0] == "half":
                keys = pass_key(m)
                uk = np.unique(keys)
                rng = np.random.default_rng(filt[1])
                keep = set(rng.choice(uk, size=len(uk) // 2, replace=False).tolist())
                sel &= keys.isin(keep).to_numpy()
            else:
                sel &= (m[filt[0]] == filt[1]).to_numpy()
        ms.append(m[sel]); fs.append(f[sel])
    m = pd.concat(ms, ignore_index=True)
    return m, np.concatenate(fs), m.mri.to_numpy()


def sample_blocks(U, tr_idx, k_km, rng):
    """v1 sampler (exp_lira.sample_blocks): contiguous 1 km blocks of one route-direction from the training routes."""
    if k_km == "all":
        return tr_idx
    blocks = U.block.to_numpy()[tr_idx]
    ub = np.unique(blocks)
    chosen = rng.choice(ub, size=min(len(ub), int(k_km)), replace=False)
    return tr_idx[np.isin(blocks, chosen)]


def gbm(features=None):
    return M.GBM(features=features)


def fit_predict_gbm(Xtr, ytr, Xte, features=None):
    g = M.GBM(features=features)
    g.fit(dict(feat=Xtr, y=ytr))
    return g.predict(dict(feat=Xte, y=np.zeros(len(Xte))))


def fit_predict_index(Xtr, ytr, Xte):
    pi = M.PhysicsIndex(None).fit(dict(feat=Xtr, y=ytr))
    return pi.predict(dict(feat=Xte, y=np.zeros(len(Xte))))


def seg_table(U, idx, p):
    """Segment-level table (mean of pass predictions) for units idx with pass predictions p."""
    df = pd.DataFrame(dict(segment=U.segment.to_numpy()[idx], route=U.route.to_numpy()[idx], y=U.mri.to_numpy()[idx],
                           p=np.asarray(p, float), v=U.v_mean.to_numpy()[idx], block=U.block.to_numpy()[idx],
                           block5=U.block5.to_numpy()[idx], cls=U.cls.to_numpy()[idx],
                           lp=np.log(np.asarray(p, float) + EPS)))
    return df.groupby("segment").agg(route=("route", "first"), cls=("cls", "first"), y=("y", "first"), p=("p", "mean"),
                                     lp=("lp", "mean"), v=("v", "mean"), block=("block", "first"),
                                     block5=("block5", "first")).reset_index()


def partial_spearman(x, y, z):
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    Z = np.column_stack([np.ones_like(rz), rz])
    ex = rx - Z @ np.linalg.lstsq(Z, rx, rcond=None)[0]; ey = ry - Z @ np.linalg.lstsq(Z, ry, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1])


def shape_level(S):
    """Shape/level summary of a segment table S (columns route, y, p, v): within-route Spearman and partial Spearman,
    scale b (slope of log p on log y with route fixed effects), level per route (mean log(p/y)), bias, MAE."""
    out = dict(mae=float(np.mean(np.abs(S.p - S.y))), bias=float(np.mean(S.p - S.y)))
    ly_, lp_ = np.log(S.y + EPS), np.log(S.p + EPS)
    D = pd.get_dummies(S.route).to_numpy(float)
    X = np.column_stack([D, ly_])
    b = np.linalg.lstsq(X, lp_, rcond=None)[0]
    out["scale_b"] = float(b[-1])
    for r, d in S.groupby("route"):
        out[f"mae_{r}"] = float(np.mean(np.abs(d.p - d.y)))
        out[f"bias_{r}"] = float(np.mean(d.p - d.y))
        out[f"level_{r}"] = float(np.mean(np.log((d.p + EPS) / (d.y + EPS))))
        out[f"rho_{r}"] = float(spearmanr(d.p, d.y)[0])
        out[f"prho_{r}"] = partial_spearman(d.p, d.y, d.v)
    rs = [r for r in LIRA_ROUTES if f"rho_{r}" in out]
    out["rho_within_mean"] = float(np.mean([out[f"rho_{r}"] for r in rs]))
    out["prho_within_mean"] = float(np.mean([out[f"prho_{r}"] for r in rs]))
    out["mae_within_mean"] = float(np.mean([out[f"mae_{r}"] for r in rs]))
    for c in ("urban", "motorway"):
        d = S[S.cls == c] if "cls" in S else S[S.route.map(CLASS) == c]
        out[f"mae_{c}"] = float(np.mean(np.abs(d.p - d.y))); out[f"bias_{c}"] = float(np.mean(d.p - d.y))
    return out


def calibrate_intercept(y_cal, p_cal):
    return float(np.median(np.log((y_cal + EPS) / (p_cal + EPS))))


def calibrate_affine(seg_cal):
    """seg_cal: segment table of the calibration units (columns y, lp = mean log prediction)."""
    X = np.column_stack([np.ones(len(seg_cal)), seg_cal.lp.to_numpy()])
    a, b = np.linalg.lstsq(X, np.log(seg_cal.y.to_numpy() + EPS), rcond=None)[0]
    return float(a), float(b)


def apply_intercept(p, c):
    return np.clip(np.exp(np.log(p + EPS) + c) - EPS, 0.0, None)


def apply_affine(p, ab):
    return np.clip(np.exp(ab[0] + ab[1] * np.log(p + EPS)) - EPS, 0.0, None)
