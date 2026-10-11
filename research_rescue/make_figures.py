"""Generate all paper figures from result files (no numbers typed by hand). Figures whose inputs are missing are
skipped with a message. Usage: python make_figures.py"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import plotting as PL  # noqa: E402
from common.plotting import plt, PALETTE, INK, INK2, COL_W, DBL_W  # noqa: E402
from common.features import FEATURE_NAMES  # noqa: E402
from common.paths import RESULTS, FIGURES, PROCESSED  # noqa: E402

FI = {n: i for i, n in enumerate(FEATURE_NAMES)}


def need(*paths):
    miss = [p for p in paths if not os.path.exists(p)]
    if miss:
        print("  skip (missing):", ", ".join(os.path.relpath(m, RESULTS) for m in miss))
    return not miss


def speed_exponent(lr, liri, lv, seg, B=1000, seed=0):
    """gamma in log RMS = a + beta log IRI + gamma log v (vibration speed exponent at fixed roughness);
    cluster bootstrap over segments."""
    X = np.column_stack([np.ones(len(lr)), liri, lv])
    g = np.linalg.lstsq(X, lr, rcond=None)[0][2]
    u, inv = np.unique(seg, return_inverse=True)
    mem = [np.where(inv == k)[0] for k in range(len(u))]
    rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        idx = np.concatenate([mem[k] for k in rng.integers(0, len(u), len(u))])
        bs.append(np.linalg.lstsq(X[idx], lr[idx], rcond=None)[0][2])
    return float(g), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def fig_sim_vs_real():
    """Fig. 3: (a) simulated vs measured vibration on identical road segments; (b) speed exponent per domain."""
    gp = os.path.join(RESULTS, "lira", "gap_segment_logrms.csv")
    if not need(gp, os.path.join(PROCESSED, "lira", "units.csv")):
        return
    j = pd.read_csv(gp)
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 2.5), gridspec_kw=dict(width_ratios=[1, 1.25]))
    a = ax[0]
    a.scatter(j.sim, j.real, s=4, color=PALETTE[0], alpha=0.5, linewidths=0)
    lo, hi = np.nanmin([j.sim.min(), j.real.min()]), np.nanmax([j.sim.max(), j.real.max()])
    a.plot([lo, hi], [lo, hi], color=INK2, lw=0.7, ls="--")
    from scipy.stats import spearmanr
    PL.stat_text(a, [f"n = {len(j)} segments", f"Spearman = {spearmanr(j.sim, j.real)[0]:.2f}",
                     f"mean real - sim = {np.mean(j.real - j.sim):+.2f} (log)"])
    a.set_xlabel("simulated log RMS $a_z$ (60-100 km/h)"); a.set_ylabel("measured log RMS $a_z$ (LiRA-CD)")
    a.set_title("(a) Same road segments: simulation vs. real cars", loc="left")
    # (b) speed exponent gamma per domain
    rows = []
    U = pd.read_csv(os.path.join(PROCESSED, "lira", "units.csv")); A = np.load(os.path.join(PROCESSED, "lira", "arrays.npz"))
    for cls, m in [("LiRA motorway", U.route.str.startswith("M").to_numpy()), ("LiRA urban", U.route.str.startswith("CPH").to_numpy())]:
        rows.append((cls,) + speed_exponent(A["feat"][m, FI["log_rms"]], np.log(U.mri.to_numpy()[m]), A["feat"][m, FI["log_v_mean"]], U.segment.to_numpy()[m]))
    sp = os.path.join(PROCESSED, "sim", "p79_train_meta.csv")
    if os.path.exists(sp):
        Sm = pd.read_csv(sp); SA = np.load(os.path.join(PROCESSED, "sim", "p79_train_arrays.npz"))
        rows.append(("Simulator (P79 profiles)",) + speed_exponent(SA["feat"][:, FI["log_rms"]], np.log(Sm.mri.to_numpy()), SA["feat"][:, FI["log_v_mean"]], Sm.segment.to_numpy()))
    bp = os.path.join(PROCESSED, "beamng", "meta.csv")
    if os.path.exists(bp):
        Bm = pd.read_csv(bp); BA = np.load(os.path.join(PROCESSED, "beamng", "arrays.npz"))
        for lab, nm in [("iri_raw", "BeamNG, raw-profile label"), ("iri_corr", "BeamNG, legacy label")]:
            ok = Bm[lab].notna().to_numpy() & (Bm[lab].to_numpy() > 0)
            rows.append((nm,) + speed_exponent(BA["feat"][ok, FI["log_rms"]], np.log(Bm[lab].to_numpy()[ok]), BA["feat"][ok, FI["log_v_mean"]], Bm.cluster.to_numpy()[ok]))
    b = ax[1]
    for i, (nm, g, l, h) in enumerate(rows):
        b.errorbar(g, i, xerr=[[g - l], [h - g]], fmt="o", color=PALETTE[0], ms=4, capsize=2, lw=1)
        b.text(h + 0.04, i, f"{g:.2f}", va="center", fontsize=7, color=INK2)
    for x, lab in [(0.5, "0.5: random road\n(white velocity input)"), (2.0, "2: legacy\n" + r"$(v_{ref}/v)^2$")]:
        b.axvline(x, color=INK2, lw=0.7, ls=":")
        b.text(x, -0.95, lab, fontsize=6, color=INK2, ha="center", va="top")
    b.set_yticks(range(len(rows))); b.set_yticklabels([r[0] for r in rows])
    b.set_xlabel(r"speed exponent $\gamma$:  RMS $a_z \propto$ IRI$^{\beta} v^{\gamma}$  (95% CI)")
    b.set_title("(b) How vibration scales with speed at fixed roughness", loc="left")
    b.set_xlim(-0.55, 2.35); b.set_ylim(len(rows) - 0.5, -1.25)
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "sim_vs_real"))
    pd.DataFrame(rows, columns=["domain", "gamma", "lo", "hi"]).to_csv(os.path.join(RESULTS, "speed_exponent_by_domain.csv"), index=False)


def fig_speed_shortcut():
    """Fig. 4: (a) PVS ordinal labels: what speed alone achieves; (b) controlled speed sweep."""
    pv = os.path.join(RESULTS, "pvs", "pvs_auc.csv"); sw = os.path.join(RESULTS, "sim", "speed_invariance_curves.csv")
    if not need(pv, sw):
        return
    P = pd.read_csv(pv); C = pd.read_csv(sw)
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 2.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
    a = ax[0]
    order = ["speed", "RMS", "RMS/sqrt(v)", "model", "speed+RMS", "model+speed+RMS"]
    labels = {"speed": "speed only", "RMS": "RMS $a_z$", "RMS/sqrt(v)": r"RMS/$\sqrt{v}$", "model": "legacy model",
              "speed+RMS": "speed + RMS", "model+speed+RMS": "model + speed + RMS"}
    tasks = [("A: asphalt vs cobblestone+dirt", "surface type", PALETTE[0], -0.18), ("C: bad vs regular (cobblestone+dirt only)", "bad vs regular (rough roads)", PALETTE[1], 0.18)]
    for tname, tl, col, off in tasks:
        d = P[P.task == tname].set_index("predictors").loc[order]
        y = np.arange(len(order)) + off
        a.errorbar(d.auc, y, xerr=[d.auc - d.auc_lo, d.auc_hi - d.auc], fmt="o", ms=3.5, color=col, capsize=2, lw=1, label=tl)
    a.axvline(0.5, color=INK2, lw=0.7, ls=":")
    a.set_yticks(range(len(order))); a.set_yticklabels([labels[o] for o in order]); a.invert_yaxis()
    a.set_xlabel("AUC, leave-one-route-out (95% CI)"); a.set_xlim(0.0, 1.02)
    a.legend(loc="lower left", fontsize=6.5); a.set_title("(a) PVS: which predictor separates the labels", loc="left")
    b = ax[1]
    show = [("M2c RMS/v^alpha (alpha fitted)", r"RMS/$v^{\alpha}$, $\alpha$ fitted", PALETTE[0]),
            ("M3 LightGBM", "LightGBM (with speed)", PALETTE[1]),
            ("M2d legacy exponent 2", r"legacy $(v_{ref}/v)^2$", PALETTE[2])]
    for k, lab, col in show:
        for sweep, ls, suffix in [("sweep_iso", "-", "held-out synthetic roads"), ("sweep_p79", "--", "measured P79 profiles")]:
            e = C[(C.sweep == sweep) & (C.model == k)].sort_values("speed_kmh")
            if len(e) == 0:
                continue
            b.plot(e.speed_kmh, e.mean_ratio_to_60, ls=ls, marker="o", ms=2.5, color=col, lw=1.1)
            b.fill_between(e.speed_kmh, e.lo, e.hi, color=col, alpha=0.12, lw=0)
    b.axhspan(0.9, 1.1, color=INK2, alpha=0.08, lw=0)
    b.text(112, 1.0, r"$\pm$10%", fontsize=6, color=INK2, va="center")
    b.axhline(1.0, color=INK2, lw=0.6)
    b.set_xlabel("constant speed (km/h)"); b.set_ylabel("prediction / prediction at 60 km/h")
    b.set_yscale("log"); b.set_yticks([0.5, 0.7, 1.0, 1.4, 2.0]); b.set_yticklabels(["0.5", "0.7", "1.0", "1.4", "2.0"])
    b.minorticks_off(); b.set_xlim(15, 122)
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=c, lw=1.2, label=l) for _, l, c in show] +               [Line2D([0], [0], color=INK2, lw=1.1, ls="-", label="held-out synthetic roads"),
               Line2D([0], [0], color=INK2, lw=1.1, ls="--", label="measured P79 profiles")]
    b.legend(handles=handles, fontsize=6, loc="upper right")
    b.set_title("(b) Same road, different speeds (simulator)", loc="left")
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "speed_shortcut"))


def fig_lira_main():
    """Fig. 5: LiRA-CD real-car results (segment level, leave-one-route-out)."""
    lp = os.path.join(RESULTS, "lira", "ladder_segment_metrics.csv"); zp = os.path.join(RESULTS, "lira", "zeroshot_segment_metrics.csv")
    pr = os.path.join(RESULTS, "lira", "ladder_per_route.csv")
    if not need(lp, pr):
        return
    L = pd.read_csv(lp)
    short = {"M0 constant (training median)": "M0 constant", "M1 speed-only (LightGBM on speed features)": "M1 speed only",
             "M2a RMS only (alpha=0)": r"M2a RMS ($\alpha$=0)", "M2b RMS/v^0.5": r"M2b RMS/$v^{0.5}$",
             "M2c RMS/v^alpha (alpha fitted on training data)": r"M2c RMS/$v^{\alpha}$, $\alpha$ fitted",
             "M2d RMS*(v_ref/v)^2 (legacy exponent, gravity removed)": r"M2d RMS$\cdot(v_{ref}/v)^2$",
             "M3 LightGBM (all features)": "M3 LightGBM", "M3 LightGBM (no speed features)": "M3 LightGBM, no speed",
             "M4 MLP": "M4 MLP", "M5 1D-CNN": "M5 1D-CNN", "M5 1D-CNN (no speed input)": "M5 1D-CNN, no speed",
             "M6 inner-validation-selected model": "M6 inner-selected (MLP)",
             "Z sim[iso] LightGBM": "LightGBM, synthetic profiles", "Z sim[p79] LightGBM": "LightGBM, measured profiles",
             "Z sim[p79+iso] LightGBM": "LightGBM, both profile sources", "Z sim[p79+iso] 1D-CNN": "1D-CNN, both profile sources",
             "Z sim[p79+iso] physics index (alpha fitted in sim)": r"RMS/$v^{\alpha}$, both profile sources",
             "Z BeamNG[iri_corr] LightGBM": "LightGBM, BeamNG corpus"}
    rows = [(short.get(r.model, r.model), r.mae, r.mae_lo, r.mae_hi, "trained on real data (other routes)") for r in L.itertuples()]
    if os.path.exists(zp):
        Z = pd.read_csv(zp)
        keep = ["Z sim[iso] LightGBM", "Z sim[p79] LightGBM", "Z sim[p79+iso] LightGBM", "Z sim[p79+iso] 1D-CNN",
                "Z sim[p79+iso] physics index (alpha fitted in sim)", "Z BeamNG[iri_corr] LightGBM"]
        Z = Z.set_index("model").loc[[k for k in keep if k in set(Z.model)]].reset_index()
        rows += [(short.get(r.model, r.model), r.mae, r.mae_lo, r.mae_hi, "trained only on simulated vehicle responses") for r in Z.itertuples()]
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 3.4), gridspec_kw=dict(width_ratios=[1.2, 1]))
    a = ax[0]
    cols = {"trained on real data (other routes)": PALETTE[0], "trained only on simulated vehicle responses": PALETTE[1]}
    for i, (m, v, l, h, grp) in enumerate(rows):
        a.errorbar(v, i, xerr=[[v - l], [h - v]], fmt="o", ms=3.5, color=cols[grp], capsize=2, lw=1,
                   label=grp if grp not in [r[4] for r in rows[:i]] else None)
    a.set_yticks(range(len(rows))); a.set_yticklabels([r[0] for r in rows], fontsize=6.3); a.invert_yaxis()
    a.set_xlabel("segment-level MAE (m/km), 95% CI"); a.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=1)
    a.set_title("(a) All four held-out routes pooled", loc="left")
    b = ax[1]
    PR = pd.read_csv(pr)
    show = [("M0 constant (training median)", "constant (reference)", "#b4b2ac"), ("M1 speed-only (LightGBM on speed features)", "speed only", PALETTE[3]),
            ("M2c RMS/v^alpha (alpha fitted on training data)", r"RMS/$v^{\alpha}$", PALETTE[1]), ("M3 LightGBM (all features)", "LightGBM", PALETTE[0]),
            ("M5 1D-CNN", "1D-CNN", PALETTE[2])]
    routes = ["CPH1", "CPH6", "M3", "M13"]
    w = 0.16
    for k, (m, lab, col) in enumerate(show):
        vals = [PR[(PR.route == r) & (PR.model == m)].mae.mean() for r in routes]
        b.bar(np.arange(4) + (k - 2) * w, vals, w * 0.92, color=col, label=lab)
    b.set_xticks(range(4)); b.set_xticklabels([f"{r}\n({'urban' if r.startswith('CPH') else 'motorway'})" for r in routes])
    b.set_ylabel("segment-level MAE (m/km)")
    b.legend(fontsize=6, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.13)); b.set_title("(b) Per held-out route", loc="left")
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "lira_main"))


def fewshot_pooled(F):
    """Segment-weighted pooled MAE over the four held-out routes for each (model, k, draw)."""
    F = F.copy(); F["w"] = F.seg_mae * F.n_seg
    per = F.groupby(["model", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum"), km=("real_km", "mean")).reset_index()
    per["mae"] = per.w / per.n
    return per


def fig_value_of_sim():
    """Fig. 6: real labelled distance vs. segment-level MAE (pooled over the four held-out routes)."""
    fp = os.path.join(RESULTS, "lira", "fewshot_raw.csv")
    if not need(fp):
        return
    per = fewshot_pooled(pd.read_csv(fp))
    summ = per.groupby(["model", "k_km"]).agg(km=("km", "mean"), mae=("mae", "mean"), med=("mae", "median"),
                                              lo=("mae", lambda x: np.percentile(x, 2.5)), hi=("mae", lambda x: np.percentile(x, 97.5))).reset_index()
    summ.to_csv(os.path.join(RESULTS, "lira", "fewshot_pooled_summary.csv"), index=False)
    fig, ax = plt.subplots(1, 2, figsize=(DBL_W, 2.7))
    panels = [(ax[0], [("real-only LightGBM", "LightGBM, real only", PALETTE[0], "-"),
                       ("sim+real LightGBM (balanced weights)", "LightGBM, simulation + real", PALETTE[1], "-"),
                       ("real-only physics index", r"RMS/$v^{\alpha}$, real only", PALETTE[0], ":"),
                       ("sim physics index + real intercept", r"RMS/$v^{\alpha}$ from sim., real intercept", PALETTE[1], ":")],
               [("sim-only LightGBM", PALETTE[1], "-"), ("sim-only physics index", PALETTE[1], ":")], "(a) LightGBM and vibration index", False),
              (ax[1], [("real-only 1D-CNN", "1D-CNN, real only", PALETTE[0], "-"),
                       ("sim-pretrained 1D-CNN + real fine-tuning", "1D-CNN, sim.-pretrained + fine-tuned", PALETTE[1], "-")],
               [("sim-only 1D-CNN", PALETTE[1], "-")], "(b) 1D-CNN (median over draws)", True)]
    for a, curves, zero, title, use_median in panels:
        for name, lab, col, ls in curves:
            d = summ[(summ.model == name) & (summ.k_km.astype(str) != "0")].sort_values("km")
            if len(d) == 0:
                continue
            yv = d.med if use_median else d.mae
            a.plot(d.km, yv, ls=ls, marker="o", ms=3, color=col, label=lab)
            if not use_median:
                a.fill_between(d.km, d.lo, d.hi, color=col, alpha=0.12, lw=0)
        zero_labels = {"sim-only LightGBM": "LightGBM, simulation only (0 km real)",
                       "sim-only physics index": r"RMS/$v^{\alpha}$, simulation only (0 km real)",
                       "sim-only 1D-CNN": "1D-CNN, simulation only (0 km real)"}
        for name, col, ls in zero:
            z = summ[summ.model == name]
            if len(z):
                a.axhline(float(z.mae.iloc[0]), color=col, ls=ls, lw=0.8, alpha=0.6, label=zero_labels[name])
        a.set_xscale("log"); a.set_xlabel("profilometer-labelled real road used for training (km)")
        a.set_xticks([1, 2, 5, 10, 20, 50, 100]); a.set_xticklabels(["1", "2", "5", "10", "20", "50", "100"]); a.minorticks_off()
        a.set_ylabel("segment-level MAE (m/km)"); a.set_title(title, loc="left"); a.legend(fontsize=5.8)
        if use_median:
            a.set_yscale("log"); a.set_yticks([0.5, 1, 2, 5, 10]); a.set_yticklabels(["0.5", "1", "2", "5", "10"]); a.minorticks_off()
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "value_of_simulation"))


RB_NAMES = {"M2c RMS/v^alpha (alpha fitted)": r"RMS/$v^{\alpha}$, $\alpha$ fitted", "M3 LightGBM": "LightGBM",
            "M3 LightGBM (no speed)": "LightGBM, no speed", "M5 1D-CNN": "1D-CNN"}


def fig_robustness():
    rp = os.path.join(RESULTS, "sim", "robustness.csv")
    if not need(rp):
        return
    Rb = pd.read_csv(rp)
    fams = list(dict.fromkeys(Rb.family))
    nice = {"sampling_rate_hz": "sampling rate", "noise_x": r"white noise ($\times$250 $\mu$g/$\sqrt{\mathrm{Hz}}$)", "quantisation_g": "quantisation step",
            "tilt_sd_deg": "mounting tilt (s.d.)", "speed_bias": "speed error", "missing_samples": "missing samples",
            "mount_resonance": "holder resonance"}
    fig, axs = plt.subplots(2, 4, figsize=(DBL_W, 3.4), sharey=True)
    models = list(dict.fromkeys(Rb.model))
    for ax, fam in zip(axs.ravel(), fams):
        d = Rb[Rb.family == fam]
        levels = list(dict.fromkeys(d.level))
        for k, m in enumerate(models):
            e = d[d.model == m].set_index("level").loc[levels]
            ax.plot(range(len(levels)), e.mae, marker="o", ms=2.5, color=PALETTE[k], label=RB_NAMES.get(m, m) if fam == fams[0] else None)
        ax.set_xticks(range(len(levels))); ax.set_xticklabels(levels, rotation=35, fontsize=6, ha="right")
        ax.set_title(nice.get(fam, fam), fontsize=7, loc="left")
    axs.ravel()[-1].axis("off")
    axs[0, 0].set_ylabel("MAE (m/km)"); axs[1, 0].set_ylabel("MAE (m/km)")
    fig.legend(loc="lower right", bbox_to_anchor=(0.99, 0.08), fontsize=6.5)
    fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "robustness"))


def fig_beamng_protocol():
    s1 = os.path.join(RESULTS, "beamng", "S1_iri_corr_metrics.csv"); s3 = os.path.join(RESULTS, "beamng", "S3_iri_corr_metrics.csv")
    l1 = os.path.join(RESULTS, "beamng", "S1_legacy_recipe_metrics.csv")
    if not need(s1, s3, l1):
        return
    S1, S3, L1 = pd.read_csv(s1), pd.read_csv(s3), pd.read_csv(l1)
    S1 = pd.concat([S1, L1])
    models = [("Legacy recipe (calibrated on val)", "legacy recipe (paper)"), ("M3 LightGBM (all features)", "LightGBM"),
              ("M2c RMS/v^alpha (alpha fitted on training data)", r"RMS/$v^{\alpha}$"), ("M4 MLP", "MLP"), ("M1 speed-only (LightGBM on speed features)", "speed only")]
    fig, ax = plt.subplots(figsize=(COL_W, 2.3))
    for k, (m, lab) in enumerate(models):
        for j, (D, nm, col) in enumerate([(S3, "legacy split (val = test track)", PALETTE[1]), (S1, "leave-one-map-out", PALETTE[0])]):
            r = D[D.model == m]
            if len(r) == 0:
                continue
            r = r.iloc[0]
            y = k + (j - 0.5) * 0.3
            ax.errorbar(r.r2, y, xerr=[[r.r2 - max(r.r2_lo, -1)], [r.r2_hi - r.r2]], fmt="o", ms=3, color=col, capsize=2, lw=1, label=nm if k == 0 else None)
    ax.set_yticks(range(len(models))); ax.set_yticklabels([m[1] for m in models]); ax.invert_yaxis()
    ax.set_xlabel(r"$R^2$ on held-out segments (legacy label, 95% CI)"); ax.set_xlim(-1, 1)
    ax.legend(fontsize=6.3, loc="lower left"); fig.tight_layout(); PL.savefig(fig, os.path.join(FIGURES, "beamng_protocol"))


def main():
    for f in [fig_sim_vs_real, fig_speed_shortcut, fig_lira_main, fig_value_of_sim, fig_robustness, fig_beamng_protocol]:
        print(f.__name__)
        try:
            f()
        except Exception as e:  # report and continue; a failing figure must not hide the others
            print("  ERROR", f.__name__, repr(e))


if __name__ == "__main__":
    main()
