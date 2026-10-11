"""Revision v3: every v3 number quoted in the paper as a LaTeX macro (paper/numbers_v3.tex), generated from
results/v3/* (and results/v2/* where a v3 statement re-reads a v2 result). Missing inputs print '??' and the script
reports them. Macro names are alphabetic and must not collide with paper/numbers.tex (v1) or paper/numbers_v2.tex.
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.paths import RESULTS, RESCUE  # noqa: E402

V2, V3 = os.path.join(RESULTS, "v2"), os.path.join(RESULTS, "v3")
M = {}
VID = {"V0": "Vzero", "V1": "Vone", "V2": "Vtwo", "V3": "Vthree", "V4": "Vfour", "V5": "Vfive", "V6": "Vsix",
       "V7": "Vseven", "V8": "Veight", "V9": "Vnine", "V10": "Vten", "REAL": "Real"}
KN = {1: "One", 2: "Two", 5: "Five", 10: "Ten", 20: "Twenty", 40: "Forty"}
RN = {"CPH1": "CphOne", "CPH6": "CphSix", "M3": "MwThree", "M13": "MwThirteen", "mean": "Mean"}
MEAS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
SENS = [v for v in MEAS if v != "V4"]
HIDEF = ["V1", "V3", "V5"]


def put(name, value, fmt="{:.2f}"):
    try:
        if isinstance(value, str):
            M[name] = value
        elif value is None or (isinstance(value, float) and not np.isfinite(value)):
            M[name] = "??"
        else:
            M[name] = fmt.format(value)
    except Exception:  # noqa: BLE001
        M[name] = "??"


S2 = "{:+.2f}"
S3 = "{:+.3f}"


def rng(a, b, fmt="{:.0f}"):
    """'a--b', or a single value when both ends print the same (avoids '20--20')."""
    x, y = fmt.format(a), fmt.format(b)
    return x if x == y else f"{x}--{y}"


def pooled(D, keys):
    """n_seg-weighted pooled MAE per draw over the four held-out routes, and within-route MAE (mean of route MAEs)."""
    D = D.assign(w=D.seg_mae * D.n_seg, wb=D.seg_bias * D.n_seg)
    a = D.groupby(keys + ["draw"]).agg(w=("w", "sum"), wb=("wb", "sum"), n=("n_seg", "sum"), within=("seg_mae", "mean"),
                                       nf=("fold", "nunique")).reset_index()
    assert (a.nf == 4).all()
    a["mae"] = a.w / a.n; a["bias"] = a.wb / a.n
    return a.drop(columns=["w", "wb", "n", "nf"])


def main():
    # ---------------- k km of paired drives: pass density (results/v2/value_of_simulation.csv, real_only arm)
    R4 = pd.read_csv(os.path.join(V2, "value_of_simulation.csv"))
    q = R4[(R4.arm == "real_only")]
    for k in (1, 2, 5, 10, 20, 40):
        g = q[q.k_km == k]
        put("kdKm" + KN[k], g.km_real.mean(), "{:.1f}")
        put("kdUnits" + KN[k], g.n_real_units.mean(), "{:,.0f}")
        put("kdUnits" + KN[k] + "Min", g.n_real_units.min(), "{:,.0f}"); put("kdUnits" + KN[k] + "Max", g.n_real_units.max(), "{:,.0f}")
        put("kdPasses" + KN[k], (g.n_real_units / (10 * g.km_real)).mean(), "{:.1f}")
        put("kdDriveKm" + KN[k], g.n_real_units.mean() * 0.1, "{:.0f}")

    # ---------------- V3-1 pooled sim+real arm, paired with real-only, real-only index, level offset, affine
    P = pd.read_csv(os.path.join(V3, "pooled_vs_real.csv"))
    pp = pooled(P, ["vid", "k_km"])
    real = pooled(R4[R4.arm == "real_only"], ["k_km"]).rename(columns={"mae": "real", "within": "real_within", "bias": "real_bias"})
    ridx = pooled(pd.read_csv(os.path.join(V2, "value_real_index.csv")), ["k_km"]).rename(
        columns={"mae": "ridx", "within": "ridx_within", "bias": "ridx_bias"})
    C = pd.read_csv(os.path.join(V2, "variants_calibration.csv")); C = C[C.model == "GBM"]
    cal = pooled(C[C.calib == "intercept"], ["vid", "k_km"]).rename(columns={"mae": "cal", "within": "cal_within", "bias": "cal_bias"})
    aff = pooled(C[C.calib == "affine"], ["vid", "k_km"]).rename(columns={"mae": "aff", "within": "aff_within", "bias": "aff_bias"})
    A = (pp.merge(real, on=["k_km", "draw"]).merge(ridx, on=["k_km", "draw"], how="left")
         .merge(cal, on=["vid", "k_km", "draw"], how="left").merge(aff, on=["vid", "k_km", "draw"], how="left"))
    A["d_real"] = A.mae - A.real; A["d_ridx"] = A.mae - A.ridx; A["d_cal"] = A.mae - A.cal; A["d_aff"] = A.mae - A.aff
    A["d_real_cal"] = A.cal - A.real
    S = A.groupby(["vid", "k_km"]).agg(mae=("mae", "mean"), within=("within", "mean"), bias=("bias", "mean"),
                                       d_real=("d_real", "mean"), w_real=("d_real", lambda x: int((x < 0).sum())),
                                       d_ridx=("d_ridx", "mean"), w_ridx=("d_ridx", lambda x: int((x < 0).sum())),
                                       d_cal=("d_cal", "mean"), w_cal=("d_cal", lambda x: int((x < 0).sum())),
                                       d_aff=("d_aff", "mean"), cal=("cal", "mean"), cal_within=("cal_within", "mean"),
                                       aff=("aff", "mean"), aff_within=("aff_within", "mean"),
                                       real=("real", "mean"), real_within=("real_within", "mean"),
                                       w_real_cal=("d_real_cal", lambda x: int((x < 0).sum())),
                                       d_real_cal=("d_real_cal", "mean"), n=("draw", "size")).reset_index()
    assert (S.n == 20).all()
    S.to_csv(os.path.join(V3, "pooled_summary.csv"), index=False)
    # reproduction check against review/v3_checks (pooled MAE of V0, V1, V3, V5 at 5, 10, 20 km)
    ref = {("V0", 5): 0.452, ("V0", 10): 0.453, ("V0", 20): 0.435, ("V1", 5): 0.467, ("V1", 10): 0.467, ("V1", 20): 0.443,
           ("V3", 5): 0.473, ("V3", 10): 0.476, ("V3", 20): 0.447, ("V5", 5): 0.466, ("V5", 10): 0.469, ("V5", 20): 0.442}
    Si = S.set_index(["vid", "k_km"])
    worst = max(abs(Si.loc[key, "mae"] - v) for key, v in ref.items())
    assert worst <= 0.002 + 5e-4, f"pooled arm does not reproduce review check c4 (max |diff| {worst:.4f})"
    put("poReproMaxDiff", worst, "{:.4f}")
    for k in (1, 2, 5, 10, 20):
        g = S[(S.k_km == k) & S.vid.isin(MEAS)]
        kn = KN[k]
        put("poMae" + kn + "Min", g.mae.min()); put("poMae" + kn + "Max", g.mae.max())
        put("poMaeSpread" + kn, g.mae.max() - g.mae.min()); put("poCalSpread" + kn, g.cal.max() - g.cal.min())
        put("poWithin" + kn + "Min", g.within.min(), "{:.3f}"); put("poWithin" + kn + "Max", g.within.max(), "{:.3f}")
        put("poCalWithin" + kn + "Min", g.cal_within.min(), "{:.3f}"); put("poCalWithin" + kn + "Max", g.cal_within.max(), "{:.3f}")
        put("poCal" + kn + "Min", g.cal.min()); put("poCal" + kn + "Max", g.cal.max())
        put("poAff" + kn + "Min", g.aff.min()); put("poAff" + kn + "Max", g.aff.max())
        put("poDiff" + kn + "Min", g.d_real.min(), S2); put("poDiff" + kn + "Max", g.d_real.max(), S2)
        put("poWins" + kn + "Min", g.w_real.min(), "{:.0f}"); put("poWins" + kn + "Max", g.w_real.max(), "{:.0f}")
        put("poWins" + kn + "Range", rng(g.w_real.min(), g.w_real.max()))
        put("poDiffIdx" + kn + "Min", g.d_ridx.min(), S2); put("poDiffIdx" + kn + "Max", g.d_ridx.max(), S2)
        put("poWinsIdx" + kn + "Min", g.w_ridx.min(), "{:.0f}"); put("poWinsIdx" + kn + "Max", g.w_ridx.max(), "{:.0f}")
        put("poBeat" + kn, int(((g.d_real < 0) & (g.w_real >= 15)).sum()), "{:.0f}")
        put("poRealWithin" + kn, g.real_within.iloc[0], "{:.3f}"); put("poReal" + kn, g.real.iloc[0])
        hd = g[g.vid.isin(HIDEF)]; ld = g[~g.vid.isin(HIDEF)]
        for grp, nm in ((hd, "HiDef"), (ld, "LoDef")):
            put("po" + nm + "Mae" + kn + "Min", grp.mae.min()); put("po" + nm + "Mae" + kn + "Max", grp.mae.max())
            put("po" + nm + "Diff" + kn + "Min", grp.d_real.min(), S2); put("po" + nm + "Diff" + kn + "Max", grp.d_real.max(), S2)
            put("po" + nm + "Wins" + kn + "Min", grp.w_real.min(), "{:.0f}"); put("po" + nm + "Wins" + kn + "Max", grp.w_real.max(), "{:.0f}")
            put("po" + nm + "Cal" + kn + "Min", grp.cal.min()); put("po" + nm + "Cal" + kn + "Max", grp.cal.max())
            put("po" + nm + "DiffCal" + kn + "Min", grp.d_cal.min(), S3); put("po" + nm + "DiffCal" + kn + "Max", grp.d_cal.max(), S3)
            put("po" + nm + "CalWins" + kn + "Min", grp.w_real_cal.min(), "{:.0f}"); put("po" + nm + "CalWins" + kn + "Max", grp.w_real_cal.max(), "{:.0f}")
        for _, r in S[S.k_km == k].iterrows():
            v = VID[r.vid]
            put("po" + v + "Mae" + kn, r.mae); put("po" + v + "Diff" + kn, r.d_real, S2); put("po" + v + "Wins" + kn, r.w_real, "{:.0f}")
            put("po" + v + "Within" + kn, r.within, "{:.3f}"); put("po" + v + "DiffCal" + kn, r.d_cal, S2)
            put("po" + v + "WinsCal" + kn, r.w_cal, "{:.0f}"); put("po" + v + "Bias" + kn, r.bias, S2)
    # pre-registered H1 (PROTOCOL_V3 V3-1): every variant better than real-only on average at k <= 10 km, and not worse
    # by more than 0.02 m/km at 20 km; evaluated over V0-V8 and over V0-V8 + V10
    for grp, nm in ((MEAS, "Meas"), (MEAS + ["V10"], "All")):
        g = S[S.vid.isin(grp)]
        ok = bool((g[g.k_km <= 10].d_real < 0).all() and (g[g.k_km == 20].d_real <= 0.02).all())
        put("poHone" + nm, "holds" if ok else "does not hold")
    put("poBeatAllK", int(sum(((S.vid == v) & (S.d_real < 0) & (S.w_real >= 15)).sum() == 5 for v in MEAS)), "{:.0f}")
    # affine map against the better of level offset and joint training (V0-V8)
    for k in (1, 2, 5, 10, 20):
        g = S[(S.k_km == k) & S.vid.isin(MEAS)]
        put("poAffWorse" + KN[k], int((g.aff > np.minimum(g.cal, g.mae)).sum()), "{:.0f}")
        put("poAffWorseBoth" + KN[k], int((g.aff > np.maximum(g.cal, g.mae)).sum()), "{:.0f}")
    # per route (pooled minus real-only, mean over draws)
    PR = P.merge(R4[R4.arm == "real_only"][["fold", "k_km", "draw", "seg_mae"]].rename(columns={"seg_mae": "real"}),
                 on=["fold", "k_km", "draw"])
    PR["d"] = PR.seg_mae - PR.real
    G = PR[PR.vid.isin(MEAS)].groupby(["vid", "k_km", "fold"]).d.mean().reset_index()
    G.to_csv(os.path.join(V3, "pooled_by_route.csv"), index=False)
    for k in (5, 10, 20):
        g = G[G.k_km == k]
        put("poRoute" + KN[k] + "DiffMin", g.d.min(), S3); put("poRoute" + KN[k] + "DiffMax", g.d.max(), S3)
        put("poRoute" + KN[k] + "Neg", int((g.d < 0).sum()), "{:.0f}"); put("poRoute" + KN[k] + "Cells", len(g), "{:.0f}")
        put("poRoute" + KN[k] + "Pos", int((g.d > 0).sum()), "{:.0f}")
        for f in ("CPH1", "CPH6", "M3", "M13"):
            put("poRoute" + KN[k] + RN[f] + "Pos", int((g[g.fold == f].d > 0).sum()), "{:.0f}")
        for f in ("CPH1", "CPH6", "M3", "M13"):
            h = g[g.fold == f]
            put("poRoute" + KN[k] + RN[f] + "Min", h.d.min(), S3); put("poRoute" + KN[k] + RN[f] + "Max", h.d.max(), S3)

    # ---------------- V3-2 test-route uncertainty of the calibration comparison
    U = pd.read_csv(os.path.join(V3, "calib_uncertainty.csv"))
    for k in (5, 20):
        for arm, an in (("sim_all_cal", "Cal"), ("sim_real_pooled", "Pool")):
            g = U[(U.k_km == k) & (U.arm == arm)]
            kn = KN[k]
            put("cu" + an + kn + "DiffMin", g["diff"].min(), S2); put("cu" + an + kn + "DiffMax", g["diff"].max(), S2)
            put("cu" + an + kn + "HiMax", g.hi.max(), S2); put("cu" + an + kn + "LoMin", g.lo.min(), S2)
            put("cu" + an + kn + "ExclNeg", int((g.hi < 0).sum()), "{:.0f}"); put("cu" + an + kn + "ExclPos", int((g.lo > 0).sum()), "{:.0f}")
            put("cu" + an + kn + "N", len(g), "{:.0f}")
            for _, r in g.iterrows():
                v = VID[r.vid]
                put("cu" + an + v + kn, r["diff"], S2); put("cu" + an + v + kn + "Lo", r.lo, S2); put("cu" + an + v + kn + "Hi", r.hi, S2)
        put("cuBlocks", int(U.n_blocks.iloc[0]), "{:.0f}")

    # ---------------- V3-3 band-limited intervention
    BL = pd.read_csv(os.path.join(V3, "band_limited.csv"))
    sn = {"full": "Full", "no1015": "NoHigh", "lt10": "Low"}
    for s, name in sn.items():
        g = BL[(BL.features == s) & BL.vid.isin(SENS)]
        for col, cn in (("bias", "Bias"), ("lvl_mean", "Lvl"), ("lvl_urban", "LvlUrban"), ("lvl_motorway", "LvlMotorway")):
            put("bl" + name + "Spread" + cn, g[col].max() - g[col].min())
            put("bl" + name + cn + "Min", g[col].min(), S2); put("bl" + name + cn + "Max", g[col].max(), S2)
        g9 = BL[(BL.features == s) & BL.vid.isin(MEAS)]
        put("bl" + name + "CalMin", g9.mae_level5km.min()); put("bl" + name + "CalMax", g9.mae_level5km.max())
        put("bl" + name + "CalWithinMin", g9.mae_within_level5km.min(), "{:.3f}"); put("bl" + name + "CalWithinMax", g9.mae_within_level5km.max(), "{:.3f}")
        put("bl" + name + "RhoMin", g9.rho_within.min()); put("bl" + name + "RhoMax", g9.rho_within.max())
        v4 = BL[(BL.features == s) & (BL.vid == "V4")].iloc[0]
        put("bl" + name + "VfourBias", v4.bias, S2); put("bl" + name + "VfourLvl", v4.lvl_mean, S2)
        put("bl" + name + "VfourLvlUrban", v4.lvl_urban, S2); put("bl" + name + "VfourLvlMotorway", v4.lvl_motorway, S2)
        v0 = BL[(BL.features == s) & (BL.vid == "V0")].iloc[0]
        put("bl" + name + "VzeroCal", v0.mae_level5km); put("bl" + name + "VzeroCalWithin", v0.mae_within_level5km, "{:.3f}")
    # spread ratios from the unrounded spreads (H3: lt10 <= 50 % of full for the mean and both class levels; no1015 within 20 %)
    def spread(s, col):
        g = BL[(BL.features == s) & BL.vid.isin(SENS)][col]
        return g.max() - g.min()
    nochg = []
    for col, cn in (("bias", "Bias"), ("lvl_mean", "Lvl"), ("lvl_urban", "LvlUrban"), ("lvl_motorway", "LvlMotorway")):
        put("blRatio" + cn, 100 * spread("lt10", col) / spread("full", col), "{:.0f}")
        put("blRatioNoHigh" + cn, 100 * spread("no1015", col) / spread("full", col), "{:.0f}")
        nochg.append(abs(100 * spread("no1015", col) / spread("full", col) - 100))
    put("blNoHighMaxChange", float(np.ceil(max(nochg))), "{:.0f}")
    h3 = all(spread("lt10", c) <= 0.5 * spread("full", c) for c in ("lvl_mean", "lvl_urban", "lvl_motorway")) and max(nochg) < 20
    v4l = BL[(BL.features == "lt10") & (BL.vid == "V4")].lvl_mean.iloc[0]
    g8 = BL[(BL.features == "lt10") & BL.vid.isin(SENS)].lvl_mean
    put("blHthreeHolds", "holds" if h3 else "does not hold"); put("blHthreeBHolds", "holds" if not (g8.min() <= v4l <= g8.max()) else "does not hold")
    put("blNfeatLow", 5, "{:.0f}")

    # ---------------- V3-4 band associations
    BA = pd.read_csv(os.path.join(V3, "band_associations.csv"))
    fn = {"log_band_0.5_2": "Low", "log_band_2_5": "Mid", "log_band_5_10": "MidHigh", "log_band_10_15": "High", "log_rms": "Rms"}
    tn = {"bias": "Bias", "lvl_mean": "Lvl", "spread": "Spread"}
    for _, r in BA.iterrows():
        k = fn[r.feature] + tn[r.target]
        put("baSp" + k, r.spearman); put("baPe" + k, r.pearson); put("baRtwo" + k, r.r2)

    # ---------------- V3-5 level decomposition
    LD = pd.read_csv(os.path.join(V3, "level_decomposition.csv")).set_index("vid")
    for v, r in LD.iterrows():
        k = "ld" + VID[v]
        put(k + "Urban", r.lvl_urban, S3); put(k + "Motorway", r.lvl_motorway, S3); put(k + "Spread", r.spread, "{:.2f}")
        put(k + "Mean", r.lvl_mean, S3); put(k + "PctUrban", r.pct_urban, "{:+.0f}"); put(k + "PctMotorway", r.pct_motorway, "{:+.0f}")
        put(k + "PctMotorwayAbs", abs(r.pct_motorway), "{:.0f}")
    g = LD.loc[MEAS]
    put("ldSpreadCalRho", spearmanr(g.spread, g.mae_level5km)[0])
    put("ldSpreadMin", g.spread.min()); put("ldSpreadMax", g.spread.max())
    put("ldHiDefSpreadMin", g.loc[HIDEF].spread.min()); put("ldHiDefSpreadMax", g.loc[HIDEF].spread.max())
    lo = g.drop(index=HIDEF)
    put("ldLoDefSpreadMin", lo.spread.min()); put("ldLoDefSpreadMax", lo.spread.max())
    put("ldCalWithinMin", g.mae_within_level5km.min(), "{:.3f}"); put("ldCalWithinMax", g.mae_within_level5km.max(), "{:.3f}")
    put("ldRealWithin", LD.loc["REAL"].mae_within, "{:.3f}")
    put("ldMotorwayPctMin", g.pct_motorway.min(), "{:+.0f}"); put("ldMotorwayPctMax", g.pct_motorway.max(), "{:+.0f}")
    # vehicle population (V4: V0's sensor mixture, one mid-range vehicle instead of 30) against V0, zero-shot LightGBM
    SV = pd.read_csv(os.path.join(V2, "summary_variants.csv")); SV = SV[SV.model == "GBM"].set_index("vid")
    put("vpVehicleEffBias", SV.loc["V4", "bias"] - SV.loc["V0", "bias"], S2)
    put("vpVehicleEffLvl", LD.loc["V4", "lvl_mean"] - LD.loc["V0", "lvl_mean"], S2)
    G = pd.read_csv(os.path.join(V2, "band_gain.csv")).set_index(["vid", "feature"])
    for v in ("V0", "V4"):
        put("vp" + VID[v] + "RatioHigh", G.loc[(v, "log_band_10_15"), "ratio"]); put("vp" + VID[v] + "RatioRms", G.loc[(v, "log_rms"), "ratio"])

    # ---------------- V3-6 paired ranking test
    RP = pd.read_csv(os.path.join(V3, "rank_paired.csv"))
    mn = {"real LightGBM": "Real", "V0 LightGBM (zero-shot)": "Vzero", "V1 LightGBM (zero-shot)": "Vone"}
    for (metric, model), g in RP[RP["diff"].notna()].groupby(["metric", "model"]):
        k = "rp" + ("Rho" if metric == "rho" else "Prho") + mn[model]
        for _, r in g.iterrows():
            put(k + RN[r.route], r["diff"], S3); put(k + RN[r.route] + "Lo", r.lo, S3); put(k + RN[r.route] + "Hi", r.hi, S3)
    rr = RP[(RP.metric == "rho") & RP["diff"].notna() & (RP.route != "mean")]
    put("rpAbsMax", float(np.ceil(100 * rr["diff"].abs().max()) / 100), "{:.2f}")      # upper bound: "within rpAbsMax"
    put("rpAbsMaxExact", rr["diff"].abs().max(), "{:.3f}")
    put("rpBlocksMwThirteen", int(RP[(RP.route == "M13") & RP.n_blocks.notna()].n_blocks.iloc[0]), "{:.0f}")

    # ---------------- V3-7 speed robustness
    SR = pd.read_csv(os.path.join(V3, "speed_robustness.csv"))
    qn = {"raw_rms": "Raw", "real_gbm": "Real", "sim_v0": "Sim", "diff": "Diff"}
    for _, r in SR.iterrows():
        k = "sr" + qn[r.quantity] + ("Urban" if r.cls == "urban" else "Motorway")
        put(k, r.base, S2); put(k + "Lo", r.base_lo, S2); put(k + "Hi", r.base_hi, S2)
        put(k + "UnitFe", r.unit_fe, S2)
        put(k + "Lsd", r.lsd, S2); put(k + "LsdLo", r.lsd_lo, S2); put(k + "LsdHi", r.lsd_hi, S2)
        put(k + "Cv", r.cv, S2); put(k + "CvLo", r.cv_lo, S2); put(k + "CvHi", r.cv_hi, S2)
    put("srCorrLsdUrban", SR[SR.cls == "urban"].corr_lv_lsd.iloc[0], S2)
    put("srCorrCvUrban", SR[SR.cls == "urban"].corr_lv_cv.iloc[0], S2)

    # ---------------- V3-9 no-simulator comparator
    NS = pd.read_csv(os.path.join(V3, "nosim_index.csv"))
    ns = pooled(NS, ["arm", "k_km"]).groupby(["arm", "k_km"]).mae.mean()
    an = {"idx05_level": "HalfLevel", "idx05_affine": "HalfAffine", "idxcar_affine": "CarAffine", "simidx_level": "SimIdxLevel"}
    for (arm, k), v in ns.items():
        put("ns" + an[arm] + KN[int(k)], v)
    AL = pd.read_csv(os.path.join(V3, "nosim_index_alpha.csv"))
    put("nsAlphaCarMin", AL.alpha_car.min()); put("nsAlphaCarMax", AL.alpha_car.max())
    put("nsAlphaSimMin", AL.alpha_sim.min()); put("nsAlphaSimMax", AL.alpha_sim.max())

    # ---------------- V3-10 pass density at 5 km
    PD = pd.read_csv(os.path.join(V3, "pass_density.csv"))
    pdm = pooled(PD.assign(vid=PD.vid.fillna("-")), ["arm", "vid", "m"])
    rd_ = pdm[pdm.arm == "real_only"].rename(columns={"mae": "real"})[["m", "draw", "real"]]
    pdm = pdm.merge(rd_, on=["m", "draw"])
    pdm["d"] = pdm.mae - pdm.real
    T = pdm.groupby(["arm", "vid", "m"]).agg(mae=("mae", "mean"), d=("d", "mean"), w=("d", lambda x: int((x < 0).sum()))).reset_index()
    T.to_csv(os.path.join(V3, "pass_density_summary.csv"), index=False)
    mm = {1: "One", 2: "Two", 5: "Five"}
    for m in (1, 2, 5):
        put("pdReal" + mm[m], T[(T.arm == "real_only") & (T.m == m)].mae.iloc[0])
        for arm, a_ in (("sim_all_cal", "Cal"), ("sim_real_pooled", "Pool")):
            g = T[(T.arm == arm) & (T.m == m) & T.vid.isin(MEAS)]
            put("pd" + a_ + mm[m] + "Min", g.mae.min()); put("pd" + a_ + mm[m] + "Max", g.mae.max())
            put("pd" + a_ + mm[m] + "WinsMin", g.w.min(), "{:.0f}"); put("pd" + a_ + mm[m] + "WinsMax", g.w.max(), "{:.0f}")
            put("pd" + a_ + mm[m] + "DiffMin", g.d.min(), S2); put("pd" + a_ + mm[m] + "DiffMax", g.d.max(), S2)
    wmin = int(min(T[(T.arm == a) & (T.m == 1) & T.vid.isin(MEAS)].w.min() for a in ("sim_all_cal", "sim_real_pooled")))
    put("pdOneAllDraws", "in every draw" if wmin == 20 else f"in at least {wmin} of 20 draws")
    pdu = PD.groupby(["m", "fold", "draw"]).n_real.first().groupby("m").mean()
    for m in (1, 2, 5):
        put("pdUnits" + mm[m], pdu.loc[m], "{:,.0f}")

    # ---------------- V3-11 relative errors per class (Table I estimators)
    E = pd.read_csv(os.path.join(V2, "summary_real_estimators.csv")).set_index("estimator")
    Uu = pd.read_csv(os.path.join(RESCUE, "data", "processed", "lira", "units.csv"))
    segm = Uu.drop_duplicates("segment")
    # PROTOCOL_V3 V3-11: MAE of the class (over all segments of its two held-out routes) / mean IRI of those segments
    nseg = {r: int((segm.route == r).sum()) for r in ("CPH1", "CPH6", "M3", "M13")}
    cls = {"urban": ("CPH1", "CPH6"), "motorway": ("M3", "M13")}
    iri_c = {c: segm[segm.route.isin(rs)].mri.mean() for c, rs in cls.items()}
    rel = []
    for est, r in E.iterrows():
        d = dict(estimator=est)
        for c, rs in cls.items():
            mae_c = sum(nseg[q] * r["mae_" + q] for q in rs) / sum(nseg[q] for q in rs)
            d["mae_" + c] = mae_c; d["iri_" + c] = iri_c[c]; d["rel_" + c] = 100 * mae_c / iri_c[c]
        rel.append(d)
    RE = pd.DataFrame(rel).set_index("estimator")
    RE.to_csv(os.path.join(V3, "relative_errors.csv"))
    put("reGbmUrban", RE.loc["M3 LightGBM", "rel_urban"], "{:.0f}"); put("reGbmMotorway", RE.loc["M3 LightGBM", "rel_motorway"], "{:.0f}")
    put("reSimUrban", RE.loc["Sim V0 LightGBM (zero-shot)", "rel_urban"], "{:.0f}")
    put("reSimMotorway", RE.loc["Sim V0 LightGBM (zero-shot)", "rel_motorway"], "{:.0f}")

    # ---------------- V3-8 M7 before/after the segment-grid fix
    old = pd.read_csv(os.path.join(RESCUE, "checkpoints", "v2_2026-10-03", "results", "v2", "physics_inversion.csv"))
    new = pd.read_csv(os.path.join(V2, "physics_inversion.csv"))
    for d, nm in ((old, "Old"), (new, "New")):
        g = d[(d.fold == "M13") & d.model.str.startswith("M7 quarter")].iloc[0]
        put("mtMwThirteen" + nm + "Mae", g.mae, "{:.3f}"); put("mtMwThirteen" + nm + "Seg", g.n_seg, "{:.0f}")
    put("mtNewSeg", int(new[new.model.str.startswith("M7 quarter")].n_seg.sum()), "{:,.0f}")

    # ---------------- write
    bad = [k for k in M if not re.fullmatch(r"[A-Za-z]+", k)]
    assert not bad, bad
    prev = set()
    for f in ("numbers.tex", "numbers_v2.tex"):
        prev |= set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", open(os.path.join(RESCUE, "paper", f), encoding="utf-8").read()))
    clash = sorted(set(M) & prev)
    assert not clash, clash

    def tex(v):
        for s in "+-<":
            if v.startswith(s):
                return f"\\ensuremath{{{s}}}" + v[1:]
        return v
    with open(os.path.join(RESCUE, "paper", "numbers_v3.tex"), "w", encoding="utf-8") as f:
        f.write("% AUTO-GENERATED by research_rescue/make_numbers_v3.py from results/v3/ (and results/v2/) - do not edit by hand.\n")
        for k in sorted(M):
            f.write(f"\\newcommand{{\\{k}}}{{{tex(M[k])}}}\n")
    json.dump(M, open(os.path.join(V3, "paper_numbers_v3.json"), "w"), indent=1, sort_keys=True)
    miss = [k for k, v in M.items() if v == "??"]
    print(f"{len(M)} v3 macros written; missing: {len(miss)}", miss[:40])


if __name__ == "__main__":
    main()
