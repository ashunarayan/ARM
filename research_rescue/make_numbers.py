"""Write every number quoted in the paper as a LaTeX macro (paper/numbers.tex) from result files, so that no
experimental number is typed by hand. Missing inputs produce '??' (visible in the PDF) instead of stale values."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.paths import RESULTS, PROCESSED, RESCUE  # noqa: E402

M = {}
RN = {"CPH1": "CphOne", "CPH6": "CphSix", "M3": "MwThree", "M13": "MwThirteen"}


def put(name, value, fmt="{:.2f}"):
    try:
        M[name] = fmt.format(value) if not isinstance(value, str) else value
    except Exception:
        M[name] = "??"


def csv(p):
    p = os.path.join(RESULTS, p)
    return pd.read_csv(p) if os.path.exists(p) else None


def row(df, model):
    if df is None:
        return None
    r = df[df.model == model]
    return r.iloc[0] if len(r) else None


def ci_macro(prefix, r, stat="mae", nd=2):
    f = "{:.%df}" % nd
    if r is None:
        for s in ("", "Lo", "Hi"):
            M[prefix + s] = "??"
        return
    put(prefix, r[stat], f); put(prefix + "Lo", r[stat + "_lo"], f); put(prefix + "Hi", r[stat + "_hi"], f)


def sci(x, nd=1):
    """LaTeX scientific notation usable in text and math mode, e.g. \\ensuremath{3.9\\cdot10^{-13}}."""
    m, e = f"{x:.{nd}e}".split("e")
    return f"\\ensuremath{{{m}\\cdot10^{{{int(e)}}}}}"


def main():
    # ---------------- simulator unit tests, LiRA-CD sensor statistics, CPH6-HH alignment search
    j = lambda p: json.load(open(os.path.join(RESULTS, p))) if os.path.exists(os.path.join(RESULTS, p)) else None
    S = j("sim_unit_test.json")
    if S:
        put("simModalDev", sci(S["modal_vs_direct_max_rel_dev"])); put("simRkDev", sci(S.get("modal_vs_rk4_max_rel_dev", np.nan)))
        put("simBodyHzLo", S["body_modes_hz_range"][0], "{:.2f}"); put("simBodyHzHi", S["body_modes_hz_range"][1], "{:.2f}")
        put("simHopHzLo", S["wheel_hop_hz_range"][0], "{:.1f}"); put("simHopHzHi", S["wheel_hop_hz_range"][1], "{:.1f}")
        put("simPreRatio", S["preprocess_rms_ratio_ideal_sensor"], "{:.3f}")
    Q = j("lira_sensor_stats.json")
    if Q:
        put("liraRateLow", Q["nominal_hz_low_cluster"], "{:.1f}"); put("liraRateHigh", Q["nominal_hz_high_cluster"], "{:.0f}")
        put("liraRateLowShare", 100 * Q["share_passes_low_cluster"], "{:.0f}")
        put("liraRateMeanMin", Q["mean_hz_min"], "{:.0f}"); put("liraRateMeanMax", Q["mean_hz_max"], "{:.0f}")
        put("liraLsbShare", 100 * Q["share_passes_lsb_0p01g"], "{:.0f}"); put("liraLsbMin", Q["lsb_g_min"], "{:.4f}")
        put("liraTiltMedian", Q["tilt_deg_median"], "{:.0f}"); put("liraTiltPninetyfive", Q["tilt_deg_p95"], "{:.0f}")
        put("liraTiltMax", Q["tilt_deg_max"], "{:.0f}"); put("liraSensorPasses", Q["n_passes"], "{:.0f}")
        if "signal_availability" in Q:
            put("liraGpsOnly", Q["signal_availability"]["gps_only"], "{:.0f}"); put("liraNoSpeed", Q["signal_availability"]["no_speed"], "{:.0f}")
            put("liraAllSignals", Q["signal_availability"]["all_signals"], "{:.0f}")
        if "gps_hz_min" in Q:
            put("liraGpsHzMin", Q["gps_hz_min"], "{:.1f}"); put("liraGpsHzMax", Q["gps_hz_max"], "{:.1f}")
            put("liraGpsHzMedian", Q["gps_hz_median"], "{:.1f}"); put("liraCanHz", Q["speed_hz_median"], "{:.0f}")
    Ro = j("route_overlap.json")
    if Ro:
        put("overlapWithin", Ro["total_within_15m"], "{:.0f}")
    Al = j("iri_alignment_search.json")
    if Al:
        h = Al["CPH6_HH"]
        put("alignBestR", max(max(h[s]["best_r_forward"], h[s]["best_r_reversed"]) for s in ("left", "right")))
        put("alignControlR", min(Al[k][s]["r_at_zero_shift"] for k in Al if k != "CPH6_HH" for s in ("left", "right")), "{:.3f}")
    # ---------------- IRI validation
    v = json.load(open(os.path.join(RESULTS, "iri_validation.json"))) if os.path.exists(os.path.join(RESULTS, "iri_validation.json")) else None
    if v:
        P = pd.DataFrame(v["pooled"])
        g = lambda comp, scope: P[(P.comparison == comp) & (P.scope == scope)].iloc[0]
        c = g("This implementation (0.1 m) vs P79-reported", "consistent files")
        put("iriValN", c.n, "{:,.0f}"); put("iriValR", c.pearson, "{:.3f}"); put("iriValBias", c.bias, "{:+.3f}")
        put("iriValMae", c.mae, "{:.3f}"); put("iriValMape", c.mape, "{:.1f}"); put("iriValFiles", c.files, "{:.0f}")
        put("iriValLoaLo", c.loa_low, "{:+.3f}"); put("iriValLoaHi", c.loa_high, "{:+.3f}")
        a = g("This implementation (0.1 m) vs P79-reported", "all files"); put("iriValAllR", a.pearson, "{:.3f}")
        l = g("Legacy compute_iri (no correction) vs P79-reported", "consistent files"); put("legacyCoreBias", l.bias, "{:+.3f}"); put("legacyCoreMape", l.mape, "{:.1f}")
        st_ = v.get("self_test", {})
        if st_:
            put("iriSolverDev", sci(st_["fast_vs_loop_max_abs_diff"])); put("iriSineDev", sci(st_["sine_rel_err"]))
            put("iriRampIri", sci(abs(st_["ramp_iri"])))
        for scope, nm in [("consistent files", "All"), ("urban", "Urban"), ("motorway", "Motorway")]:
            r = g("Legacy pipeline incl. mesh correction vs P79-reported", scope)
            put(f"legacyCorr{nm}Bias", r.bias, "{:+.2f}"); put(f"legacyCorr{nm}Mape", r.mape, "{:.0f}"); put(f"legacyCorr{nm}R", r.pearson, "{:.2f}")
        for scope, nm in [("urban", "Urban"), ("motorway", "Motorway"), ("all files", "All")]:
            r = g("ARAN9000 vs P79 (profile)", scope)
            put(f"aran{nm}R", r.pearson, "{:.2f}"); put(f"aran{nm}Bias", r.bias, "{:+.2f}"); put(f"aran{nm}Mae", r.mae, "{:.2f}")
    # ---------------- datasets
    U = pd.read_csv(os.path.join(PROCESSED, "lira", "units.csv")) if os.path.exists(os.path.join(PROCESSED, "lira", "units.csv")) else None
    if U is not None:
        put("liraUnits", len(U), "{:,.0f}"); put("liraSegments", U.segment.nunique(), "{:,.0f}"); put("liraKm", U.segment.nunique() / 10, "{:.0f}")
        put("liraPasses", U.groupby(["route", "direction", "task", "pass_id"]).ngroups, "{:.0f}")
        put("liraDevices", U.loc[U.unit != "?", "unit"].nunique(), "{:.0f}")
        urb = U.route.str.startswith("CPH")
        put("liraSpeedUrban", 3.6 * U.loc[urb, "v_mean"].mean(), "{:.0f}"); put("liraSpeedMotorway", 3.6 * U.loc[~urb, "v_mean"].mean(), "{:.0f}")
        seg = U.groupby("segment").agg(y=("mri", "first"), r=("route", "first"))
        put("liraIriUrban", seg[seg.r.str.startswith("CPH")].y.mean()); put("liraIriMotorway", seg[seg.r.str.startswith("M")].y.mean())
        st = json.load(open(os.path.join(PROCESSED, "lira", "build_status.json")))
        put("liraSkipped", sum(x["passes_without_acc_or_speed"] for x in st.values()), "{:.0f}")
        put("liraNoUnits", sum(x["passes_without_valid_units"] for x in st.values()), "{:.0f}")
        for r_, g_ in U.groupby("route"):
            s_ = g_.groupby("segment").agg(y=("mri", "first"), v=("v_mean", "mean"))
            put(f"speedIriRho{RN[r_]}", s_[["v", "y"]].corr("spearman").iloc[0, 1])
    bm = os.path.join(PROCESSED, "beamng", "meta.csv")
    if os.path.exists(bm):
        B = pd.read_csv(bm); put("bngKm", B.is_eval.sum() / 10, "{:.0f}"); put("bngSegments", int(B.is_eval.sum()), "{:,.0f}")
        put("bngTrips", B[["car", "map", "trip"]].drop_duplicates().shape[0], "{:.0f}")
        put("bngCars", B.car.nunique(), "{:.0f}"); put("bngMaps", B["map"].nunique(), "{:.0f}")
        E = B[B.is_eval & B.iri_raw.notna() & B.iri_corr.notna()]
        put("bngIriRawMedian", E.iri_raw.median()); put("bngIriCorrMedian", E.iri_corr.median())
        put("bngIriRawMean", E.iri_raw.mean()); put("bngIriCorrMean", E.iri_corr.mean())
        cls = lambda x: np.digitize(x, [1.50, 2.68])
        put("bngClassChange", 100 * np.mean(cls(E.iri_raw) != cls(E.iri_corr)), "{:.0f}")
        put("bngCorrReduction", 100 * (1 - E.iri_corr.sum() / E.iri_raw.sum()), "{:.0f}")
        ar = os.path.join(RESCUE, "audit", "outputs", "audit_raw.csv")
        if os.path.exists(ar):
            A_ = pd.read_csv(ar)
            put("bngImuDupMin", A_.imu_dup_pct.min(), "{:.0f}"); put("bngImuDupMax", A_.imu_dup_pct.max(), "{:.0f}")
    lf = os.path.join(RESULTS, "legacy_fidelity_check.json")
    if os.path.exists(lf):
        L = json.load(open(lf))["reimplementation_mean"]
        put("legacyFidMae", L["cal"]["mae"]); put("legacyFidRtwo", L["cal"]["r2"])
    # ---------------- BeamNG protocol (RQ2)
    s3 = csv("beamng/S3_iri_corr_metrics.csv"); s1l = csv("beamng/S1_legacy_recipe_metrics.csv"); s1c = csv("beamng/S1_iri_corr_metrics.csv")
    ci_macro("bngSthreeLegacyMae", row(s3, "Legacy recipe (calibrated on val)"))
    ci_macro("bngSthreeLegacyRho", row(s3, "Legacy recipe (calibrated on val)"), "spearman")
    ci_macro("bngSoneLegacyMae", row(s1l, "Legacy recipe (calibrated on val)"))
    ci_macro("bngSoneLegacyRho", row(s1l, "Legacy recipe (calibrated on val)"), "spearman")
    ci_macro("bngSoneLegacyRtwo", row(s1l, "Legacy recipe (calibrated on val)"), "r2")
    ci_macro("bngSthreeLegacyRtwo", row(s3, "Legacy recipe (calibrated on val)"), "r2")
    r = row(s1l, "Legacy recipe (uncalibrated)"); put("bngSoneLegacyUncalMae", r["mae"] if r is not None else "??", "{:.0f}")
    for mdl, nm in [("M4 MLP", "Mlp"), ("M3 LightGBM (all features)", "Gbm"), ("M2c RMS/v^alpha (alpha fitted on training data)", "Phys"),
                    ("M1 speed-only (LightGBM on speed features)", "Speed"), ("M0 constant (training median)", "Const"), ("M5 1D-CNN", "Cnn")]:
        ci_macro(f"bngSoneCorr{nm}Mae", row(s1c, mdl)); ci_macro(f"bngSoneCorr{nm}Rho", row(s1c, mdl), "spearman")
    dr = csv("beamng/S3_legacy_discard_rule_effect.csv")
    if dr is not None:
        put("discardMaxUnfiltered", dr.unfiltered_mae.max(), "{:,.0f}"); put("discardMaxFiltered", dr.filtered_mae.max())
        put("discardMinN", dr.n_discarded.min(), "{:.0f}"); put("discardMaxN", dr.n_discarded.max(), "{:.0f}")
    s2 = csv("beamng/S2_iri_raw_metrics.csv")
    ci_macro("bngStwoConstMae", row(s2, "M0 constant (training median)")); ci_macro("bngStwoGbmMae", row(s2, "M3 LightGBM (all features)"))
    ci_macro("bngStwoCnnMae", row(s2, "M5 1D-CNN")); ci_macro("bngStwoPhysMae", row(s2, "M2c RMS/v^alpha (alpha fitted on training data)"))
    bv = csv("beamng/seen_vs_unseen_vehicle.csv")
    if bv is not None:
        for mdl, nm in [("M3 LightGBM (all features)", "Gbm"), ("M5 1D-CNN", "Cnn"), ("M2c RMS/v^alpha (alpha fitted on training data)", "Phys"),
                        ("M3 LightGBM (no speed features)", "GbmNoSpeed"), ("M2d RMS*(v_ref/v)^2 (legacy exponent, gravity removed)", "PhysD"),
                        ("M2a RMS only (alpha=0)", "PhysA"), ("M1 speed-only (LightGBM on speed features)", "Speed"),
                        ("M0 constant (training median)", "Const")]:
            q = bv[bv.model == mdl]
            if len(q):
                q = q.iloc[0]
                put(f"bngVeh{nm}Rel", 100 * q.rel, "{:+.0f}"); put(f"bngVeh{nm}RelHi", 100 * q.rel_hi, "{:+.0f}")
                put(f"bngVeh{nm}Seen", q.mae_vehicle_seen); put(f"bngVeh{nm}Unseen", q.mae_vehicle_unseen)
                put(f"bngVeh{nm}Pass", "yes" if bool(q.generalises) else "no", "{}")
    # ---------------- LiRA ladder (RQ4)
    lad = csv("lira/ladder_segment_metrics.csv")
    names = {"M0 constant (training median)": "Const", "M1 speed-only (LightGBM on speed features)": "Speed",
             "M2a RMS only (alpha=0)": "PhysA", "M2b RMS/v^0.5": "PhysB", "M2c RMS/v^alpha (alpha fitted on training data)": "PhysC",
             "M2d RMS*(v_ref/v)^2 (legacy exponent, gravity removed)": "PhysD", "M3 LightGBM (all features)": "Gbm",
             "M3 LightGBM (no speed features)": "GbmNoSpeed", "M4 MLP": "Mlp", "M5 1D-CNN": "Cnn", "M5 1D-CNN (no speed input)": "CnnNoSpeed",
             "M6 inner-validation-selected model": "Sel"}
    for mdl, nm in names.items():
        r = row(lad, mdl)
        ci_macro(f"lira{nm}Mae", r); ci_macro(f"lira{nm}Rho", r, "spearman"); ci_macro(f"lira{nm}Kappa", r, "kappa")
        if r is not None and "mae_seed_sd" in r and np.isfinite(r.mae_seed_sd):
            put(f"lira{nm}SeedSd", r.mae_seed_sd, "{:.3f}")
        if r is not None and "dmae_vs_ref" in r and mdl != "M3 LightGBM (all features)":
            put(f"lira{nm}Dmae", r.dmae_vs_ref, "{:+.2f}"); put(f"lira{nm}DmaeLo", r.dmae_lo, "{:+.2f}"); put(f"lira{nm}DmaeHi", r.dmae_hi, "{:+.2f}")
            put(f"lira{nm}P", "<0.001" if r.p_holm < 0.0005 else f"{r.p_holm:.3f}")
    pr = csv("lira/ladder_per_route.csv")
    if pr is not None:
        for mdl, nm in names.items():
            for rt in ["CPH1", "CPH6", "M3", "M13"]:
                q = pr[(pr.model == mdl) & (pr.route == rt)]
                if len(q):
                    put(f"lira{nm}Mae{RN[rt]}", q.mae.iloc[0])
    sel = csv("lira/ladder_model_selection.csv")
    if sel is not None:
        put("liraSelected", ", ".join(f"{a}:{b}" for a, b in zip(sel.test_route, sel.selected)), "{}")
    wr = csv("lira/analysis_within_route_ranking.csv")
    if wr is not None:
        for mdl, nm in names.items():
            q = wr[wr.model == mdl]
            if len(q):
                put(f"lira{nm}PartialUrban", q[q.route.str.startswith("CPH")].partial_spearman_given_speed.mean())
                put(f"lira{nm}PartialMotorway", q[q.route.str.startswith("M")].partial_spearman_given_speed.mean())
    pn = csv("lira/analysis_passes_needed.csv")
    if pn is not None:
        for mdl, nm in [("M3 LightGBM (all features)", "Gbm"), ("M2c RMS/v^alpha (alpha fitted on training data)", "Phys"), ("M5 1D-CNN", "Cnn")]:
            for road, rn in [("urban", "Urban"), ("motorway", "Motorway")]:
                for k, kn_ in [(1, "One"), (5, "Five")]:
                    q = pn[(pn.model == mdl) & (pn.road == road) & (pn.n_passes == k)]
                    if len(q):
                        put(f"pass{nm}{rn}{kn_}", q.mae.iloc[0])
    # ---------------- zero-shot / comparisons (RQ5)
    zs = csv("lira/zeroshot_segment_metrics.csv")
    zn = {"Z sim[iso] physics index (alpha fitted in sim)": "IsoPhys", "Z sim[iso] LightGBM": "IsoGbm", "Z sim[iso] 1D-CNN": "IsoCnn",
          "Z sim[p79] physics index (alpha fitted in sim)": "PsevenPhys", "Z sim[p79] LightGBM": "PsevenGbm",
          "Z sim[p79+iso] physics index (alpha fitted in sim)": "BothPhys", "Z sim[p79+iso] LightGBM": "BothGbm", "Z sim[p79+iso] 1D-CNN": "BothCnn",
          "Z sim[p79-fixedvehicle] LightGBM": "FixVehGbm", "Z sim[p79-idealsensor] LightGBM": "IdealGbm",
          "Z sim[p79-fixedvehicle] physics index (alpha fitted in sim)": "FixVehPhys", "Z sim[p79-idealsensor] physics index (alpha fitted in sim)": "IdealPhys",
          "Z BeamNG[iri_corr] LightGBM": "BngCorrGbm", "Z BeamNG[iri_raw] LightGBM": "BngRawGbm",
          "Z BeamNG[iri_corr] physics index": "BngCorrPhys", "Z BeamNG[iri_raw] physics index": "BngRawPhys"}
    for mdl, nm in zn.items():
        r = row(zs, mdl); ci_macro(f"zs{nm}Mae", r); ci_macro(f"zs{nm}Rho", r, "spearman")
    cmp_ = csv("lira/compare_zeroshot_vs_real.csv")
    if cmp_ is not None:
        for mdl, nm in zn.items():
            q = cmp_[(cmp_.model == mdl) & (cmp_.reference == "M3 LightGBM (all features)")]
            if len(q):
                q = q.iloc[0]
                put(f"zs{nm}Dmae", q.dmae_diff, "{:+.2f}"); put(f"zs{nm}DmaeLo", q.dmae_lo, "{:+.2f}"); put(f"zs{nm}DmaeHi", q.dmae_hi, "{:+.2f}")
                put(f"zs{nm}P", "<0.001" if q.p_holm < 0.0005 else f"{q.p_holm:.3f}")
                put(f"zs{nm}MaeUrban", q.mae_model_urban); put(f"zs{nm}MaeMotorway", q.mae_model_motorway)
        q = cmp_[cmp_.reference == "M3 LightGBM (all features)"]
        if len(q):
            put("liraGbmMaeUrban", q.mae_ref_urban.iloc[0]); put("liraGbmMaeMotorway", q.mae_ref_motorway.iloc[0])
    ph = csv("lira/zeroshot_sensor_segment_metrics.csv")      # post-hoc sensor sensitivity analysis
    if ph is not None:
        for mdl, nm in [("Z sim[p79] LightGBM", "PrimGbm"), ("Z sim[p79-measuredsensor] LightGBM", "MeasGbm"),
                        ("Z sim[p79] physics index (alpha fitted in sim)", "PrimPhys"),
                        ("Z sim[p79-measuredsensor] physics index (alpha fitted in sim)", "MeasPhys"),
                        ("Z sim[p79-measuredmix] LightGBM", "MixGbm"), ("Z sim[p79-measuredmix] physics index (alpha fitted in sim)", "MixPhys")]:
            r = row(ph, mdl)
            ci_macro(f"ph{nm}Mae", r)
            if r is not None and mdl != r.reference:
                put(f"ph{nm}Dmae", r.dmae_vs_ref, "{:+.2f}"); put(f"ph{nm}DmaeLo", r.dmae_lo, "{:+.2f}"); put(f"ph{nm}DmaeHi", r.dmae_hi, "{:+.2f}")
                put(f"ph{nm}P", "<0.001" if r.p_holm < 0.0005 else f"{r.p_holm:.3f}")
        pr2 = csv("lira/zeroshot_sensor_per_route.csv")
        if pr2 is not None:
            pr2 = pr2.assign(w=pr2.mae * pr2.n_segments, cls=np.where(pr2.route.str.startswith("CPH"), "Urban", "Motorway"))
            for mdl, nm in [("Z sim[p79] LightGBM", "PrimGbm"), ("Z sim[p79-measuredsensor] LightGBM", "MeasGbm"),
                            ("Z sim[p79-measuredmix] LightGBM", "MixGbm")]:
                for c, g_ in pr2[pr2.model == mdl].groupby("cls"):
                    put(f"ph{nm}Mae{c}", g_.w.sum() / g_.n_segments.sum())
    gap = os.path.join(RESULTS, "lira", "gap_summary.json")
    if os.path.exists(gap):
        G = json.load(open(gap)); put("gapRho", G["segment_match"]["spearman"]); put("gapN", G["segment_match"]["n_segments"], "{:,.0f}")
        put("gapLogRatio", G["segment_match"]["mean_log_ratio_real_minus_sim"], "{:+.2f}"); put("gapRatio", float(np.exp(G["segment_match"]["mean_log_ratio_real_minus_sim"])))
    se = csv("speed_exponent_by_domain.csv")
    if se is not None:
        for d, nm in [("LiRA motorway", "LiraMw"), ("LiRA urban", "LiraUrban"), ("Simulator (P79 profiles)", "Sim"),
                      ("BeamNG, raw-profile label", "BngRaw"), ("BeamNG, legacy label", "BngCorr")]:
            q = se[se.domain == d]
            if len(q):
                put(f"gamma{nm}", q.gamma.iloc[0]); put(f"gamma{nm}Lo", q.lo.iloc[0]); put(f"gamma{nm}Hi", q.hi.iloc[0])
    fs = csv("lira/fewshot_raw.csv")
    if fs is not None:
        fs = fs.assign(w=fs.seg_mae * fs.n_seg)
        per = fs.groupby(["model", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
        per["mae"] = per.w / per.n
        agg = per.groupby(["model", "k_km"]).mae.agg(["mean", lambda x: np.percentile(x, 2.5), lambda x: np.percentile(x, 97.5), "median"]).reset_index()
        agg.columns = ["model", "k", "mean", "lo", "hi", "median"]
        fn = {"real-only LightGBM": "RealGbm", "sim+real LightGBM (balanced weights)": "SimRealGbm", "real-only 1D-CNN": "RealCnn",
              "sim-pretrained 1D-CNN + real fine-tuning": "FtCnn", "real-only physics index": "RealPhys",
              "sim physics index + real intercept": "SimPhysInt", "sim-only LightGBM": "SimOnlyGbm", "sim-only physics index": "SimOnlyPhys",
              "sim-only 1D-CNN": "SimOnlyCnn"}
        kn = {"0": "Zero", "1": "One", "2": "Two", "5": "Five", "10": "Ten", "20": "Twenty", "all": "All"}
        for _, q in agg.iterrows():
            if q.model in fn and str(q.k) in kn:
                put(f"fs{fn[q.model]}{kn[str(q.k)]}", q["mean"]); put(f"fs{fn[q.model]}{kn[str(q.k)]}Lo", q.lo); put(f"fs{fn[q.model]}{kn[str(q.k)]}Hi", q.hi)
                put(f"fs{fn[q.model]}{kn[str(q.k)]}Med", q["median"])
        # by road class (urban = CPH routes, motorway = M routes): segment-weighted within each draw, mean over draws
        fs["road"] = np.where(fs.test_route.str.startswith("CPH"), "Urban", "Motorway")
        rc = fs.groupby(["model", "k_km", "draw", "road"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
        rc["mae"] = rc.w / rc.n
        for (mdl, k, road), g_ in rc.groupby(["model", "k_km", "road"]):
            if mdl in fn and str(k) in kn:
                put(f"fs{fn[mdl]}{kn[str(k)]}{road}", g_.mae.mean())
    zr = csv("lira/zeroshot_per_route.csv")
    if zr is not None:
        for mdl, nm in zn.items():
            for rt in ["CPH1", "CPH6", "M3", "M13"]:
                q = zr[(zr.model == mdl) & (zr.route == rt)]
                if len(q):
                    put(f"zs{nm}Mae{RN[rt]}", q.mae.iloc[0]); put(f"zs{nm}Bias{RN[rt]}", q.bias.iloc[0], "{:+.2f}")
    if pr is not None:
        for mdl, nm in names.items():
            for rt in ["CPH1", "CPH6", "M3", "M13"]:
                q = pr[(pr.model == mdl) & (pr.route == rt)]
                if len(q) and "bias" in q:
                    put(f"lira{nm}Bias{RN[rt]}", q.bias.iloc[0], "{:+.2f}")
    # ---------------- controlled simulation
    uv = csv("sim/unseen_vehicle_paired.csv")
    if uv is not None:
        for mdl, nm in [("M3 LightGBM", "Gbm"), ("M5 1D-CNN", "Cnn"), ("M2c RMS/v^alpha (alpha fitted)", "Phys"), ("M3 LightGBM (no speed)", "GbmNoSpeed"),
                        ("M2a RMS only (alpha=0)", "PhysA"), ("M2d legacy exponent 2", "PhysD")]:
            q = uv[uv.model == mdl]
            if len(q):
                q = q.iloc[0]; put(f"uv{nm}Seen", q.mae_seen); put(f"uv{nm}Unseen", q.mae_unseen); put(f"uv{nm}Rel", 100 * q.rel_diff, "{:+.0f}")
                put(f"uv{nm}RelHi", 100 * q.rel_hi, "{:+.0f}"); put(f"uv{nm}Pass", "yes" if q.generalises else "no", "{}")
    rg = csv("sim/vehicle_region_extrapolation.csv")
    if rg is not None:
        for mdl, nm in [("M3 LightGBM", "Gbm"), ("M5 1D-CNN", "Cnn"), ("M2c RMS/v^alpha (alpha fitted)", "Phys"), ("M5 1D-CNN (no speed)", "CnnNoSpeed")]:
            q = rg[rg.model == mdl]
            if len(q):
                q = q.iloc[0]; put(f"rg{nm}Low", q.mae_low_fs_unseen); put(f"rg{nm}High", q.mae_high_fs_unseen); put(f"rg{nm}Diff", q["diff"], "{:+.2f}")
                put(f"rg{nm}Bias", q.bias_high_fs, "{:+.2f}")
    sp = csv("sim/speed_invariance.csv"); sp2 = csv("sim/speed_invariance_p79trained.csv")
    for df, tag in [(sp, ""), (sp2, "Ptrain")]:
        if df is None:
            continue
        for _, q in df.iterrows():
            nm = {"M2a RMS only (alpha=0)": "PhysA", "M2b RMS/v^0.5": "PhysB", "M2c RMS/v^alpha (alpha fitted)": "PhysC", "M2d legacy exponent 2": "PhysD",
                  "M3 LightGBM": "Gbm", "M3 LightGBM (no speed)": "GbmNoSpeed", "M5 1D-CNN": "Cnn", "M5 1D-CNN (no speed)": "CnnNoSpeed",
                  "raw RMS of a_z (no model, not an IRI)": "Raw"}.get(q.model)
            if nm is None:
                continue
            sw = "Iso" if "iso" in q.sweep else "Pseven"
            put(f"sp{tag}{sw}{nm}", 100 * q.rel_change_40_100, "{:+.0f}"); put(f"sp{tag}{sw}{nm}Lo", 100 * q.ci_lo, "{:+.0f}")
            put(f"sp{tag}{sw}{nm}Hi", 100 * q.ci_hi, "{:+.0f}"); put(f"sp{tag}{sw}{nm}Pass", "yes" if q.invariant_40_100 else "no", "{}")
    rb = csv("sim/robustness.csv")
    if rb is not None:
        g = lambda fam, lev, mdl: rb[(rb.family == fam) & (rb.level == lev) & (rb.model == mdl)].mae
        for mdl, nm in [("M3 LightGBM", "Gbm"), ("M5 1D-CNN", "Cnn"), ("M2c RMS/v^alpha (alpha fitted)", "Phys"), ("M3 LightGBM (no speed)", "GbmNoSpeed")]:
            for fam, lev, tag in [("sampling_rate_hz", "25 Hz", "RateTwentyFive"), ("sampling_rate_hz", "200 Hz", "RateTwoHundred"),
                                  ("sampling_rate_hz", "50 Hz", "RateFifty"), ("sampling_rate_hz", "100 Hz", "RateHundred"),
                                  ("noise_x", "x0", "NoiseZero"), ("noise_x", "x8", "NoiseEight"), ("quantisation_g", "0.05 g", "QuantFive"),
                                  ("tilt_sd_deg", "0 deg", "TiltZero"), ("tilt_sd_deg", "20 deg", "TiltTwenty"), ("speed_bias", "+0%", "SpeedZero"),
                                  ("speed_bias", "+20%", "SpeedPlusTwenty"), ("speed_bias", "-20%", "SpeedMinusTwenty"), ("speed_bias", "GPS 1 Hz", "SpeedGps"),
                                  ("missing_samples", "0%", "MissZero"), ("missing_samples", "40%", "MissForty"), ("mount_resonance", "rigid", "MountRigid"),
                                  ("mount_resonance", "15 Hz", "MountFifteen")]:
                s_ = g(fam, lev, mdl)
                if len(s_):
                    put(f"rb{nm}{tag}", s_.iloc[0])
    pv = csv("pvs/pvs_auc.csv")
    if pv is not None:
        for t, tn in [("A: asphalt vs cobblestone+dirt", "Surf"), ("B: good vs regular+bad", "Good"), ("C: bad vs regular (cobblestone+dirt only)", "Bad")]:
            for p_, pn in [("speed", "Speed"), ("RMS", "Rms"), ("RMS/sqrt(v)", "RmsV"), ("model", "Model"), ("model+speed", "ModelSpeed"),
                           ("model+RMS", "ModelRms"), ("model+speed+RMS", "All"), ("speed+RMS", "SpeedRms")]:
                q = pv[(pv.task == t) & (pv.predictors == p_)]
                if len(q):
                    q = q.iloc[0]; put(f"pvs{tn}{pn}", q.auc); put(f"pvs{tn}{pn}Lo", q.auc_lo); put(f"pvs{tn}{pn}Hi", q.auc_hi)
        W = csv("pvs/pvs_windows.csv")
        if W is not None:
            put("pvsWindows", len(W), "{:,.0f}"); put("pvsCells", W.cell.nunique(), "{:.0f}")
            sp_ = (3.6 * W.groupby("surface").speed.mean()).to_dict()
            put("pvsSpeedAsphalt", sp_.get("Asphalt", np.nan), "{:.0f}"); put("pvsSpeedCobble", sp_.get("Cobblestone", np.nan), "{:.0f}"); put("pvsSpeedDirt", sp_.get("Dirt", np.nan), "{:.0f}")
    # ---------------- write
    for k in list(M):        # unsigned variants for prose ("over-corrects by 32 %")
        if isinstance(M[k], str) and M[k][:1] in "+-" and M[k][1:2].isdigit():
            M[k + "Abs"] = M[k][1:]
    bad = [k for k in M if not k.isalpha()]
    assert not bad, f"non-alphabetic macro names: {bad}"

    def tex(v):              # math-mode signs: in OT1 text mode '<' prints as an inverted '!' and '-' as a hyphen
        for s in "+-<":
            if v.startswith(s):
                return f"\\ensuremath{{{s}}}" + v[1:]
        return v
    out = os.path.join(RESCUE, "paper", "numbers.tex")
    with open(out, "w", encoding="utf-8") as f:
        f.write("% AUTO-GENERATED by research_rescue/make_numbers.py from results/ - do not edit by hand.\n")
        for k in sorted(M):
            f.write(f"\\newcommand{{\\{k}}}{{{tex(M[k])}}}\n")
    json.dump(M, open(os.path.join(RESULTS, "paper_numbers.json"), "w"), indent=1, sort_keys=True)
    print(f"{len(M)} macros written; missing: {sum(v == '??' for v in M.values())}")


if __name__ == "__main__":
    main()
