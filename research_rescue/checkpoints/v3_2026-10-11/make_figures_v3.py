"""Revision v3 figures (from results/v2/*.csv and results/v3/*.csv). Colour = concept, fixed across figures:
real-trained = blue (palette slot 0), simulation-trained = orange (1), simulation + level offset = green (2),
joint simulation + real training = pink (4). Outputs: figures/v3_*.pdf/png. The v2 figures are left unchanged.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import plotting as PL  # noqa: E402
from common.plotting import plt, PALETTE, INK2, GRID, DBL_W  # noqa: E402
from common.paths import RESULTS, FIGURES  # noqa: E402
from make_figures_v2 import VLAB, ORDER  # noqa: E402

V2, V3 = os.path.join(RESULTS, "v2"), os.path.join(RESULTS, "v3")
C_REAL, C_SIM, C_CAL, C_POOL = PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[4]
MEAS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]


def r2(name):
    return pd.read_csv(os.path.join(V2, name))


def r3(name):
    return pd.read_csv(os.path.join(V3, name))


def fig_variants():
    """(a) within-route ranking, (b) zero-shot log level by road class, (c) pooled MAE zero-shot, after a 5 km level
    offset and with joint training on the same 5 km."""
    S = r2("summary_variants.csv"); S = S[S.model == "GBM"].set_index("vid")
    L = r3("level_decomposition.csv").set_index("vid")
    PS = r3("pooled_summary.csv").set_index(["vid", "k_km"])
    vs = r2("summary_value_of_sim.csv").set_index(["arm", "k_km"])
    real_k5 = vs.loc[("real_only", 5), "mean"]; real_all = S.loc["REAL", "mae"]
    rows = [v for v in ORDER if v in S.index]
    y = np.arange(len(rows))[::-1]
    fig, ax = plt.subplots(1, 3, figsize=(DBL_W, 3.1), sharey=True, gridspec_kw=dict(width_ratios=[1, 1, 1.5]))
    a = ax[0]
    for yi, v in zip(y, rows):
        a.plot(S.loc[v, "rho_within_mean"], yi, "o", color=C_REAL if v == "REAL" else C_SIM, ms=4)
    rk = r2("ranking_untrained.csv").groupby("statistic").rho.mean()["RMS/v^0.5"]
    a.axvline(rk, color=INK2, lw=0.8, ls="--", label="untrained RMS/v$^{0.5}$")
    a.set_xlim(0.7, 0.9); a.set_xlabel("within-route Spearman $\\rho$")
    a.set_yticks(y); a.set_yticklabels([VLAB[v] for v in rows]); a.set_title("(a) ranking within routes", loc="left")
    b = ax[1]
    for yi, v in zip(y, rows):
        b.plot([L.loc[v, "lvl_urban"], L.loc[v, "lvl_motorway"]], [yi, yi], color=GRID, lw=1.5, zorder=1)
        b.plot(L.loc[v, "lvl_urban"], yi, "s", color=PALETTE[6], ms=3.5, zorder=2, label="urban" if yi == y[0] else None)
        b.plot(L.loc[v, "lvl_motorway"], yi, "D", color=PALETTE[3], ms=3.5, zorder=2, label="motorway" if yi == y[0] else None)
    b.axvline(0, color=INK2, lw=0.7, ls=":")
    b.set_xlabel("zero-shot level (mean log ratio)"); b.set_title("(b) level", loc="left")
    c = ax[2]
    c.axvline(real_all, color=C_REAL, lw=1.0, label="real cars, all training routes")
    c.axvline(real_k5, color=C_REAL, lw=1.0, ls="--", label="real cars, 5 km")
    for yi, v in zip(y, rows):
        if v == "REAL":
            continue
        z, k5 = S.loc[v, "mae"], S.loc[v, "intercept_k5_mean"]
        c.plot([z, k5], [yi, yi], color=GRID, lw=1.5, zorder=1)
        c.plot(z, yi, "o", mfc="white", mec=C_SIM, ms=4.5, zorder=3, label="simulation only (zero-shot)" if yi == y[0] else None)
        c.plot(k5, yi, "o", color=C_CAL, ms=4, zorder=4, label="+ level offset from 5 km" if yi == y[0] else None)
        if (v, 5) in PS.index:
            c.plot(PS.loc[(v, 5), "mae"], yi + 0.22, "^", color=C_POOL, ms=4, zorder=4,
                   label="joint training with 5 km" if yi == y[0] else None)
    c.set_xlabel("pooled segment MAE (m/km)"); c.set_title("(c) error zero-shot and with 5 km of paired drives", loc="left")
    h0, l0 = a.get_legend_handles_labels(); h1, l1 = b.get_legend_handles_labels(); h2, l2 = c.get_legend_handles_labels()
    # column-major legend: (b) urban, motorway | (a) untrained, (c) real all | real 5 km, zero-shot | offset, joint
    fig.legend(h1 + h0 + h2, l1 + l0 + l2, loc="lower center", ncol=4, fontsize=6.0, columnspacing=1.0, handletextpad=0.4)
    fig.tight_layout(rect=[0, 0.12, 1, 1]); PL.savefig(fig, os.path.join(FIGURES, "v3_variants"))


def fig_spectra():
    """(a) same-segment spectral differences; (b) zero-shot bias vs the 10-15 Hz ratio, every band's association
    printed; (c) band-limited retraining."""
    R = r2("spectra_log10_diff.csv")
    S = r2("summary_variants.csv"); S = S[S.model == "GBM"].set_index("vid")
    G = r2("band_gain.csv")
    BA = r3("band_associations.csv"); BL = r3("band_limited.csv")
    fig, ax = plt.subplots(1, 3, figsize=(DBL_W, 2.55), gridspec_kw=dict(width_ratios=[1.45, 1, 1]))
    a = ax[0]
    series = [("real-V1", "V1 telematics-like, rigid", PALETTE[6]), ("real-V7", "V7 telematics-like, holder", PALETTE[4]),
              ("real-V8", "V8 phone-like, rigid", PALETTE[3]), ("real-V2", "V2 phone-like, holder", PALETTE[5]),
              ("real-V3", "V3 ideal sensor", INK2)]
    for comp, lab, col in series:
        g = R[R.comparison == comp].sort_values("freq_hz")
        a.plot(g.freq_hz, g.log10_diff, color=col, lw=1.1, label=lab, ls="--" if comp == "real-V3" else "-")
        a.fill_between(g.freq_hz, g.lo, g.hi, color=col, alpha=0.15, lw=0)
    a.axhline(0, color=INK2, lw=0.7, ls=":")
    a.set_xlabel("frequency (Hz)"); a.set_ylabel("log$_{10}$ PSD real $-$ simulated")
    a.set_title("(a) same segments and speeds", loc="left")
    a.legend(loc="upper left", fontsize=5.6, ncol=1, frameon=False)
    b = ax[1]
    g = G[G.feature == "log_band_10_15"].set_index("vid")
    x = np.log10(g.loc[MEAS, "ratio"]); yb = S.loc[MEAS, "bias"]
    for v, xi, yi in zip(MEAS, x, yb):
        b.plot(xi, yi, "D" if v == "V4" else "o", color=PALETTE[3] if v == "V4" else C_SIM, ms=4.5 if v == "V4" else 4)
    off = {"V0": (4, -3), "V1": (3, 4), "V3": (-14, -9), "V5": (-14, 4), "V2": (4, 2), "V4": (-14, 3), "V6": (4, -7),
           "V7": (4, 2), "V8": (4, -2)}
    for v, xi, yi in zip(MEAS, x, yb):
        b.annotate(v, (xi, yi), xytext=off[v], textcoords="offset points", fontsize=6, color=INK2)
    lab = {"log_band_0.5_2": "0.5-2 Hz", "log_band_2_5": "2-5 Hz", "log_band_5_10": "5-10 Hz",
           "log_band_10_15": "10-15 Hz", "log_rms": "overall RMS"}
    q = BA[BA.target == "bias"].set_index("feature")
    txt = "Spearman with bias\n" + "\n".join(f"{lab[f]}: {q.loc[f, 'spearman']:.2f}" for f in
                                             ["log_band_10_15", "log_rms", "log_band_5_10", "log_band_2_5", "log_band_0.5_2"])
    b.text(0.04, 0.80, txt, transform=b.transAxes, va="top", ha="left", fontsize=5.6, color=INK2)
    b.axhline(0, color=INK2, lw=0.7, ls=":")
    b.set_xlabel("log$_{10}$ real/sim amplitude, 10-15 Hz"); b.set_ylabel("zero-shot bias (m/km)")
    b.set_title("(b) level vs 10-15 Hz deficit", loc="left")
    c = ax[2]
    order = ["V0", "V1", "V7", "V8", "V2", "V3", "V5", "V6", "V4"]
    yy = np.arange(len(order))[::-1]
    full = BL[BL.features == "full"].set_index("vid"); low = BL[BL.features == "lt10"].set_index("vid")
    for yi, v in zip(yy, order):
        col = PALETTE[3] if v == "V4" else C_SIM
        c.plot([full.loc[v, "lvl_mean"], low.loc[v, "lvl_mean"]], [yi, yi], color=GRID, lw=1.4, zorder=1)
        c.plot(full.loc[v, "lvl_mean"], yi, "o", mfc="white", mec=col, ms=4, zorder=3)
        c.plot(low.loc[v, "lvl_mean"], yi, "o", color=col, ms=4, zorder=3)
    yv1 = yy[order.index("V1")]
    c.annotate("all features", (full.loc["V1", "lvl_mean"], yv1), xytext=(0, 5), textcoords="offset points",
               ha="center", fontsize=5.6, color=INK2)
    c.annotate("below 10 Hz", (low.loc["V1", "lvl_mean"], yv1), xytext=(0, 5), textcoords="offset points",
               ha="left", fontsize=5.6, color=INK2)
    c.axvline(0, color=INK2, lw=0.7, ls=":")
    c.set_xlim(-0.02, 0.33)
    c.set_yticks(yy); c.set_yticklabels(order, fontsize=6.5)
    c.set_xlabel("zero-shot level (mean log ratio)"); c.set_title("(c) band-limited retraining", loc="left")
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "v3_spectra"))


def fig_value():
    """(a) equal profile budget; (b) all training-route profiles + k km of paired drives: level offset vs joint
    training, every measured-profile variant, against both real-only comparators."""
    V = r2("summary_value_of_sim.csv")
    P = r2("paired_vs_real.csv")
    PS = r3("pooled_summary.csv")
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 2.9))
    ylims = {0: (0.35, 1.9), 1: (0.38, 0.80)}       # (b) zoomed on the combinations; off-scale values are printed
    for a, ks, title in ((ax[0], [1, 2, 5, 10, 20, 40], "(a) equal profile budget"),
                         (ax[1], [1, 2, 5, 10, 20], "(b) all profiles + $k$ km of paired drives")):
        g = V[(V.arm == "real_only") & V.k_km.isin(ks)].sort_values("k_km")
        a.fill_between(g.k_km, g.lo, g.hi, color=C_REAL, alpha=0.12, lw=0)
        a.plot(g.k_km, g["mean"], marker="o", color=C_REAL, label="real cars, LightGBM (2.5-97.5 % of draws)", zorder=4)
        ri = P[(P.vid == "V0") & (P.arm == "sim_same") & P.k_km.isin(ks)].sort_values("k_km")
        a.plot(ri.k_km, ri.real_idx_mae, marker="s", ms=3, color=C_REAL, ls="--", lw=1.0, label="real cars, vibration index", zorder=4)
        arms = ([("sim_same", C_SIM, "simulation on the same $k$ km of profiles")] if a is ax[0] else
                [("sim_all_cal", C_CAL, "level offset"), ("pooled", C_POOL, "joint training")])
        for arm, col, lab in arms:
            for v in MEAS:
                if arm == "pooled":
                    q = PS[(PS.vid == v) & PS.k_km.isin(ks)].sort_values("k_km"); yv = q.mae
                else:
                    q = P[(P.vid == v) & (P.arm == arm) & P.k_km.isin(ks)].sort_values("k_km"); yv = q.mae
                if v == "V0":
                    a.plot(q.k_km, yv, marker="o", ms=3.5, color=col, lw=1.6, zorder=5, label=lab + ", V0")
                else:
                    a.plot(q.k_km, yv, color=col, lw=0.7, alpha=0.6, zorder=3, label=lab + ", V1-V8" if v == "V1" else None)
        a.set_xscale("log"); a.set_xticks(ks); a.set_xticklabels([str(k) for k in ks]); a.minorticks_off()
        a.set_xlabel("profiled road with paired drives, $k$ (km)")
        lo_, hi_ = ylims[0 if a is ax[0] else 1]
        a.set_ylim(lo_, hi_); a.set_title(title, loc="left"); a.set_ylabel("pooled segment MAE (m/km)")
        if a is ax[1]:      # the off-scale real-only values (1 and 2 km) are given in the caption (macros)
            off = sorted(set(int(r.k_km) for _, r in g.iterrows() if r["mean"] > hi_)
                         | set(int(r.k_km) for _, r in ri.iterrows() if r.real_idx_mae > hi_))
            assert off == [1, 2], f"caption of fig:value assumes off-scale real-only values at 1 and 2 km only, got {off}"
    # one legend for both panels, below them (de-duplicated, in drawing order)
    hs, ls_ = [], []
    for a in ax:
        for h, l in zip(*a.get_legend_handles_labels()):
            if l not in ls_:
                hs.append(h); ls_.append(l)
    fig.legend(hs, ls_, loc="lower center", ncol=4, fontsize=6.0, columnspacing=1.0, handletextpad=0.4, frameon=False)
    fig.tight_layout(rect=[0, 0.16, 1, 1]); PL.savefig(fig, os.path.join(FIGURES, "v3_value"))


def main():
    fig_variants(); fig_spectra(); fig_value()
    print("written:", sorted(f for f in os.listdir(FIGURES) if f.startswith("v3_")))


if __name__ == "__main__":
    PL.set_style()
    main()
