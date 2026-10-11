"""Revision v2, step 0: verify the factual claims of the independent review (review/first.md) that can be checked
from EXISTING result files and data, without fitting any new model. Output: results/v2/verify_review_claims.json.

Checked claims (review section in brackets):
  CNN per-seed mean vs 5-seed ensemble MAE, and per-route deficit vs LightGBM            [1, 4]
  BeamNG-trained vibration index vs LightGBM on LiRA-CD (MAE, rho, bias)                  [1, 10]
  holder-resonance effect on bias in the robustness sweep                                 [5]
  comparator of the "about 20 km" statement (few-shot sim-only reference set)             [6]
  map-only road-class prior                                                               [4]
  ARAN9000 matching: share of ARAN points travelling against the P79 track direction      [10]
  telematics units shared across routes                                                   [2]
  segment subsets of the passes-needed analysis                                           [10]
  within-route partial Spearman (given speed) of raw vibration RMS                        [5, 7]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from common import lira, geo  # noqa: E402
from common.paths import PROCESSED, RESULTS, LIRA_ROUTES, LIRA_DIRS  # noqa: E402

OUT = os.path.join(RESULTS, "v2"); os.makedirs(OUT, exist_ok=True)
PRED = os.path.join(RESULTS, "predictions")
GBM = "M3 LightGBM (all features)"


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def partial_spearman(x, y, z):
    rx, ry, rz = rankdata(x), rankdata(y), rankdata(z)
    Z = np.column_stack([np.ones_like(rz), rz])
    ex = rx - Z @ np.linalg.lstsq(Z, rx, rcond=None)[0]; ey = ry - Z @ np.linalg.lstsq(Z, ry, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1])


def main():
    R = {}
    U = pd.read_csv(os.path.join(PROCESSED, "lira", "units.csv"))
    U["task"] = U.task.astype(str)
    seg = U.groupby("segment").agg(route=("route", "first"), y=("mri", "first"), v=("v_mean", "mean")).reset_index()

    # --- CNN / MLP: per-seed mean vs ensemble, per route
    L = pd.read_csv(os.path.join(PRED, "lira_ladder.csv"))
    L = L[L.model.isin([GBM, "M4 MLP", "M5 1D-CNN"])]
    s = L.groupby(["model", "seed", "segment"]).agg(y=("y", "first"), p=("pred", "mean")).reset_index()
    s = s.merge(seg[["segment", "route"]], on="segment")
    out = {}
    for m, d in s.groupby("model"):
        per_seed = d.groupby("seed").apply(lambda q: mae(q.p, q.y))
        ens = d.groupby("segment").agg(y=("y", "first"), p=("p", "mean"), route=("route", "first"))
        out[m] = dict(mean_per_seed_mae=float(per_seed.mean()), ensemble_mae=mae(ens.p, ens.y),
                      per_route_ensemble={r: mae(q.p, q.y) for r, q in ens.groupby("route")})
    for m in ["M4 MLP", "M5 1D-CNN"]:
        out[m]["per_route_minus_gbm"] = {r: out[m]["per_route_ensemble"][r] - out[GBM]["per_route_ensemble"][r]
                                         for r in out[GBM]["per_route_ensemble"]}
    R["neural_seed_vs_ensemble"] = out

    # --- BeamNG-trained models on LiRA-CD
    z = pd.read_csv(os.path.join(RESULTS, "lira", "zeroshot_segment_metrics.csv"))
    R["beamng_transfer"] = z[z.model.str.contains("BeamNG")][["model", "mae", "mae_lo", "mae_hi", "bias", "spearman"]].to_dict("records")

    # --- robustness: holder resonance
    rb = pd.read_csv(os.path.join(RESULTS, "sim", "robustness.csv"))
    R["robustness_mount"] = rb[rb.family == "mount_resonance"][["level", "model", "mae", "bias"]].to_dict("records")
    R["robustness_rate"] = rb[rb.family == "sampling_rate_hz"][["level", "model", "mae", "bias"]].to_dict("records")

    # --- few-shot comparator
    fs = pd.read_csv(os.path.join(RESULTS, "lira", "fewshot_raw.csv"))
    fs = fs.assign(w=fs.seg_mae * fs.n_seg)
    per = fs.groupby(["model", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    per["mae"] = per.w / per.n
    agg = per.groupby(["model", "k_km"]).mae.agg(["mean", "min", "max", "count"]).reset_index()
    R["fewshot_curves"] = agg.to_dict("records")
    R["fewshot_sim_reference_set"] = "p79+iso (exp_lira.part_fewshot: Dsim = sim_training_set(R, 'p79+iso'))"

    # --- map-only road-class prior: each held-out route predicted by the median IRI of the other same-class route
    pair = {"CPH1": "CPH6", "CPH6": "CPH1", "M3": "M13", "M13": "M3"}
    err = {r: (d.y - seg[seg.route == pair[r]].y.median()).abs() for r, d in seg.groupby("route")}
    R["map_prior"] = dict(pooled_mae=float(pd.concat(err.values()).mean()), per_route={r: float(e.mean()) for r, e in err.items()})

    # --- telematics units shared across routes
    U["pk"] = U.route + "|" + U.direction + "|" + U.task + "|" + U.pass_id
    R["tmu_routes"] = {u: sorted(d.route.unique().tolist()) for u, d in U.groupby("unit")}

    # --- passes-needed subsets
    pn = pd.read_csv(os.path.join(RESULTS, "lira", "analysis_passes_needed.csv"))
    R["passes_needed_subsets"] = pn[pn.model == GBM][["road", "n_passes", "n_segments", "mae"]].to_dict("records")

    # --- within-route partial Spearman given speed: raw vibration RMS vs trained models
    raw = U.assign(lr=np.log(U.a_rms)).groupby("segment").agg(route=("route", "first"), y=("mri", "first"),
                                                              p=("lr", "mean"), v=("v_mean", "mean"))
    R["partial_spearman_raw_rms"] = {r: partial_spearman(d.p, d.y, d.v) for r, d in raw.groupby("route")}
    Z = pd.read_csv(os.path.join(PRED, "lira_zeroshot.csv"))
    Z = Z[Z.model.isin(["Z sim[p79] LightGBM", "Z sim[iso] LightGBM"])]
    zz = Z.groupby(["model", "segment"]).agg(y=("y", "first"), p=("pred", "mean")).reset_index().merge(seg[["segment", "route", "v"]], on="segment")
    R["partial_spearman_sim_models"] = {m: {r: partial_spearman(q.p, q.y, q.v) for r, q in d.groupby("route")} for m, d in zz.groupby("model")}
    gg = s[s.model == GBM].groupby("segment").agg(y=("y", "first"), p=("p", "mean")).reset_index().merge(seg[["segment", "route", "v"]], on="segment")
    R["partial_spearman_real_gbm"] = {r: partial_spearman(q.p, q.y, q.v) for r, q in gg.groupby("route")}

    # --- ARAN9000 matching: (a) travel heading of ARAN records (device 'Heading' column, compass degrees) vs the
    # P79 track direction at the matched vertex; (b) is each ARAN record nearer to the P79 track of its own
    # direction or of the opposite direction (opposite-lane contamination); (c) invalid zero-IRI records.
    from common.paths import LIRA_REF
    aran = {}
    for route in LIRA_ROUTES:
        tracks = {}
        for d in LIRA_DIRS:
            zp = lira.load_zp(route, d)
            tracks[d] = zp
        lat0, lon0 = tracks["HH"].lat.median(), tracks["HH"].lon.median()
        pls = {d: geo.Polyline(geo.to_local_xy(z.lat.to_numpy(), z.lon.to_numpy(), lat0, lon0)[::10], z.dist.to_numpy()[::10])
               for d, z in tracks.items()}
        for d in LIRA_DIRS:
            raw = pd.read_csv(os.path.join(LIRA_REF, f"{route.lower()}_aran_{d.lower()}.csv"), sep=";", encoding="latin-1",
                              usecols=["BeginChainage", "Lat", "Lon", "Heading"]).dropna()
            ar = lira.load_aran(route, d)
            axy = geo.to_local_xy(raw.Lat.to_numpy(), raw.Lon.to_numpy(), lat0, lon0)
            h = np.deg2rad(90.0 - raw.Heading.to_numpy())                 # compass -> math angle (x east, y north)
            other = "VH" if d == "HH" else "HH"
            _, d_own = pls[d].match(axy)
            _, d_oth = pls[other].match(axy)
            _, d_own_h = pls[d].match(axy, heading=h)
            near = d_own < 10
            aran[f"{route}_{d}"] = dict(
                n_records=int(len(raw)), within_10m_of_own_track=int(near.sum()),
                share_heading_disagrees=float(np.mean(near & ~(np.isfinite(d_own_h) & (d_own_h < 10)))),
                share_nearer_opposite_track=float(np.mean(d_oth[near] < d_own[near])),
                median_dist_own_m=float(np.median(d_own)), median_dist_opposite_m=float(np.median(d_oth)),
                share_zero_iri=float(np.mean((ar.iri_left <= 0) | (ar.iri_right <= 0))))
    R["aran_alignment_check"] = aran

    json.dump(R, open(os.path.join(OUT, "verify_review_claims.json"), "w"), indent=1, default=float)
    print(json.dumps({k: R[k] for k in ["neural_seed_vs_ensemble", "map_prior", "partial_spearman_raw_rms",
                                        "partial_spearman_real_gbm", "partial_spearman_sim_models", "aran_alignment_check"]},
                     indent=1, default=lambda x: round(float(x), 3)))


if __name__ == "__main__":
    main()
