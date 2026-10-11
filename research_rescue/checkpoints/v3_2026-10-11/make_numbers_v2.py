"""Revision v2: every v2 number quoted in the paper as a LaTeX macro (paper/numbers_v2.tex), generated from
results/v2/*. Missing inputs print '??'. Macro names are alphabetic and must not collide with paper/numbers.tex (v1).
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.paths import RESULTS, RESCUE  # noqa: E402

V2 = os.path.join(RESULTS, "v2")
M = {}
NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
       "8": "eight", "9": "nine", "10": "ten"}
VID = {"V0": "Vzero", "V1": "Vone", "V2": "Vtwo", "V3": "Vthree", "V4": "Vfour", "V5": "Vfive", "V6": "Vsix",
       "V7": "Vseven", "V8": "Veight", "V9": "Vnine", "V10": "Vten", "V7full": "VsevenFull", "V8full": "VeightFull",
       "B_corr": "Bcorr", "B_raw": "Braw", "REAL": "Real"}
KN = {1: "One", 2: "Two", 5: "Five", 10: "Ten", 20: "Twenty", 40: "Forty"}
RN = {"CPH1": "CphOne", "CPH6": "CphSix", "M3": "MwThree", "M13": "MwThirteen"}


def put(name, value, fmt="{:.2f}"):
    try:
        if isinstance(value, str):
            M[name] = value
        elif value is None or (isinstance(value, float) and not np.isfinite(value)):
            M[name] = "??"
        else:
            M[name] = fmt.format(value)
    except Exception:
        M[name] = "??"


def rd(n):
    p = os.path.join(V2, n)
    return pd.read_csv(p) if os.path.exists(p) else None


def main():
    # ---------------- real-data estimators
    E = rd("summary_real_estimators.csv")
    ek = {"M0 constant": "Const", "M1 speed only": "Speed", "M2c vibration index": "Index", "M3 LightGBM": "Gbm",
          "M3 LightGBM, no speed": "GbmNoSpeed", "M4 MLP": "Mlp", "M5 1D-CNN": "Cnn", "Sim V0 LightGBM (zero-shot)": "SimVzero",
          "Sim V10 LightGBM (zero-shot)": "SimVten", "M0b map-only road-class prior": "Map", "M7 quarter-car inversion": "Inv",
          "M7 + output calibration": "InvCal"}
    for _, r in E.iterrows():
        k = "vr" + ek[r.estimator]
        put(k + "Mae", r.mae); put(k + "MaeWithin", r.mae_within); put(k + "RhoWithin", r.rho_within)
        put(k + "PrhoWithin", r.prho_within); put(k + "Bias", r.bias, "{:+.2f}"); put(k + "Kappa", r.kappa)
        put(k + "RhoPooled", r.rho_pooled)
        for rt, nm in RN.items():
            put(k + "Mae" + nm, r.get(f"mae_{rt}", np.nan))
            if np.isfinite(r.get(f"rho_{rt}", np.nan)):              # undefined for constant predictors
                put(k + "Rho" + nm, r[f"rho_{rt}"])
        if not np.isfinite(r.rho_within):
            M.pop(k + "RhoWithin", None)
        if not np.isfinite(r.prho_within):                             # constant within every route: undefined
            M.pop(k + "PrhoWithin", None)
        if np.isfinite(r.get("d5", np.nan)):
            put(k + "Dfive", r.d5, "{:+.3f}"); put(k + "DfiveLo", r.d5_lo, "{:+.3f}"); put(k + "DfiveHi", r.d5_hi, "{:+.3f}")
            put(k + "DsegLo", r.dseg_lo, "{:+.3f}"); put(k + "DsegHi", r.dseg_hi, "{:+.3f}")
            put(k + "DoneLo", r.d1_lo, "{:+.3f}"); put(k + "DoneHi", r.d1_hi, "{:+.3f}")
            put(k + "DrouteLo", r.droute_lo, "{:+.2f}"); put(k + "DrouteHi", r.droute_hi, "{:+.2f}")
            put(k + "RoutesBetter", r.routes_better, "{:.0f}")
        if np.isfinite(r.get("perseed_d5", np.nan)):
            put(k + "PerseedDfive", r.perseed_d5, "{:+.3f}"); put(k + "PerseedDfiveLo", r.perseed_d5_lo, "{:+.3f}")
            put(k + "PerseedDfiveHi", r.perseed_d5_hi, "{:+.3f}")
    vr = json.load(open(os.path.join(V2, "verify_review_claims.json")))
    ns = vr["neural_seed_vs_ensemble"]
    put("vrCnnPerSeedMae", ns["M5 1D-CNN"]["mean_per_seed_mae"], "{:.3f}"); put("vrCnnEnsMae", ns["M5 1D-CNN"]["ensemble_mae"], "{:.3f}")
    for rt, nm in RN.items():
        put("vrCnnDeficit" + nm, ns["M5 1D-CNN"]["per_route_minus_gbm"][rt], "{:+.2f}")

    # ---------------- inference: autocorrelation, variance components
    A = rd("residual_acf.csv")
    for m, nm in (("REAL_GBM", "Gbm"), ("SIM_P79", "Sim"), ("INDEX", "Index")):
        for lag, ln in ((100, "Hundred"), (1000, "Km"), (2000, "TwoKm"), (5000, "FiveKm")):
            q = A[(A.model == m) & (A.lag_m == lag)]
            put("acf" + nm + ln, q.r.iloc[0] if len(q) else np.nan)
    VC = rd("variance_components.csv")
    for m, nm in (("REAL_GBM", "Real"), ("SIM_P79", "Sim")):
        q = VC[VC.model == m].iloc[0]
        put("vc" + nm + "Unit", 100 * q.sd_unit_effect, "{:.0f}"); put("vc" + nm + "UnitLo", 100 * q.sd_unit_lo, "{:.0f}")
        put("vc" + nm + "UnitHi", 100 * q.sd_unit_hi, "{:.0f}"); put("vc" + nm + "Segment", 100 * q.sd_segment_effect, "{:.0f}")
        put("vc" + nm + "Residual", 100 * q.sd_residual, "{:.0f}")

    # ---------------- simulator variants
    S = rd("summary_variants.csv")
    for _, r in S.iterrows():
        k = "vv" + VID[r.vid] + ("" if r.model == "GBM" else "Idx")
        put(k + "Mae", r.mae); put(k + "Bias", r.bias, "{:+.2f}"); put(k + "BiasUrban", r.bias_urban, "{:+.2f}")
        put(k + "BiasMotorway", r.bias_motorway, "{:+.2f}"); put(k + "MaeUrban", r.mae_urban); put(k + "MaeMotorway", r.mae_motorway)
        put(k + "ScaleB", r.scale_b); put(k + "RhoWithin", r.rho_within_mean); put(k + "PrhoWithin", r.prho_within_mean)
        put(k + "MaeWithin", r.mae_within_mean)
        for sc, sn in (("pooled", "Pooled"), ("urban", "Urban"), ("motorway", "Motorway")):
            put(k + "Elast" + sn, r.get(f"elast_{sc}", np.nan), "{:+.2f}")
            put(k + "Elast" + sn + "Lo", r.get(f"elast_{sc}_lo", np.nan), "{:+.2f}")
            put(k + "Elast" + sn + "Hi", r.get(f"elast_{sc}_hi", np.nan), "{:+.2f}")
        for kk, kn in KN.items():
            if f"intercept_k{kk}_mean" not in r or not np.isfinite(r.get(f"intercept_k{kk}_mean", np.nan)):
                continue                                          # R3 used k in {1, 2, 5, 10, 20}
            for kind, kd in (("intercept", "Cal"), ("affine", "Aff")):
                put(k + kd + kn, r.get(f"{kind}_k{kk}_mean", np.nan)); put(k + kd + kn + "Lo", r.get(f"{kind}_k{kk}_lo", np.nan))
                put(k + kd + kn + "Hi", r.get(f"{kind}_k{kk}_hi", np.nan))
    G = S[(S.model == "GBM") & S.vid.isin(["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"])]
    put("vvBiasMin", G.bias.min(), "{:+.2f}"); put("vvBiasMax", G.bias.max(), "{:+.2f}")
    put("vvMaeMin", G.mae.min()); put("vvMaeMax", G.mae.max())
    put("vvRhoMin", G.rho_within_mean.min()); put("vvRhoMax", G.rho_within_mean.max())
    put("vvPrhoMin", G.prho_within_mean.min()); put("vvPrhoMax", G.prho_within_mean.max())
    put("vvScaleMin", G.scale_b.min()); put("vvScaleMax", G.scale_b.max())
    for kk, kn in KN.items():
        col = f"intercept_k{kk}_mean"
        if col in G:
            put("vvCalMin" + kn, G[col].min()); put("vvCalMax" + kn, G[col].max())
    G10 = S[(S.model == "GBM") & S.vid.isin(["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V10"])]
    for kk, kn in KN.items():
        col = f"intercept_k{kk}_mean"
        if col in G10:
            put("vvTenCalMin" + kn, G10[col].min()); put("vvTenCalMax" + kn, G10[col].max())
    # factorial effects (E2): holder on minus off, family phone minus telematics (bias, MAE)
    b = S[S.model == "GBM"].set_index("vid")
    put("vvHolderEffTele", b.loc["V7", "bias"] - b.loc["V1", "bias"], "{:+.2f}")
    put("vvHolderEffPhone", b.loc["V2", "bias"] - b.loc["V8", "bias"], "{:+.2f}")
    put("vvFamilyEffRigid", b.loc["V8", "bias"] - b.loc["V1", "bias"], "{:+.2f}")
    put("vvFamilyEffHolder", b.loc["V2", "bias"] - b.loc["V7", "bias"], "{:+.2f}")

    # ---------------- value of simulation (equal budget)
    V = rd("summary_value_of_sim.csv")
    an = {"real_only": "RealOnly", "sim_same": "SimSame", "sim_same_cal": "SimSameCal", "sim_all": "SimAll", "sim_all_cal": "SimAllCal"}
    for _, r in V.iterrows():
        k = "vb" + an[r.arm] + KN[int(r.k_km)]
        put(k, r["mean"]); put(k + "Lo", r.lo); put(k + "Hi", r.hi)
        if r.arm == "sim_same":
            kk = "vbDiff" + KN[int(r.k_km)]
            put(kk, r["diff"], "{:+.2f}"); put(kk + "Lo", r.diff_lo, "{:+.2f}"); put(kk + "Hi", r.diff_hi, "{:+.2f}")
            put("vbShare" + KN[int(r.k_km)], 100 * r.share_sim_better, "{:.0f}")

    # ---------------- speed on real roads (within-segment elasticity)
    SP = rd("speed_real.csv")
    sm = {"RAW_RMS": "Raw", "REAL_GBM": "RealGbm", "REAL_GBM_nospeed": "RealGbmNoSpeed", "REAL_INDEX": "RealIdx",
          "REAL_SPEED": "RealSpeed", "REAL_MLP": "RealMlp", "REAL_CNN": "RealCnn", "SIM_V0_GBM": "SimGbm",
          "SIM_V0_INDEX": "SimIdx", "SIM_V10_GBM": "SimTenGbm"}
    for _, r in SP.iterrows():
        if r.model not in sm:
            continue
        k = "el" + sm[r.model] + {"pooled": "Pooled", "urban": "Urban", "motorway": "Motorway"}[r.scope]
        put(k, r.within_elasticity, "{:+.2f}"); put(k + "Lo", r.within_lo, "{:+.2f}"); put(k + "Hi", r.within_hi, "{:+.2f}")
        put(k + "Pct", r.change_40_100_pct, "{:+.0f}"); put(k + "Between", r.between_speed_coef, "{:+.2f}")
    simg = SP[SP.model.str.match(r"^SIM_V(\d+)_GBM$") & (SP.scope == "pooled")]
    put("elSimGbmVariantsMin", simg.within_elasticity.min(), "{:+.2f}"); put("elSimGbmVariantsMax", simg.within_elasticity.max(), "{:+.2f}")
    put("elSimGbmVariantsMedian", simg.within_elasticity.median(), "{:+.2f}")
    simi = SP[SP.model.str.match(r"^SIM_V(\d+)_INDEX$") & (SP.scope == "pooled") & ~SP.model.str.contains("V9")]
    put("elSimIdxVariantsMin", simi.within_elasticity.min(), "{:+.2f}"); put("elSimIdxVariantsMax", simi.within_elasticity.max(), "{:+.2f}")
    put("elSegments", SP[(SP.model == "REAL_GBM") & (SP.scope == "pooled")].n_segments.iloc[0], "{:,.0f}")
    put("elSdLogv", SP[(SP.model == "REAL_GBM") & (SP.scope == "pooled")].median_within_seg_sd_logv.iloc[0])

    # ---------------- vehicle sweep (S1)
    VS = rd("vehicle_sweep.csv")
    nn = {3: "Three", 10: "Ten", 30: "Thirty", 100: "Hundred", 300: "ThreeHundred"}
    for _, r in VS.iterrows():
        k = "vs" + ("" if r.model == "GBM" else "Idx") + nn[int(r.N)]
        put(k + "Seen", r.mae_seen); put(k + "Unseen", r.mae_unseen); put(k + "Rel", 100 * r.rel, "{:+.0f}")
        put(k + "RelHi", 100 * r.rel_hi, "{:.0f}"); put(k + "RelHiRoute", 100 * r.rel_hi_route_boot, "{:.0f}")
        put(k + "Meets", "yes" if r.meets_v1_criterion else "no")
    Dd = rd("vehicle_sweep_distance.csv")
    if Dd is not None and len(Dd):
        from scipy.stats import spearmanr
        put("vsDistRho", spearmanr(Dd.dist_nearest, Dd.mae)[0])

    # ---------------- spectra and band gains (E3/E4)
    R = rd("spectra_log10_diff.csv")
    bands = [(0.4, 2.0, "Low"), (2.0, 5.0, "Mid"), (5.0, 10.0, "MidHigh"), (10.0, 15.0, "High"), (15.0, 20.1, "Top")]
    cm = {"real-V1": "Vone", "real-V2": "Vtwo", "real-V3": "Vthree", "real-V5": "Vfive", "real-V7": "Vseven", "real-V8": "Veight",
          "all units: 52.6Hz-333Hz": "Alias"}
    for comp, g in R.groupby("comparison"):
        if comp not in cm:
            continue
        for lo, hi, bn in bands:
            q = g[(g.freq_hz > lo) & (g.freq_hz <= hi)]
            put("sp" + cm[comp] + bn, q.log10_diff.mean(), "{:+.2f}")
            put("sp" + cm[comp] + bn + "Pow", 10 ** q.log10_diff.mean(), "{:.1f}")
        put("sp" + cm[comp] + "Cells", g.n_cells.iloc[0], "{:,.0f}")
    hf = json.load(open(os.path.join(V2, "spectra_highfreq_333hz.json")))
    put("hfAboveTwenty", 100 * hf["share_above_20hz"], "{:.0f}"); put("hfAboveNyq", 100 * hf["share_above_26hz"], "{:.0f}")
    put("hfTenTwenty", 100 * hf["share_10_20hz"], "{:.0f}"); put("hfUnits", hf["n_units"], "{:,.0f}")
    BG = rd("band_gain.csv")
    from scipy.stats import spearmanr, pearsonr
    zb = S[(S.model == "GBM")].set_index("vid").bias
    for f, fn in (("log_rms", "Rms"), ("log_band_10_15", "High"), ("log_band_2_5", "Mid"), ("log_band_0.5_2", "Low")):
        g = BG[BG.feature == f].set_index("vid")
        vids = [v for v in g.index if v in zb.index]
        put("bgRho" + fn, spearmanr(np.log(g.loc[vids, "ratio"]), zb.loc[vids])[0])
        put("bgR" + fn, pearsonr(np.log(g.loc[vids, "ratio"]), zb.loc[vids])[0])
        for v in vids:
            put("bg" + VID[v] + fn, g.loc[v, "ratio"])
        put("bg" + fn + "Min", g.loc[vids, "ratio"].min()); put("bg" + fn + "Max", g.loc[vids, "ratio"].max())
        put("bg" + fn + "SlopeMin", g.loc[vids, "slope"].min()); put("bg" + fn + "SlopeMax", g.loc[vids, "slope"].max())

    # ---------------- unit-disjoint baseline, Bajic anchor, passes needed, ARAN, physics inversion
    UD = rd("unit_disjoint.csv")
    for _, r in UD.iterrows():
        k = "ud" + RN[r.fold]
        put(k + "Dis", r.mae_unit_disjoint); put(k + "Ctrl", r.mae_size_matched_mean); put(k + "CtrlLo", r.mae_size_matched_min)
        put(k + "CtrlHi", r.mae_size_matched_max); put(k + "Full", r.mae_v1_all_units); put(k + "Ntrain", r.n_train_units, "{:,.0f}")
        put(k + "Classes", "both" if r.both_classes else "urban only")
    BJ = rd("bajic_anchor.csv")
    bjn = {"train mean (baseline)": "Base", "LightGBM": "Gbm", "vibration index (alpha fitted)": "Idx", "MLP (5-seed mean prediction)": "Mlp"}
    for _, r in BJ.iterrows():
        k = "bj" + bjn[r.model]
        put(k + "Mae", r.mae, "{:.3f}"); put(k + "Rmse", r.rmse); put(k + "Rtwo", r.r2)
    put("bjNtest", BJ.n_test_segments.iloc[0], "{:.0f}"); put("bjNtrain", BJ.n_train_segments.iloc[0], "{:.0f}")
    PN = rd("passes_needed_fixed.csv")
    pm = {"real LightGBM": "Real", "real index (M2c)": "Idx", "sim LightGBM (V0)": "Sim"}
    for (m, road, n), g in PN.groupby(["model", "road", "n_passes"]):
        put("pf" + pm[m] + road.capitalize() + {1: "One", 2: "Two", 3: "Three", 5: "Five", 8: "Eight"}[n], g.mae.mean())
    put("pfSegUrban", PN[(PN.road == "urban")].n_segments.iloc[0], "{:.0f}"); put("pfSegMotorway", PN[(PN.road == "motorway")].n_segments.iloc[0], "{:.0f}")
    AR = rd("aran_rematch.csv").set_index("scope")
    for sc, sn in (("urban", "Urban"), ("motorway", "Motorway"), ("CPH1", "CphOne"), ("CPH6", "CphSix")):
        q = AR.loc[sc]
        put("ar" + sn + "Mae", q.mae); put("ar" + sn + "Bias", q.bias, "{:+.2f}"); put("ar" + sn + "Rho", q.spearman)
        put("ar" + sn + "R", q.pearson); put("ar" + sn + "MedRatio", q.median_ratio); put("ar" + sn + "ShareFifteen", 100 * q.share_above_15, "{:.0f}")
    PI = json.load(open(os.path.join(V2, "physics_inversion_check.json")))
    put("invCheckR", PI["log_pearson"]); put("invCheckRatio", PI["median_ratio"])
    PT = rd("physics_inversion.csv")
    q = PT[PT.model.str.startswith("M7 quarter")]
    put("invKone", q.K1.mean(), "{:.0f}"); put("invKtwo", q.K2.mean(), "{:.0f}"); put("invC", q.C.mean(), "{:.1f}")
    put("invU", q.U.mean()); put("invGain", q.gain.mean()); put("invFitRmse", q.fit_rmse_log.mean())
    put("invBodyHz", np.mean(np.sqrt(q.K2) / (2 * np.pi)), "{:.1f}")
    put("invHopHz", np.mean(np.sqrt((q.K1 + q.K2) / q.U) / (2 * np.pi)), "{:.0f}")

    # ---------------- variants grouped by a PRE-COMPUTED spectral property (10-15 Hz real/sim amplitude ratio), not by
    # their test error: large deficit (ratio >= 2) vs the rest
    g15 = BG[BG.feature == "log_band_10_15"].set_index("vid").ratio
    Sg = S[(S.model == "GBM")].set_index("vid")
    hi_def = [v for v in g15.index if g15[v] >= 2.0 and v in Sg.index]
    lo_def = [v for v in g15.index if g15[v] < 2.0 and v in Sg.index]
    put("vvHiDefList", ", ".join(hi_def)); put("vvLoDefList", ", ".join(lo_def))
    for grp, nm in ((hi_def, "HiDef"), (lo_def, "LoDef")):
        for col, cn in (("intercept_k5_mean", "CalFive"), ("intercept_k20_mean", "CalTwenty"), ("affine_k20_mean", "AffTwenty"),
                        ("bias_urban", "BiasUrban"), ("bias_motorway", "BiasMotorway"), ("bias", "Bias"), ("mae", "Mae")):
            fmt = "{:+.2f}" if cn.startswith("Bias") else "{:.2f}"
            put("vv" + nm + cn + "Min", Sg.loc[grp, col].min(), fmt); put("vv" + nm + cn + "Max", Sg.loc[grp, col].max(), fmt)
    put("bgHiDefRatioMin", g15[hi_def].min()); put("bgLoDefRatioMax", g15[lo_def].max())

    # ---------------- sensor perturbations (v1 robustness run, LightGBM): MAE and bias
    RB = pd.read_csv(os.path.join(RESULTS, "sim", "robustness.csv"))
    RB = RB[RB.model == "M3 LightGBM"].set_index(["family", "level"])
    for (fam, lev), nm in ((("mount_resonance", "rigid"), "MountRigid"), (("mount_resonance", "40 Hz"), "MountForty"),
                           (("mount_resonance", "25 Hz"), "MountTwentyFive"), (("mount_resonance", "15 Hz"), "MountFifteen"),
                           (("sampling_rate_hz", "200 Hz"), "RateTwoHundred"), (("sampling_rate_hz", "50 Hz"), "RateFifty"),
                           (("sampling_rate_hz", "25 Hz"), "RateTwentyFive"), (("speed_bias", "+20%"), "SpeedPlus"),
                           (("noise_x", "x8"), "NoiseEight"), (("tilt_sd_deg", "20 deg"), "TiltTwenty"), (("missing_samples", "40%"), "MissForty")):
        put("rbvGbmMae" + nm, RB.loc[(fam, lev), "mae"]); put("rbvGbmBias" + nm, RB.loc[(fam, lev), "bias"], "{:+.2f}")

    # ---------------- real-car transmissibility: frequency of the high-frequency peak (empirical, training routes)
    TR = rd("physics_transmissibility.csv")
    pk = [g[g.freq_hz > 8].sort_values("log_T_empirical").freq_hz.iloc[-1] for _, g in TR.groupby("fold")]
    put("invPeakHz", float(np.mean(pk)), "{:.1f}")

    # ---------------- speed terciles: within-route rank stability (real and simulation-trained LightGBM)
    TT = rd("speed_real_terciles.csv")
    for m, nm in (("REAL_GBM", "Real"), ("SIM_V0_GBM", "Sim")):
        q = TT[TT.model == m]
        put("terc" + nm + "RhoMin", q.rho.min()); put("terc" + nm + "RhoMax", q.rho.max())
        put("terc" + nm + "RhoMedian", q.rho.median())

    # ---------------- E5/E6: paired per-draw comparison with real-only training on the same k km (paired_vs_real.py)
    PV = rd("paired_vs_real.csv")
    meas = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
    for arm, an_ in (("sim_all_cal", "Cal"), ("sim_all_aff", "Aff"), ("sim_same", "Same"), ("sim_same_cal", "SameCal")):
        q = PV[(PV.arm == arm) & PV.vid.isin(meas)]
        for kk, g in q.groupby("k_km"):
            kn = KN[int(kk)]
            for grp, gn in ((meas, ""), (hi_def, "HiDef"), (lo_def, "LoDef")):
                h = g[g.vid.isin(grp)]
                if len(h) == 0:
                    continue
                put("pc" + an_ + gn + "Diff" + kn + "Min", h["diff"].min(), "{:+.2f}")
                put("pc" + an_ + gn + "Diff" + kn + "Max", h["diff"].max(), "{:+.2f}")
                put("pc" + an_ + gn + "Wins" + kn + "Min", h.n_better.min(), "{:.0f}")
                put("pc" + an_ + gn + "Wins" + kn + "Max", h.n_better.max(), "{:.0f}")
                put("pc" + an_ + gn + "Mae" + kn + "Min", h.mae.min()); put("pc" + an_ + gn + "Mae" + kn + "Max", h.mae.max())
                # E9: against the real-only vibration index fitted on the same k km
                put("pc" + an_ + gn + "DiffIdx" + kn + "Min", h.diff_idx.min(), "{:+.2f}")
                put("pc" + an_ + gn + "DiffIdx" + kn + "Max", h.diff_idx.max(), "{:+.2f}")
                put("pc" + an_ + gn + "WinsIdx" + kn + "Min", h.n_better_idx.min(), "{:.0f}")
                put("pc" + an_ + gn + "WinsIdx" + kn + "Max", h.n_better_idx.max(), "{:.0f}")
            put("pc" + an_ + "Nvar" + kn, g.vid.nunique(), "{:.0f}")
            for _, r in g.iterrows():
                put("pc" + an_ + VID[r.vid] + "Diff" + kn, r["diff"], "{:+.2f}"); put("pc" + an_ + VID[r.vid] + "Wins" + kn, r.n_better, "{:.0f}")
    put("pcDraws", int(PV.n_draws.max()), "{:.0f}")
    PR = rd("paired_vs_real_by_route.csv")
    for kk in (5, 10, 20):
        q = PR[(PR.k_km == kk) & PR.vid.isin(meas)]
        put("pcRoute" + KN[kk] + "DiffMin", q["diff"].min(), "{:+.2f}"); put("pcRoute" + KN[kk] + "DiffMax", q["diff"].max(), "{:+.2f}")
        put("pcRoute" + KN[kk] + "Neg", int((q["diff"] < 0).sum()), "{:.0f}"); put("pcRoute" + KN[kk] + "Cells", len(q), "{:.0f}")
    ri = PV[(PV.vid == "V0") & (PV.arm == "sim_same")].set_index("k_km").real_idx_mae
    for kk, v in ri.items():
        put("vbRealIdx" + KN[int(kk)], v)

    # ---------------- E4 by class: 10-15 Hz amplitude ratio real/sim on urban and motorway cells (V0-V8)
    BC = rd("band_gain_by_class.csv")
    h = BC[(BC.feature == "log_band_10_15") & BC.vid.isin(meas)].pivot(index="vid", columns="cls", values="ratio")
    put("bgcUrbanMin", h.urban.min()); put("bgcUrbanMax", h.urban.max())
    put("bgcMotorwayMin", h.motorway.min()); put("bgcMotorwayMax", h.motorway.max())
    put("bgcMotorwayLarger", int((h.motorway > h.urban).sum()), "{:.0f}"); put("bgcNvar", len(h), "{:.0f}")

    # ---------------- E7: speed scaling of raw vibration, simulation vs real car
    SS = rd("speed_scaling_sim.csv")
    for cls, cn in (("urban", "Urban"), ("motorway", "Motorway")):
        r = SS[(SS.source == "real") & (SS.cls == cls)].iloc[0]
        put("ssReal" + cn, r.elasticity); put("ssReal" + cn + "Lo", r.lo); put("ssReal" + cn + "Hi", r.hi)
        r = SS[(SS.source == "V0") & (SS.cls == cls)].iloc[0]
        put("ssVzero" + cn, r.elasticity); put("ssVzero" + cn + "Lo", r.lo); put("ssVzero" + cn + "Hi", r.hi)
        q = SS[SS.source.isin(meas) & (SS.cls == cls)]
        put("ssSim" + cn + "Min", q.elasticity.min()); put("ssSim" + cn + "Max", q.elasticity.max())
        put("ssSim" + cn + "LoMin", q.lo.min())
        # implied RMS increase between 40 and 100 km/h on a fixed road (%)
        put("ssReal" + cn + "Pct", 100 * (2.5 ** SS[(SS.source == "real") & (SS.cls == cls)].elasticity.iloc[0] - 1), "{:.0f}")
        put("ssVzero" + cn + "Pct", 100 * (2.5 ** r.elasticity - 1), "{:.0f}")
    put("ssNvar", SS[SS.source.isin(meas)].source.nunique(), "{:.0f}")

    # ---------------- speed elasticity of simulation-trained LightGBM across the nine measured-profile variants
    for sc, scn in (("pooled", "Pooled"), ("urban", "Urban"), ("motorway", "Motorway")):
        q = SP[SP.model.isin([f"SIM_{v}_GBM" for v in meas]) & (SP.scope == sc)]
        put("elSimGbmMeas" + scn + "Min", q.within_elasticity.min(), "{:+.2f}")
        put("elSimGbmMeas" + scn + "Max", q.within_elasticity.max(), "{:+.2f}")
        if sc == "pooled":
            put("elSimGbmMeasInside", int((q.within_elasticity.abs() <= 0.104).sum()), "{:.0f}")

    # ---------------- E8: paired elasticity differences, simulation-trained minus real-trained (5 km blocks)
    EP = rd("speed_paired.csv")
    for fam, fn, ref in (("GBM", "", "REAL_GBM"), ("INDEX", "Idx", "REAL_INDEX")):
        q = EP[EP.model.isin([f"SIM_{v}_{fam}" for v in meas]) & (EP.reference == ref)]
        for sc, scn in (("pooled", "Pooled"), ("urban", "Urban"), ("motorway", "Motorway")):
            h = q[q.scope == sc]
            put("ep" + fn + "Meas" + scn + "Min", h.diff_elasticity.min(), "{:+.2f}")
            put("ep" + fn + "Meas" + scn + "Max", h.diff_elasticity.max(), "{:+.2f}")
            put("ep" + fn + "Meas" + scn + "Excl", int(((h.lo > 0) | (h.hi < 0)).sum()), "{:.0f}")
            r = q[(q.model == f"SIM_V0_{fam}") & (q.scope == sc)].iloc[0]
            put("ep" + fn + "Vzero" + scn, r.diff_elasticity, "{:+.2f}")
            put("ep" + fn + "Vzero" + scn + "Lo", r.lo, "{:+.2f}"); put("ep" + fn + "Vzero" + scn + "Hi", r.hi, "{:+.2f}")
    q = EP[(EP.model == "SIM_V7_GBM") & (EP.scope == "pooled")].iloc[0]
    put("epVsevenPooled", q.diff_elasticity, "{:+.2f}")

    # ---------------- E10: within-route ranking by untrained vibration statistics
    RK = rd("ranking_untrained.csv").groupby("statistic")[["rho", "prho"]].mean()
    for st, sn in (("raw RMS", "Raw"), ("RMS/v^0.5", "Half"), ("RMS/v", "One")):
        put("rk" + sn + "Rho", RK.loc[st, "rho"]); put("rk" + sn + "Prho", RK.loc[st, "prho"])
    # offset-calibrated MAE of the six variants with the smaller 10-15 Hz deficit vs the real-trained model
    put("vvLoDefN", len(lo_def), "{:.0f}"); put("vvHiDefN", len(hi_def), "{:.0f}")

    # ---------------- width of 5 km-block vs segment-level intervals of paired differences
    IB = rd("inference_blocks.csv")
    w = IB.assign(w=IB.hi - IB.lo).pivot_table(index=["model", "reference"], columns="level", values="w")
    put("infWidthRatioMin", (w.block5km / w.segment).min(), "{:.1f}"); put("infWidthRatioMax", (w.block5km / w.segment).max(), "{:.1f}")

    # ---------------- write
    bad = [k for k in M if not re.fullmatch(r"[A-Za-z]+", k)]
    assert not bad, bad
    v1 = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", open(os.path.join(RESCUE, "paper", "numbers.tex"), encoding="utf-8").read()))
    clash = sorted(set(M) & v1)
    assert not clash, clash

    def tex(v):
        for s in "+-<":
            if v.startswith(s):
                return f"\\ensuremath{{{s}}}" + v[1:]
        return v
    with open(os.path.join(RESCUE, "paper", "numbers_v2.tex"), "w", encoding="utf-8") as f:
        f.write("% AUTO-GENERATED by research_rescue/make_numbers_v2.py from results/v2/ - do not edit by hand.\n")
        for k in sorted(M):
            f.write(f"\\newcommand{{\\{k}}}{{{tex(M[k])}}}\n")
    json.dump(M, open(os.path.join(V2, "paper_numbers_v2.json"), "w"), indent=1, sort_keys=True)
    print(f"{len(M)} v2 macros written; missing: {sum(v == '??' for v in M.values())}")
    print([k for k, v in M.items() if v == "??"][:40])


if __name__ == "__main__":
    main()
