"""BeamNG experiments under the frozen protocol (evaluation/FINAL_EVALUATION_PROTOCOL.md, section 2).

S1  leave-one-map-out (3 folds)                         labels: iri_raw (primary), iri_corr (legacy definition)
S2  leave-one-vehicle-and-map-out (9 folds)              label: iri_raw; reduced ladder (no MLP / no-speed CNN)
S3  legacy split (train east+west, val test-track trip 1, test test-track trips 2-3) - protocol-inflation check
Legacy recipe (6-ch KN input + 13 context features + asymmetric loss + weights + isotonic): S1 and S3, label iri_corr.

Outputs: results/beamng/*.csv|json, results/predictions/beamng_*.csv
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import models as M, report  # noqa: E402
from common.models_legacy import LegacyRecipe  # noqa: E402
from common.stats import metrics  # noqa: E402
from common.paths import PROCESSED, RESULTS  # noqa: E402

OUT = os.path.join(RESULTS, "beamng"); os.makedirs(OUT, exist_ok=True)
PRED = os.path.join(RESULTS, "predictions"); os.makedirs(PRED, exist_ok=True)
MAPS = ["automation_test_track", "east_coast_usa", "west_coast_usa"]
CARS = ["hopper", "sunburst2", "vivace"]


def load():
    meta = pd.read_csv(os.path.join(PROCESSED, "beamng", "meta.csv"))
    A = np.load(os.path.join(PROCESSED, "beamng", "arrays.npz"))
    meta["trip_no"] = meta.trip.str.extract(r"(\d+)").astype(int)
    meta["is_val_trip"] = meta.trip_no == meta.groupby(["car", "map"]).trip_no.transform("max")
    meta["unit_id"] = meta.car + "|" + meta["map"] + "|" + meta.trip + "|" + meta.start_m.astype(int).astype(str)
    D = dict(feat=A["feat"], seq=A["X_zv"][:, :, :1], leg6=A["X_legacy6"], ctx13=A["ctx_legacy"])
    return meta, D


def sub(D, idx, y, groups):
    return dict(feat=D["feat"][idx], seq=D["seq"][idx], y=y[idx], group=groups[idx])


def run_ladder(meta, D, tr, va, te, ylab, ladder, tag):
    y = meta[ylab].to_numpy(); groups = meta.cluster.to_numpy()
    fit_idx = np.concatenate([tr, va])
    Dfit = sub(D, fit_idx, y, groups)
    inner = [(np.arange(len(tr)), np.arange(len(tr), len(fit_idx)))]
    Dte = sub(D, te, y, groups)
    preds = {}
    for m in ladder:
        t0 = time.time()
        if isinstance(m, M.TorchModel):
            m.fit(Dfit, val_idx=np.arange(len(tr), len(fit_idx)))
            preds[m.name] = m.predict_seeds(Dte)
        else:
            m.fit(Dfit, inner=inner)
            preds[m.name] = m.predict(Dte)
        print(f"  [{tag}] {m.name:60s} MAE={np.mean(np.abs(np.atleast_2d(preds[m.name]).mean(0) - y[te])):.3f} ({time.time()-t0:.0f}s)", flush=True)
    return preds


def save_preds(meta, te, y, preds, fname, extra):
    rows = []
    for k, P in preds.items():
        P = np.atleast_2d(P)
        for s in range(P.shape[0]):
            rows.append(pd.DataFrame(dict(unit_id=meta.unit_id.to_numpy()[te], cluster=meta.cluster.to_numpy()[te], y=y,
                                          model=k, seed=s if P.shape[0] > 1 else -1, pred=P[s], **extra)))
    pd.concat(rows).to_csv(fname, index=False, mode="a", header=not os.path.exists(fname))


def experiment_S1(meta, D, ylab):
    tag = f"S1_{ylab}"
    fname = os.path.join(PRED, f"beamng_{tag}.csv")
    if os.path.exists(fname):
        os.remove(fname)
    allp, ally, allc = {}, [], []
    for test_map in MAPS:
        tr = np.where((meta["map"] != test_map) & ~meta.is_val_trip)[0]
        va = np.where((meta["map"] != test_map) & meta.is_val_trip)[0]
        te = np.where((meta["map"] == test_map) & meta.is_eval & meta[ylab].notna())[0]
        preds = run_ladder(meta, D, tr, va, te, ylab, M.standard_ladder(), f"{tag}:{test_map}")
        y = meta[ylab].to_numpy()[te]
        save_preds(meta, te, y, preds, fname, dict(split="S1", fold=test_map, label=ylab))
        for k, P in preds.items():
            allp.setdefault(k, []).append(np.atleast_2d(P))
        ally.append(y); allc.append(meta.cluster.to_numpy()[te])
    y = np.concatenate(ally); c = np.concatenate(allc)
    P = {k: np.concatenate(v, axis=1) for k, v in allp.items()}
    df = report.evaluate(y, P, c, ref="M5 1D-CNN", label=tag)
    df.to_csv(os.path.join(OUT, f"{tag}_metrics.csv"), index=False)
    return df


def experiment_S2(meta, D, ylab="iri_raw"):
    tag = f"S2_{ylab}"
    fname = os.path.join(PRED, f"beamng_{tag}.csv")
    if os.path.exists(fname):
        os.remove(fname)
    rows = []
    allp, ally, allc = {}, [], []
    for test_map in MAPS:
        for test_car in CARS:
            base = (meta["map"] != test_map) & (meta.car != test_car)
            tr = np.where(base & ~meta.is_val_trip)[0]; va = np.where(base & meta.is_val_trip)[0]
            te = np.where((meta["map"] == test_map) & (meta.car == test_car) & meta.is_eval & meta[ylab].notna())[0]
            if len(te) == 0:
                continue
            ladder = [m for m in M.standard_ladder() if not (isinstance(m, M.TorchModel) and (m.kind == "mlp" or not m.use_speed))]
            preds = run_ladder(meta, D, tr, va, te, ylab, ladder, f"{tag}:{test_map}:{test_car}")
            y = meta[ylab].to_numpy()[te]
            save_preds(meta, te, y, preds, fname, dict(split="S2", fold=f"{test_map}|{test_car}", label=ylab))
            for k, P in preds.items():
                allp.setdefault(k, []).append(np.atleast_2d(P))
            ally.append(y); allc.append(meta.cluster.to_numpy()[te])
    y = np.concatenate(ally); c = np.concatenate(allc)
    P = {k: np.concatenate(v, axis=1) for k, v in allp.items()}
    df = report.evaluate(y, P, c, ref="M5 1D-CNN", label=tag)
    df.to_csv(os.path.join(OUT, f"{tag}_metrics.csv"), index=False)
    return df


def experiment_S3_and_legacy(meta, D):
    """Legacy split vs. leave-one-map-out, for the standard ladder and the legacy recipe (label iri_corr)."""
    ylab = "iri_corr"
    y_all = meta[ylab].to_numpy()
    out_rows = []
    tt = "automation_test_track"
    tr = np.where(meta["map"] != tt)[0]
    va = np.where((meta["map"] == tt) & (meta.trip == "trip_1"))[0]
    te = np.where((meta["map"] == tt) & meta.trip.isin(["trip_2", "trip_3"]) & meta.is_eval)[0]
    preds = run_ladder(meta, D, tr, va, te, ylab, M.standard_ladder(), "S3_legacy_split")
    lr = LegacyRecipe().fit(D["leg6"][tr], D["ctx13"][tr], y_all[tr], D["leg6"][va], D["ctx13"][va], y_all[va])
    preds["Legacy recipe (calibrated on val)"] = lr.predict_seeds(D["leg6"][te], D["ctx13"][te])
    raw = lr.predict_seeds(D["leg6"][te], D["ctx13"][te], calibrated=False)
    preds["Legacy recipe (uncalibrated)"] = raw
    y = y_all[te]
    save_preds(meta, te, y, preds, os.path.join(PRED, "beamng_S3_iri_corr.csv"), dict(split="S3", fold=tt, label=ylab))
    df3 = report.evaluate(y, preds, meta.cluster.to_numpy()[te], ref="M5 1D-CNN", label="S3_legacy_split_iri_corr")
    df3.to_csv(os.path.join(OUT, "S3_iri_corr_metrics.csv"), index=False)
    # the legacy reporting rule (discard predictions >= 40 m/km), shown only to quantify its effect
    legacy_rule = []
    for s in range(raw.shape[0]):
        keep = raw[s] < 40.0
        legacy_rule.append(dict(seed=s, n_discarded=int((~keep).sum()), **{f"filtered_{k}": v for k, v in metrics(y[keep], raw[s][keep]).items()},
                                **{f"unfiltered_{k}": v for k, v in metrics(y, raw[s]).items()}))
    pd.DataFrame(legacy_rule).to_csv(os.path.join(OUT, "S3_legacy_discard_rule_effect.csv"), index=False)
    # legacy recipe under leave-one-map-out
    allp, ally, allc = {"Legacy recipe (calibrated on val)": [], "Legacy recipe (uncalibrated)": []}, [], []
    for test_map in MAPS:
        tr = np.where((meta["map"] != test_map) & ~meta.is_val_trip)[0]
        va = np.where((meta["map"] != test_map) & meta.is_val_trip)[0]
        te = np.where((meta["map"] == test_map) & meta.is_eval)[0]
        lr = LegacyRecipe().fit(D["leg6"][tr], D["ctx13"][tr], y_all[tr], D["leg6"][va], D["ctx13"][va], y_all[va])
        allp["Legacy recipe (calibrated on val)"].append(lr.predict_seeds(D["leg6"][te], D["ctx13"][te]))
        allp["Legacy recipe (uncalibrated)"].append(lr.predict_seeds(D["leg6"][te], D["ctx13"][te], calibrated=False))
        ally.append(y_all[te]); allc.append(meta.cluster.to_numpy()[te])
        print(f"  [S1 legacy recipe] {test_map} done", flush=True)
    y = np.concatenate(ally); c = np.concatenate(allc)
    P = {k: np.concatenate(v, axis=1) for k, v in allp.items()}
    df1 = report.evaluate(y, P, c, label="S1_legacy_recipe_iri_corr")
    df1.to_csv(os.path.join(OUT, "S1_legacy_recipe_metrics.csv"), index=False)
    return df3, df1


def main():  # noqa: C901
    meta, D = load()
    print("windows", len(meta), "eval segments", int(meta.is_eval.sum()))
    which = sys.argv[1:] or ["S1_raw", "S1_corr", "S3", "S2"]
    if "S1_raw" in which:
        print(report.fmt(experiment_S1(meta, D, "iri_raw")).to_string(index=False))
    if "S1_corr" in which:
        print(report.fmt(experiment_S1(meta, D, "iri_corr")).to_string(index=False))
    if "S3" in which:
        d3, d1 = experiment_S3_and_legacy(meta, D)
        print(report.fmt(d3).to_string(index=False)); print(report.fmt(d1, cols=("mae", "rmse", "spearman")).to_string(index=False))
    if "S2" in which:
        print(report.fmt(experiment_S2(meta, D)).to_string(index=False))


if __name__ == "__main__":
    main()
