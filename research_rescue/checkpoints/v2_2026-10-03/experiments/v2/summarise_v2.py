"""Revision v2: tidy summaries feeding figures, tables and paper macros (no new model fitting).

results/v2/summary_real_estimators.csv  every real-data estimator (v1 ladder, map prior, M7, simulation-trained V0/V10):
    pooled and within-route MAE, Spearman, partial Spearman given speed, bias, kappa, 5 km-block paired difference vs
    the real-trained LightGBM and the route-level descriptive interval
results/v2/summary_variants.csv          simulator variants: zero-shot shape/level, within-segment speed elasticity,
    calibrated MAE (intercept / affine) by k with draw ranges
results/v2/summary_value_of_sim.csv      equal-budget arms by k (mean and 2.5-97.5 % range over 20 draws)
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, LIRA_ROUTES, load_lira, seg_table, partial_spearman, v1_pass_predictions  # noqa: E402
from common.stats import quadratic_kappa, bands  # noqa: E402


def within(S):
    r = {}
    for rt, d in S.groupby("route"):
        varies = d.p.std() > 1e-9 * max(1.0, abs(float(d.p.mean())))     # constant predictors: correlation undefined
        r[rt] = dict(mae=float(np.mean(np.abs(d.p - d.y))), rho=float(spearmanr(d.p, d.y)[0]) if varies else np.nan,
                     prho=partial_spearman(d.p, d.y, d.v) if varies else np.nan, bias=float(np.mean(d.p - d.y)))
    return r


def summarise_estimators(U):
    est = {
        "M0 constant": ("lira_ladder.csv", "M0 constant (training median)"),
        "M1 speed only": ("lira_ladder.csv", "M1 speed-only (LightGBM on speed features)"),
        "M2c vibration index": ("lira_ladder.csv", "M2c RMS/v^alpha (alpha fitted on training data)"),
        "M3 LightGBM": ("lira_ladder.csv", "M3 LightGBM (all features)"),
        "M3 LightGBM, no speed": ("lira_ladder.csv", "M3 LightGBM (no speed features)"),
        "M4 MLP": ("lira_ladder.csv", "M4 MLP"),
        "M5 1D-CNN": ("lira_ladder.csv", "M5 1D-CNN"),
        "Sim V0 LightGBM (zero-shot)": ("lira_zeroshot.csv", "Z sim[p79] LightGBM"),
        "Sim V10 LightGBM (zero-shot)": ("lira_zeroshot.csv", "Z sim[p79+iso] LightGBM"),
    }
    tabs = {}
    for name, (f, m) in est.items():
        p = v1_pass_predictions(U, f, m)
        idx = np.where(np.isfinite(p))[0]
        tabs[name] = seg_table(U, idx, p[idx])
    # map prior (median IRI of the other same-class route)
    S = tabs["M3 LightGBM"][["segment", "route", "cls", "y", "v", "block", "block5"]].copy()
    pair = {"CPH1": "CPH6", "CPH6": "CPH1", "M3": "M13", "M13": "M3"}
    med = S.groupby("route").y.median()
    tabs["M0b map-only road-class prior"] = S.assign(p=S.route.map(lambda r: med[pair[r]]))
    # M7 quarter-car inversion
    seg7 = pd.read_csv(os.path.join(OUT, "physics_inversion_segments.csv"))
    for m7, lab in (("M7 quarter-car inversion (uncalibrated)", "M7 quarter-car inversion"),
                    ("M7cal quarter-car inversion + log-linear calibration", "M7 + output calibration")):
        q = seg7[seg7.model == m7][["segment", "p"]]
        tabs[lab] = S.drop(columns=[]).merge(q, on="segment", how="inner")
    inf = pd.read_csv(os.path.join(OUT, "inference_blocks.csv"))
    # neural nets: rows use seed-averaged predictions (5-seed ensembles), so the ensemble comparisons are used; the
    # v1 per-seed-mean convention is added as extra columns
    key = {"M5 1D-CNN": "CNN_ens", "M4 MLP": "MLP_ens", "M1 speed only": "SPEED", "M2c vibration index": "INDEX",
           "M0b map-only road-class prior": "MAP", "Sim V0 LightGBM (zero-shot)": "SIM_P79", "Sim V10 LightGBM (zero-shot)": "SIM_P79ISO"}
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from inference_blocks import boot_diff
    ref = tabs["M3 LightGBM"].set_index("segment")

    def paired_vs_ref(T, level):
        """5 km-block (or 1 km / segment) paired MAE difference vs the real-trained LightGBM on common segments."""
        j = T.set_index("segment")[["p"]].join(ref[["p", "y", "block", "block5"]], rsuffix="_ref", how="inner")
        cl = {"segment": np.arange(len(j)), "block1km": pd.factorize(j.block)[0], "block5km": pd.factorize(j.block5)[0]}[level]
        ea = np.abs(j.p.to_numpy() - j.y.to_numpy())[None, :]; eb = np.abs(j.p_ref.to_numpy() - j.y.to_numpy())[None, :]
        return boot_diff(ea, eb, cl, seed=1)

    rows = []
    for name, T in tabs.items():
        w = within(T)
        e = T.p - T.y
        r = dict(estimator=name, n_seg=len(T), mae=float(np.mean(np.abs(e))), bias=float(np.mean(e)),
                 rho_pooled=float(spearmanr(T.p, T.y)[0]) if T.p.std() > 0 else np.nan,
                 kappa=quadratic_kappa(bands(T.y), bands(T.p)),
                 mae_within=float(np.mean([w[k]["mae"] for k in w])), rho_within=float(np.nanmean([w[k]["rho"] for k in w])),
                 prho_within=float(np.nanmean([w[k]["prho"] for k in w])),
                 **{f"mae_{k}": w[k]["mae"] for k in w}, **{f"rho_{k}": w[k]["rho"] for k in w})
        if name not in key and name != "M3 LightGBM":         # same machinery, computed here on common segments
            d5, lo5, hi5, _, _ = paired_vs_ref(T, "block5km"); _, los, his, _, _ = paired_vs_ref(T, "segment")
            _, lo1, hi1, _, _ = paired_vs_ref(T, "block1km")
            j = T.set_index("segment")[["p", "route"]].join(ref[["p", "y"]], rsuffix="_ref", how="inner")
            dd = np.array([np.mean(np.abs(g.p - g.y)) - np.mean(np.abs(g.p_ref - g.y)) for _, g in j.groupby("route")])
            from scipy import stats as _st
            q3 = _st.t.ppf(0.975, len(dd) - 1) * dd.std(ddof=1) / np.sqrt(len(dd))
            r.update(d5=d5, d5_lo=lo5, d5_hi=hi5, dseg_lo=los, dseg_hi=his, d1_lo=lo1, d1_hi=hi1, n_common=len(T),
                     droute_lo=float(dd.mean() - q3), droute_hi=float(dd.mean() + q3), routes_better=int(np.sum(dd < 0)))
        if name in key:
            q = inf[(inf.model == key[name]) & (inf.reference == "REAL_GBM")].set_index("level")
            r.update(d5=q.loc["block5km", "diff"], d5_lo=q.loc["block5km", "lo"], d5_hi=q.loc["block5km", "hi"],
                     dseg_lo=q.loc["segment", "lo"], dseg_hi=q.loc["segment", "hi"], d1_lo=q.loc["block1km", "lo"],
                     d1_hi=q.loc["block1km", "hi"], droute_lo=q.loc["route_t3", "lo"], droute_hi=q.loc["route_t3", "hi"],
                     routes_better=q.loc["route_t3", "n_routes_a_better"])
            if name in ("M5 1D-CNN", "M4 MLP"):
                qs = inf[(inf.model == key[name].replace("_ens", "")) & (inf.reference == "REAL_GBM")].set_index("level")
                r.update(perseed_d5=qs.loc["block5km", "diff"], perseed_d5_lo=qs.loc["block5km", "lo"],
                         perseed_d5_hi=qs.loc["block5km", "hi"])
        rows.append(r)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "summary_real_estimators.csv"), index=False)
    return pd.DataFrame(rows)


def summarise_variants():
    Z = pd.read_csv(os.path.join(OUT, "variants_zeroshot.csv"))
    C = pd.read_csv(os.path.join(OUT, "variants_calibration.csv"))
    C["w"] = C.seg_mae * C.n_seg
    a = C.groupby(["vid", "model", "calib", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    a["mae"] = a.w / a.n
    g = a.groupby(["vid", "model", "calib", "k_km"]).mae.agg(["mean", lambda x: np.percentile(x, 2.5),
                                                               lambda x: np.percentile(x, 97.5)]).reset_index()
    g.columns = ["vid", "model", "calib", "k_km", "mean", "lo", "hi"]
    SP = pd.read_csv(os.path.join(OUT, "speed_real.csv"))
    rows = []
    for _, z in Z.iterrows():
        r = z.to_dict()
        tag = "REAL_GBM" if (z.vid == "REAL" and z.model == "GBM") else ("REAL_INDEX" if z.vid == "REAL" else f"SIM_{z.vid}_{z.model}")
        for sc in ("pooled", "urban", "motorway"):
            q = SP[(SP.model == tag) & (SP.scope == sc)]
            if len(q):
                r[f"elast_{sc}"] = float(q.within_elasticity.iloc[0]); r[f"elast_{sc}_lo"] = float(q.within_lo.iloc[0])
                r[f"elast_{sc}_hi"] = float(q.within_hi.iloc[0])
        for _, q in g[(g.vid == z.vid) & (g.model == z.model)].iterrows():
            for s in ("mean", "lo", "hi"):
                r[f"{q.calib}_k{q.k_km}_{s}"] = float(q[s])
        rows.append(r)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "summary_variants.csv"), index=False)


def summarise_value():
    D = pd.read_csv(os.path.join(OUT, "value_of_simulation.csv"))
    D["w"] = D.seg_mae * D.n_seg
    a = D.groupby(["arm", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum"), kmp=("km_profiles", "mean")).reset_index()
    a["mae"] = a.w / a.n
    s = a.groupby(["arm", "k_km"]).agg(mean=("mae", "mean"), lo=("mae", lambda x: np.percentile(x, 2.5)),
                                       hi=("mae", lambda x: np.percentile(x, 97.5)), km_profiles=("kmp", "mean")).reset_index()
    p = a.pivot_table(index=["k_km", "draw"], columns="arm", values="mae")
    d = (p.sim_same - p.real_only).groupby("k_km").agg(diff="mean", diff_lo=lambda x: np.percentile(x, 2.5),
                                                      diff_hi=lambda x: np.percentile(x, 97.5),
                                                      share_sim_better=lambda x: float(np.mean(x < 0))).reset_index()
    s = s.merge(d, on="k_km", how="left")
    s.to_csv(os.path.join(OUT, "summary_value_of_sim.csv"), index=False)


def main():
    U, _ = load_lira()
    print(summarise_estimators(U)[["estimator", "mae", "mae_within", "rho_within", "prho_within", "bias", "kappa"]].round(3).to_string(index=False))
    summarise_variants(); summarise_value()


if __name__ == "__main__":
    main()
