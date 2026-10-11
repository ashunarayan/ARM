"""PVS analysis (ordinal / crowdsourced labels only; no IRI claims). Protocol section 4.

Windows and the legacy model's predictions come from ml_model/pvs_comparision/output/pvs_all_predictions.csv
(100 m windows of the rejected paper's PVS study; model = ml_model/iri_compliant tflite + LUT). Physics
features are recomputed here with the shared preprocessing (dashboard accelerometers, left/right average,
gravity-aligned, 0.3 Hz high-pass).

Tasks: (A) asphalt vs. cobblestone+dirt, (B) good vs. regular+bad, (C) within cobblestone+dirt: bad vs. regular.
Predictor sets: {speed}, {RMS}, {RMS/sqrt(v)}, {model}, {model+speed}, {model+RMS}, {model+speed+RMS}.
Leave-one-route-out logistic regression (3 routes = trips {1,4,7}, {2,5,8}, {3,6,9}); AUC with 95 % CI
from a cluster bootstrap over ~100 m GPS cells (repeated passes over the same place resampled together).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import preprocess as PP  # noqa: E402
from common.paths import PVS_RAW, PVS_LEGACY_PRED, RESULTS, TABLES  # noqa: E402

OUT = os.path.join(RESULTS, "pvs"); os.makedirs(OUT, exist_ok=True)


def features():
    P = pd.read_csv(PVS_LEGACY_PRED, keep_default_na=False)
    rows = []
    for t in range(1, 10):
        L = pd.read_csv(os.path.join(PVS_RAW, f"PVS {t}", "dataset_gps_mpu_left.csv"))
        Rr = pd.read_csv(os.path.join(PVS_RAW, f"PVS {t}", "dataset_gps_mpu_right.csv"))
        o = np.argsort(L.timestamp.to_numpy(), kind="stable")
        ts = L.timestamp.to_numpy()[o]
        xyz = np.column_stack([(L[f"acc_{a}_dashboard"].to_numpy() + Rr[f"acc_{a}_dashboard"].to_numpy())[o] / 2 for a in "xyz"])
        t50, a_dyn = PP.vertical_dynamic(ts, xyz / PP.G0)            # m/s^2 -> g for the shared code
        for _, w in P[P.trip_num == t].iterrows():
            t0, t1 = ts[int(w.start_sample_idx)], ts[int(w.end_sample_idx)]
            m = (t50 >= t0) & (t50 <= t1)
            if m.sum() < 25:
                continue
            rows.append(dict(trip=t, route=(t - 1) % 3, start=w.window_start_m, lat=w.latitude, lon=w.longitude,
                             speed=w.avg_speed_ms, surface=w.surface_type, quality=w.road_quality, bump=w.speed_bump,
                             model_cal=w.iri_calibrated, model_raw=w.iri_raw, rms=float(np.sqrt(np.mean(a_dyn[m] ** 2)))))
    D = pd.DataFrame(rows)
    D = D[(D.bump == "None") & (D.surface != "Unknown") & (D.quality != "Unknown")].reset_index(drop=True)
    D["cell"] = (np.round(D.lat * 900).astype(int)).astype(str) + "_" + (np.round(D.lon * 900 * np.cos(np.deg2rad(27.7))).astype(int)).astype(str)
    return D


SETS = {"speed": ["lv"], "RMS": ["lr"], "RMS/sqrt(v)": ["lrv"], "model": ["lm"], "model+speed": ["lm", "lv"],
        "model+RMS": ["lm", "lr"], "model+speed+RMS": ["lm", "lv", "lr"], "speed+RMS": ["lv", "lr"]}


def loro_scores(D, y, cols):
    p = np.full(len(D), np.nan)
    for r in sorted(D.route.unique()):
        tr, te = D.route != r, D.route == r
        if len(np.unique(y[tr])) < 2:
            continue
        X = D[cols].to_numpy(); mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        m = LogisticRegression(max_iter=2000).fit((X[tr] - mu) / sd, y[tr])
        p[te] = m.predict_proba((X[te] - mu) / sd)[:, 1]
    return p


def boot_auc(y, s, cells, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    u, inv = np.unique(cells, return_inverse=True)
    mem = [np.where(inv == k)[0] for k in range(len(u))]
    vals = []
    for _ in range(B):
        idx = np.concatenate([mem[k] for k in rng.integers(0, len(u), len(u))])
        if len(np.unique(y[idx])) == 2:
            vals.append(roc_auc_score(y[idx], s[idx]))
    return float(roc_auc_score(y, s)), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    D = features()
    D["lv"] = np.log(D.speed.clip(lower=0.5)); D["lr"] = np.log(D.rms + 1e-4); D["lrv"] = D.lr - 0.5 * D.lv
    D["lm"] = np.log(D.model_raw.clip(lower=1e-3))
    D.to_csv(os.path.join(OUT, "pvs_windows.csv"), index=False)
    tasks = {
        "A: asphalt vs cobblestone+dirt": (np.ones(len(D), bool), (D.surface != "Asphalt").astype(int).to_numpy()),
        "B: good vs regular+bad": (np.ones(len(D), bool), (D.quality != "Good").astype(int).to_numpy()),
        "C: bad vs regular (cobblestone+dirt only)": ((D.surface != "Asphalt").to_numpy(), (D.quality == "Bad").astype(int).to_numpy()),
    }
    rows = []
    for tname, (mask, yall) in tasks.items():
        Dm = D[mask].reset_index(drop=True); y = yall[mask]
        for sname, cols in SETS.items():
            s = loro_scores(Dm, y, cols)
            ok = np.isfinite(s)
            auc, lo, hi = boot_auc(y[ok], s[ok], Dm.cell.to_numpy()[ok])
            rows.append(dict(task=tname, predictors=sname, n_windows=int(ok.sum()), n_cells=int(Dm.cell[ok].nunique()),
                             n_positive=int(y[ok].sum()), auc=auc, auc_lo=lo, auc_hi=hi))
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(OUT, "pvs_auc.csv"), index=False)
    q = D.quality.map({"Good": 0, "Regular": 1, "Bad": 2})
    sp = {k: float(spearmanr(D[c], q)[0]) for k, c in [("speed (negated)", "lv"), ("RMS", "lr"), ("RMS/sqrt(v)", "lrv"), ("model", "lm")]}
    sp["speed (negated)"] *= -1
    pd.Series(sp).to_csv(os.path.join(OUT, "pvs_spearman_quality.csv"))
    piv = R.pivot(index="predictors", columns="task", values="auc").round(3)
    print(piv.to_string()); print("Spearman with quality (0/1/2):", {k: round(v, 3) for k, v in sp.items()})
    print("mean speed by surface (km/h):", (3.6 * D.groupby("surface").speed.mean()).round(1).to_dict(), "| windows:", len(D), "cells:", D.cell.nunique())


if __name__ == "__main__":
    main()
