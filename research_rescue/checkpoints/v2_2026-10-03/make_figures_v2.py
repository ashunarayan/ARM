"""Revision v2 figures (from results/v2/*.csv only). Colour = concept, fixed across figures:
real-trained = palette slot 0 (blue), simulation-trained = slot 1 (orange), simulation + calibration = slot 2 (green).
Outputs: figures/v2_*.pdf/png
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import plotting as PL  # noqa: E402
from common.plotting import plt, PALETTE, INK, INK2, GRID, DBL_W, COL_W  # noqa: E402
from common.paths import RESULTS, FIGURES  # noqa: E402

V2 = os.path.join(RESULTS, "v2")
C_REAL, C_SIM, C_CAL = PALETTE[0], PALETTE[1], PALETTE[2]
VLAB = {"V0": "V0 mixture (reference)", "V1": "V1 telematics-like, rigid", "V7": "V7 telematics-like, holder",
        "V8": "V8 phone-like, rigid", "V2": "V2 phone-like, holder", "V3": "V3 ideal sensor",
        "V5": "V5 telematics matched to LiRA", "V6": "V6 matched + phone-like", "V4": "V4 one vehicle",
        "V9": "V9 synthetic profiles", "V10": "V10 measured + synthetic", "REAL": "trained on real cars"}
ORDER = ["V0", "V1", "V7", "V8", "V2", "V3", "V5", "V6", "V4", "V10", "V9", "REAL"]


def rd(name):
    return pd.read_csv(os.path.join(V2, name))


def fig_variants():
    """Central figure: what transfers (within-route ranking) and what does not (level), per simulator variant."""
    S = rd("summary_variants.csv"); S = S[S.model == "GBM"].set_index("vid")
    vs = rd("summary_value_of_sim.csv").set_index(["arm", "k_km"])
    real_k5 = vs.loc[("real_only", 5), "mean"]; real_all = S.loc["REAL", "mae"]
    rows = [v for v in ORDER if v in S.index]
    y = np.arange(len(rows))[::-1]
    fig, ax = plt.subplots(1, 3, figsize=(DBL_W, 3.35), sharey=True, gridspec_kw=dict(width_ratios=[1, 1, 1.5]))
    # (a) within-route ranking
    a = ax[0]
    for yi, v in zip(y, rows):
        col = C_REAL if v == "REAL" else C_SIM
        a.plot(S.loc[v, "rho_within_mean"], yi, "o", color=col, ms=4)
    rk = rd("ranking_untrained.csv").groupby("statistic").rho.mean()["RMS/v^0.5"]
    a.axvline(rk, color=INK2, lw=0.8, ls="--", label="untrained RMS/v$^{0.5}$")
    a.set_xlim(0.7, 0.9); a.set_xlabel("within-route Spearman $\\rho$")
    a.set_yticks(y); a.set_yticklabels([VLAB[v] for v in rows]); a.set_title("(a) ranking within routes", loc="left")
    # (b) zero-shot bias by road class
    b = ax[1]
    for yi, v in zip(y, rows):
        b.plot([S.loc[v, "bias_urban"], S.loc[v, "bias_motorway"]], [yi, yi], color=GRID, lw=1.5, zorder=1)
        b.plot(S.loc[v, "bias_urban"], yi, "s", color=PALETTE[6], ms=3.5, zorder=2, label="urban" if yi == y[0] else None)
        b.plot(S.loc[v, "bias_motorway"], yi, "D", color=PALETTE[3], ms=3.5, zorder=2, label="motorway" if yi == y[0] else None)
    b.axvline(0, color=INK2, lw=0.7, ls=":")
    b.set_xlabel("zero-shot bias (m/km)"); b.set_title("(b) level", loc="left")
    # (c) MAE: zero-shot -> + intercept from 5 km of real data
    c = ax[2]
    c.axvline(real_all, color=C_REAL, lw=1.0, label="real cars, all training routes")
    c.axvline(real_k5, color=C_REAL, lw=1.0, ls="--", label="real cars, 5 km")
    for yi, v in zip(y, rows):
        if v == "REAL":
            continue
        z, k5 = S.loc[v, "mae"], S.loc[v, "intercept_k5_mean"]
        lo, hi = S.loc[v, "intercept_k5_lo"], S.loc[v, "intercept_k5_hi"]
        c.plot([z, k5], [yi, yi], color=GRID, lw=1.5, zorder=1)
        c.plot(z, yi, "o", mfc="white", mec=C_SIM, ms=4.5, zorder=3, label="simulation only (zero-shot)" if yi == y[0] else None)
        c.errorbar(k5, yi, xerr=[[k5 - lo], [hi - k5]], fmt="o", color=C_CAL, ms=4, capsize=1.5, lw=0.8, zorder=2,
                   label="+ level from 5 km real" if yi == y[0] else None)
    c.set_xlabel("segment MAE (m/km)"); c.set_title("(c) error before / after level calibration", loc="left")
    h0, l0 = a.get_legend_handles_labels(); h1, l1 = b.get_legend_handles_labels(); h2, l2 = c.get_legend_handles_labels()
    fig.legend(h0 + h1 + h2, l0 + l1 + l2, loc="lower center", ncol=7, fontsize=6.0, columnspacing=1.0, handletextpad=0.4)
    fig.tight_layout(rect=[0, 0.07, 1, 1]); PL.savefig(fig, os.path.join(FIGURES, "v2_variants"))


def fig_spectra():
    R = rd("spectra_log10_diff.csv")
    S = rd("summary_variants.csv"); S = S[S.model == "GBM"].set_index("vid")
    G = rd("band_gain.csv")
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 2.6), gridspec_kw=dict(width_ratios=[1.5, 1]))
    a = ax[0]
    series = [("real-V1", "V1 telematics-like, rigid", PALETTE[6]), ("real-V7", "V7 telematics-like, holder", PALETTE[4]),
              ("real-V8", "V8 phone-like, rigid", PALETTE[3]), ("real-V2", "V2 phone-like, holder", PALETTE[5]),
              ("real-V3", "V3 ideal sensor", INK2)]
    for comp, lab, col in series:
        g = R[R.comparison == comp].sort_values("freq_hz")
        a.plot(g.freq_hz, g.log10_diff, color=col, lw=1.2, label=lab, ls="--" if comp == "real-V3" else "-")
        a.fill_between(g.freq_hz, g.lo, g.hi, color=col, alpha=0.15, lw=0)
    a.axhline(0, color=INK2, lw=0.7, ls=":")
    a.set_xlabel("frequency (Hz)"); a.set_ylabel("log$_{10}$ PSD real $-$ simulated")
    a.set_title("(a) where the simulated vibration differs (same segments and speeds)", loc="left")
    a.legend(loc="upper left", fontsize=6.3, ncol=1)
    b = ax[1]
    g = G[G.feature == "log_band_10_15"].set_index("vid")
    vids = [v for v in ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"] if v in g.index]
    x = np.log10(g.loc[vids, "ratio"]); yb = S.loc[vids, "bias"]
    b.plot(x, yb, "o", color=C_SIM, ms=4)
    for v, xi, yi in zip(vids, x, yb):
        b.annotate(v, (xi, yi), xytext=(3, 2), textcoords="offset points", fontsize=6.5, color=INK2)
    from scipy.stats import spearmanr
    rho = spearmanr(x, yb)[0]
    b.text(0.04, 0.95, f"Spearman {rho:.2f} (9 variants)", transform=b.transAxes, va="top", fontsize=7, color=INK2)
    b.axhline(0, color=INK2, lw=0.7, ls=":")
    b.set_xlabel("log$_{10}$ real/sim amplitude, 10-15 Hz"); b.set_ylabel("zero-shot bias (m/km)")
    b.set_title("(b) level error tracks the 10-15 Hz deficit", loc="left")
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "v2_spectra"))


def fig_value():
    """(a) equal profile budget: real drives vs simulated drives over the same k km (all nine measured-profile variants);
    (b) simulation on all training-route profiles + level offset from k km of real passes vs real-only training."""
    V = rd("summary_value_of_sim.csv")
    P = rd("paired_vs_real.csv")
    meas = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 2.7), sharey=True)
    for a, arm, ks, title, lab in ((ax[0], "sim_same", [1, 2, 5, 10, 20, 40], "(a) equal profile budget",
                                    "simulation on the same k km of profiles"),
                                   (ax[1], "sim_all_cal", [1, 2, 5, 10, 20], "(b) k km of paired drives used only for the level",
                                    "simulation on all profiles + level from the k km")):
        g = V[(V.arm == "real_only") & V.k_km.isin(ks)].sort_values("k_km")
        a.fill_between(g.k_km, g.lo, g.hi, color=C_REAL, alpha=0.12, lw=0)
        a.plot(g.k_km, g["mean"], marker="o", color=C_REAL, label="real cars on the k km, LightGBM (2.5-97.5 % of draws)", zorder=4)
        ri = P[(P.vid == "V0") & (P.arm == "sim_same") & P.k_km.isin(ks)].sort_values("k_km")
        a.plot(ri.k_km, ri.real_idx_mae, marker="s", ms=3, color=C_REAL, ls="--", lw=1.0,
               label="real cars on the k km, vibration index", zorder=4)
        col = C_SIM if arm == "sim_same" else C_CAL
        for v in meas:
            q = P[(P.vid == v) & (P.arm == arm) & P.k_km.isin(ks)].sort_values("k_km")
            if v == "V0":
                a.plot(q.k_km, q.mae, marker="o", color=col, lw=1.6, zorder=5, label=lab + ", V0")
            else:
                a.plot(q.k_km, q.mae, color=col, lw=0.7, alpha=0.55, zorder=3,
                       label=lab + ", V1-V8" if v == "V1" else None)
        a.set_xscale("log"); a.set_xticks(ks); a.set_xticklabels([str(k) for k in ks]); a.minorticks_off()
        a.set_xlabel("profiled road with paired drives, k (km)")
        a.set_ylim(0.35, 1.9); a.set_title(title, loc="left"); a.legend(fontsize=6.0, loc="upper right")
    ax[0].set_ylabel("segment MAE (m/km)")
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "v2_value"))


def fig_speed():
    T = rd("speed_real.csv")
    items = [("RAW_RMS", "raw vibration RMS (car physics)", INK2), ("REAL_SPEED", "speed only", C_REAL),
             ("REAL_INDEX", "vibration index, real", C_REAL), ("REAL_GBM", "LightGBM, real", C_REAL),
             ("REAL_MLP", "MLP, real", C_REAL), ("REAL_CNN", "1D-CNN, real", C_REAL),
             ("SIM_V0_INDEX", "vibration index, sim. V0", C_SIM), ("SIM_V0_GBM", "LightGBM, sim. V0", C_SIM),
             ("SIM_V10_GBM", "LightGBM, sim. V10", C_SIM), ("SIM_V2_GBM", "LightGBM, sim. V2", C_SIM),
             ("SIM_V1_GBM", "LightGBM, sim. V1", C_SIM)]
    fig, ax = plt.subplots(figsize=(COL_W, 3.1))
    y = np.arange(len(items))[::-1]
    ax.axvspan(-0.104, 0.104, color=GRID, alpha=0.6, lw=0)
    for yi, (m, lab, col) in zip(y, items):
        for sc, mk, dy in (("urban", "s", 0.17), ("motorway", "D", -0.17)):
            q = T[(T.model == m) & (T.scope == sc)].iloc[0]
            ax.errorbar(q.within_elasticity, yi + dy, xerr=[[q.within_elasticity - q.within_lo], [q.within_hi - q.within_elasticity]],
                        fmt=mk, color=col, ms=3, capsize=1, lw=0.7, mfc=col if sc == "urban" else "white")
    ax.axvline(0, color=INK2, lw=0.6, ls=":")
    ax.set_yticks(y); ax.set_yticklabels([i[1] for i in items], fontsize=6.5)
    ax.set_xlabel("speed elasticity on a fixed road")
    ax.plot([], [], "s", color=INK2, ms=3, label="urban"); ax.plot([], [], "D", color=INK2, mfc="white", ms=3, label="motorway")
    ax.legend(loc="lower right", fontsize=6.3)
    ax.text(0, len(items) - 0.35, "$\\pm$10 % over 40-100 km/h", ha="center", fontsize=6, color=INK2)
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "v2_speed"))


def fig_vehicles():
    R = rd("vehicle_sweep.csv"); R = R[R.model == "GBM"].sort_values("N")
    fig, ax = plt.subplots(1, 2, figsize=(COL_W, 1.9))
    a = ax[0]
    a.plot(R.N, R.mae_seen, "o-", color=C_REAL, label="seen vehicles")
    a.plot(R.N, R.mae_unseen, "o-", color=C_SIM, label="unseen vehicles")
    a.set_xscale("log"); a.set_xlabel("training vehicles N"); a.set_ylabel("MAE (m/km)"); a.legend(fontsize=6)
    b = ax[1]
    b.errorbar(R.N, 100 * R.rel, yerr=[100 * (R.rel - R["lo"] / R.mae_seen), 100 * (R.rel_hi - R.rel)], fmt="o-", color=C_SIM,
               capsize=1.5, lw=0.9, ms=3, label="95 % CI (segments)")
    b.plot(R.N, 100 * R.rel_hi_route_boot, "_", color=INK2, ms=8, mew=1.2, label="upper bound (routes)")
    b.axhline(10, color=INK2, lw=0.7, ls="--", label="criterion 10 %")
    b.set_xscale("log"); b.set_xlabel("training vehicles N"); b.set_ylabel("unseen vs seen (%)")
    b.set_ylim(0, 105)
    b.legend(fontsize=5.6, loc="upper right", frameon=False, handlelength=1.4)
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "v2_vehicles"))


def fig_supp_scatter():
    """Supplement: predicted vs true IRI (segment level) for the real-trained model and three simulator variants."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments", "v2"))
    from common_v2 import load_lira, seg_table, v1_pass_predictions
    U, _ = load_lira()
    P = pd.read_csv(os.path.join(V2, "variants_pass_predictions.csv.gz"))
    panels = [("trained on real cars", v1_pass_predictions(U, "lira_ladder.csv", "M3 LightGBM (all features)"), C_REAL)]
    for vid in ("V0", "V1", "V2"):
        d = P[(P.vid == vid) & (P.model == "GBM")]
        p = np.full(len(U), np.nan); p[d.unit.to_numpy()] = d.pred.to_numpy()
        panels.append((VLAB[vid], p, C_SIM))
    fig, ax = plt.subplots(1, 4, figsize=(DBL_W, 2.0), sharex=True, sharey=True)
    for a, (lab, p, col) in zip(ax, panels):
        idx = np.where(np.isfinite(p))[0]
        S = seg_table(U, idx, p[idx])
        a.loglog([0.4, 12], [0.4, 12], color=INK2, lw=0.6, ls="--")
        for cls, mk in (("urban", "o"), ("motorway", "^")):
            q = S[S.cls == cls]
            a.scatter(q.y, q.p, s=3, color=col, alpha=0.4, marker=mk, lw=0)
        a.set_title(lab, fontsize=7, loc="left"); a.set_xlabel("P79 IRI (m/km)")
    ax[0].set_ylabel("predicted IRI (m/km)")
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "v2s_scatter"))


def fig_supp_acf_transmissibility():
    A = rd("residual_acf.csv"); T = rd("physics_transmissibility.csv")
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 2.3))
    a = ax[0]
    for m, lab, col in (("REAL_GBM", "LightGBM, real", C_REAL), ("SIM_P79", "LightGBM, sim. V0", C_SIM), ("INDEX", "vibration index, real", PALETTE[3])):
        g = A[A.model == m]
        a.plot(g.lag_m / 1000, g.r, "o-", color=col, label=lab)
    a.axhline(0, color=INK2, lw=0.6, ls=":"); a.set_xlabel("lag (km)"); a.set_ylabel("residual autocorrelation"); a.legend(fontsize=6.3)
    a.set_title("(a) spatial dependence of segment errors", loc="left")
    b = ax[1]
    for i, (fold, g) in enumerate(T.groupby("fold")):
        b.plot(g.freq_hz, g.log_T_empirical / np.log(10), color=C_REAL, lw=1.0, alpha=0.6, label="empirical (training routes)" if i == 0 else None)
        b.plot(g.freq_hz, g.log_T_quartercar / np.log(10), color=C_SIM, lw=1.0, ls="--", alpha=0.8, label="fitted quarter car" if i == 0 else None)
    b.set_xlabel("frequency (Hz)"); b.set_ylabel("log$_{10}$ |a / road|$^2$"); b.legend(fontsize=6.3)
    b.set_title("(b) real-car transmissibility (M7 calibration)", loc="left")
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "v2s_acf_transmissibility"))


def main():
    os.makedirs(FIGURES, exist_ok=True)
    for f in (fig_variants, fig_spectra, fig_value, fig_speed, fig_vehicles, fig_supp_scatter, fig_supp_acf_transmissibility):
        f(); print(f.__name__, flush=True)


if __name__ == "__main__":
    main()
