"""Generate paper tables (LaTeX + Markdown + CSV) and the machine-readable final results
(results/final_results.json, results/final_results.csv). Every number comes from result files."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import plotting as PL  # noqa: E402
from common.paths import RESULTS, TABLES, PROCESSED  # noqa: E402

FINAL = {}
FLAT = []


def ci(r, s, nd=2):
    if not np.isfinite(r[s]):          # e.g. Spearman of a constant prediction is undefined
        return "--"
    return f"{r[s]:.{nd}f} [{r[s + '_lo']:.{nd}f}, {r[s + '_hi']:.{nd}f}]"


def save(df, name, caption, label, col_format=None):
    df.to_csv(os.path.join(TABLES, f"{name}.csv"), index=False)
    with open(os.path.join(TABLES, f"{name}.md"), "w", encoding="utf-8") as f:
        f.write(PL.md_table(df))
    PL.latex_table(df, os.path.join(TABLES, f"{name}.tex"), caption, label, col_format)


def record(section, df_metrics, keep_cols=("mae", "mae_lo", "mae_hi", "rmse", "spearman", "spearman_lo", "spearman_hi", "r2", "kappa", "n_units", "n_clusters")):
    FINAL[section] = df_metrics.to_dict(orient="records")
    for r in df_metrics.to_dict(orient="records"):
        FLAT.append(dict(section=section, model=r.get("model"), **{k: r.get(k) for k in keep_cols if k in r}))


def table_datasets():
    rows = []
    bm = os.path.join(PROCESSED, "beamng", "meta.csv")
    if os.path.exists(bm):
        B = pd.read_csv(bm); E = B[B.is_eval]
        rows.append(dict(dataset="BeamNG (legacy corpus)", source="game-engine simulation", vehicles="3 (Hopper, Sunburst, Vivace)",
                         routes="3 maps / 19 trips", km=f"{E.shape[0] * 0.1:.0f}", units=f"{len(E)} segments",
                         label="IRI of ray-cast elevation profile (raw / legacy-corrected)",
                         label_mean=f"{E.iri_raw.mean():.1f} / {E.iri_corr.mean():.1f}"))
    lu = os.path.join(PROCESSED, "lira", "units.csv")
    if os.path.exists(lu):
        U = pd.read_csv(lu)
        for cls, m in [("urban", U.route.str.startswith("CPH")), ("motorway", U.route.str.startswith("M"))]:
            u = U[m]; seg = u.groupby("segment").mri.first()
            rows.append(dict(dataset=f"LiRA-CD ({cls})", source="real cars (Renault Zoe, AutoPi)", vehicles=f"{u.unit.nunique()} telematics units",
                             routes=", ".join(sorted(u.route.unique())) + f" ({u.groupby(['route','direction','task','pass_id']).ngroups} passes)",
                             km=f"{len(seg) * 0.1:.0f}", units=f"{len(seg)} segments / {len(u)} segment-passes",
                             label="P79 profilometer IRI", label_mean=f"{seg.mean():.2f}"))
    for name, nice in [("p79_train", "Sim: P79 profiles, train vehicles"), ("iso_train", "Sim: ISO-type profiles, train"),
                       ("iso_test", "Sim: ISO-type, held-out routes & vehicles")]:
        p = os.path.join(PROCESSED, "sim", f"{name}_meta.csv")
        if os.path.exists(p):
            S = pd.read_csv(p)
            rows.append(dict(dataset=nice, source="parametric half-car + sensor model", vehicles=f"{S.vehicle.nunique()} sampled",
                             routes=f"{S.route.nunique()} profiles", km=f"{S.segment.nunique() * 0.1:.0f}", units=f"{len(S)} segment-passes",
                             label="IRI of driven profile", label_mean=f"{S.mri.mean():.2f}"))
    pv = os.path.join(RESULTS, "pvs", "pvs_windows.csv")
    if os.path.exists(pv):
        P = pd.read_csv(pv)
        rows.append(dict(dataset="PVS", source="real cars (3 vehicles, 3 drivers)", vehicles="3", routes="3 routes / 9 trips",
                         km=f"{len(P) * 0.1:.0f}", units=f"{len(P)} windows / {P.cell.nunique()} GPS cells", label="surface type, subjective quality",
                         label_mean="-"))
    df = pd.DataFrame(rows)
    save(df, "table1_datasets", "Datasets used in this study (km = distinct 100 m units x 0.1).", "tab:datasets")
    FINAL["datasets"] = rows


def table_baselines():
    p = os.path.join(RESULTS, "lira", "ladder_segment_metrics.csv")
    if not os.path.exists(p):
        return
    L = pd.read_csv(p)
    rec = L.copy(); record("lira_ladder_segment", rec)
    df = pd.DataFrame(dict(Model=L.model, **{"MAE (m/km)": [ci(r, "mae") for _, r in L.iterrows()],
                                            "RMSE": [f"{v:.2f}" for v in L.rmse],
                                            "Spearman": [ci(r, "spearman") for _, r in L.iterrows()],
                                            "kappa": [f"{v:.2f}" for v in L.kappa],
                                            "dMAE vs LightGBM": [("ref" if m == r_ else f"{a:+.2f} [{b:+.2f}, {c:+.2f}]{'*' if p_ < 0.05 else ''}")
                                                                 for m, r_, a, b, c, p_ in zip(L.model, L.reference, L.dmae_vs_ref, L.dmae_lo, L.dmae_hi, L.p_holm)]}))
    save(df, "table2_baselines_lira", "Real-car results (LiRA-CD), leave-one-route-out, segment level (mean of pass predictions per 100 m), "
         "95\\% cluster-bootstrap CIs over segments; * Holm-adjusted $p<0.05$ for the paired difference to LightGBM.", "tab:baselines")


def table_real_world():
    pr = os.path.join(RESULTS, "lira", "ladder_per_route.csv"); zp = os.path.join(RESULTS, "lira", "zeroshot_segment_metrics.csv")
    if not os.path.exists(pr):
        return
    PR = pd.read_csv(pr)
    keep = ["M0 constant (training median)", "M1 speed-only (LightGBM on speed features)", "M2c RMS/v^alpha (alpha fitted on training data)",
            "M3 LightGBM (all features)", "M4 MLP", "M5 1D-CNN", "M6 inner-validation-selected model"]
    t = PR[PR.model.isin(keep)].pivot(index="model", columns="route", values="mae").reindex(keep).round(2)
    s = PR[PR.model.isin(keep)].pivot(index="model", columns="route", values="spearman").reindex(keep).round(2)
    out = pd.DataFrame({"Model": t.index})
    for r in ["CPH1", "CPH6", "M3", "M13"]:
        if r in t.columns:
            out[f"{r} MAE"] = t[r].to_numpy(); out[f"{r} rho"] = s[r].to_numpy()
    if os.path.exists(zp):
        Z = pd.read_csv(zp); record("lira_zeroshot_segment", Z)
        zz = pd.DataFrame(dict(Model=["(sim only) " + m.replace("Z ", "") for m in Z.model], **{"pooled MAE": [ci(r, "mae") for _, r in Z.iterrows()],
                                                                                              "pooled rho": [ci(r, "spearman") for _, r in Z.iterrows()]}))
        save(zz, "table3b_zeroshot", "Models trained only on simulated data, evaluated on all LiRA-CD routes (segment level, 95\\% CIs).", "tab:zeroshot")
    save(out, "table3_real_world_per_route", "Segment-level MAE (m/km) and Spearman $\\rho$ per held-out LiRA-CD route.", "tab:perroute")
    FINAL["lira_per_route"] = PR.to_dict(orient="records")


def table_ablations():
    rows = []
    L = os.path.join(RESULTS, "lira", "ladder_segment_metrics.csv")
    if os.path.exists(L):
        D = pd.read_csv(L).set_index("model")
        def add(factor, a, b, la, lb):
            if a in D.index and b in D.index:
                rows.append(dict(factor=factor, setting_a=la, mae_a=ci(D.loc[a], "mae"), setting_b=lb, mae_b=ci(D.loc[b], "mae"),
                                 domain="LiRA-CD (real)"))
        add("speed normalisation", "M2a RMS only (alpha=0)", "M2c RMS/v^alpha (alpha fitted on training data)", "alpha = 0", "alpha fitted")
        add("speed normalisation", "M2b RMS/v^0.5", "M2d RMS*(v_ref/v)^2 (legacy exponent, gravity removed)", "alpha = 0.5", "alpha = 2 (legacy)")
        add("speed input", "M3 LightGBM (all features)", "M3 LightGBM (no speed features)", "GBM with speed", "GBM without speed")
        add("speed input", "M5 1D-CNN", "M5 1D-CNN (no speed input)", "CNN with speed", "CNN without speed")
        add("architecture", "M3 LightGBM (all features)", "M5 1D-CNN", "LightGBM", "1D-CNN")
        add("architecture", "M4 MLP", "M5 1D-CNN", "MLP", "1D-CNN")
    Z = os.path.join(RESULTS, "lira", "zeroshot_segment_metrics.csv")
    if os.path.exists(Z):
        D = pd.read_csv(Z).set_index("model")
        def addz(factor, a, b, la, lb):
            if a in D.index and b in D.index:
                rows.append(dict(factor=factor, setting_a=la, mae_a=ci(D.loc[a], "mae"), setting_b=lb, mae_b=ci(D.loc[b], "mae"),
                                 domain="sim -> LiRA-CD"))
        addz("profile source (sim)", "Z sim[iso] LightGBM", "Z sim[p79] LightGBM", "ISO-type synthetic", "measured P79 profiles")
        addz("vehicle randomisation (sim)", "Z sim[p79-fixedvehicle] LightGBM", "Z sim[p79] LightGBM", "one fixed vehicle", "randomised vehicles")
        addz("sensor model (sim)", "Z sim[p79-idealsensor] LightGBM", "Z sim[p79] LightGBM", "ideal sensor", "sensor model")
        addz("label source (sim)", "Z BeamNG[iri_corr] LightGBM", "Z sim[p79] LightGBM", "BeamNG legacy labels", "parametric sim, P79 labels")
    B = os.path.join(RESULTS, "beamng", "ablation_features.csv")
    if os.path.exists(B):
        for r in pd.read_csv(B).to_dict(orient="records"):
            rows.append(r)
    if rows:
        df = pd.DataFrame(rows)
        save(df, "table4_ablations", "One-factor-at-a-time ablations (segment-level MAE in m/km, 95\\% CIs).", "tab:ablations")
        FINAL["ablations"] = rows


def table_generalisation():
    rows = []
    p = os.path.join(RESULTS, "sim", "unseen_vehicle_paired.csv")
    if os.path.exists(p):
        for r in pd.read_csv(p).to_dict(orient="records"):
            rows.append(dict(test="unseen vehicles (random split)", model=r["model"], result=f"MAE seen {r['mae_seen']:.3f} -> unseen {r['mae_unseen']:.3f}; "
                             f"diff {r['diff']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]", criterion_met=r["generalises"]))
    p = os.path.join(RESULTS, "sim", "vehicle_region_extrapolation.csv")
    if os.path.exists(p):
        for r in pd.read_csv(p).to_dict(orient="records"):
            rows.append(dict(test="vehicle extrapolation (f_s > 1.25 Hz unseen)", model=r["model"],
                             result=f"MAE low-f_s {r['mae_low_fs_unseen']:.3f} vs high-f_s {r['mae_high_fs_unseen']:.3f}; diff {r['diff']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]",
                             criterion_met=bool(r["hi"] / max(r["mae_low_fs_unseen"], 1e-9) <= 0.10)))
    p = os.path.join(RESULTS, "beamng", "seen_vs_unseen_vehicle.csv")
    if os.path.exists(p):
        for r in pd.read_csv(p).to_dict(orient="records"):
            rows.append(dict(test="BeamNG: vehicle held out (S2 vs S1)", model=r["model"],
                             result=f"MAE seen {r['mae_vehicle_seen']:.2f} -> unseen {r['mae_vehicle_unseen']:.2f}; diff {r['diff']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]",
                             criterion_met=r["generalises"]))
    for fn, tag in [("speed_invariance.csv", ""), ("speed_invariance_p79trained.csv", "")]:
        p = os.path.join(RESULTS, "sim", fn)
        if os.path.exists(p):
            for r in pd.read_csv(p).to_dict(orient="records"):
                rows.append(dict(test=f"speed 40->100 km/h ({r['sweep']})", model=r["model"],
                                 result=f"rel. change {100*r['rel_change_40_100']:+.1f}% [{100*r['ci_lo']:+.1f}, {100*r['ci_hi']:+.1f}]",
                                 criterion_met=r["invariant_40_100"]))
    if rows:
        df = pd.DataFrame(rows)
        save(df, "table5_generalisation", "Controlled generalisation tests of the first analysis round in the parametric simulator, with criteria fixed in advance "
             "(unseen vehicles: relative MAE increase $\\le$10\\% incl. CI; speed: $|$change$|\\le$10\\% incl. CI).", "tab:generalisation",
             r">{\raggedright\arraybackslash}p{4.3cm}>{\raggedright\arraybackslash}p{4.3cm}>{\raggedright\arraybackslash}p{6.4cm}l")
        FINAL["generalisation"] = rows
    p = os.path.join(RESULTS, "sim", "robustness.csv")
    if os.path.exists(p):
        FINAL["robustness"] = pd.read_csv(p).to_dict(orient="records")


def table_sim_ranges():
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "sim_ranges.json")))
    rows = []
    for k, v in cfg["vehicle"].items():
        rows.append(dict(group="vehicle", parameter=k, range=f"{v['range'][0]:g} - {v['range'][1]:g}", unit=v["unit"], source=v["src"]))
    for kind in ("sensor_autopi", "sensor_phone"):
        c = cfg[kind]
        rows.append(dict(group=kind.replace("sensor_", "sensor: "), parameter="rate / LSB / noise / tilt SD",
                         range=f"{c['rate_hz'][0]}-{c['rate_hz'][1]} Hz / {c['lsb_g']} g / {c['noise_ug_rthz'][0]}-{c['noise_ug_rthz'][1]} ug/rtHz / {c['tilt_deg_sd']} deg",
                         unit="-", source=c["src"]))
    sp = cfg["speed"]
    rows.append(dict(group="speed", parameter="base speed", range=f"{sp['base_kmh'][0]}-{sp['base_kmh'][1]}", unit="km/h", source="design choice (independent of roughness)"))
    df = pd.DataFrame(rows)
    save(df, "tableS_sim_ranges", "Parameter ranges of the parametric simulator (sensitivity ranges; sources in config/sim\\_ranges.json).", "tab:simranges")


def table_supplement():
    """Supplementary tables: pass level, 1 km-block bootstrap, complete BeamNG protocol tables, PVS AUCs."""
    for src, name, cap in [("lira/ladder_pass_metrics.csv", "tableS_pass_level",
                            "Real cars (LiRA-CD), leave-one-route-out, pass level (every segment-pass is a unit; CIs from a cluster bootstrap over segments)."),
                           ("lira/ladder_segment_1kmblock_metrics.csv", "tableS_block_bootstrap",
                            "Real cars (LiRA-CD), segment level with 95\\% CIs from a cluster bootstrap over 1 km blocks (sensitivity analysis)."),
                           ("lira/zeroshot_segment_metrics.csv", "tableS_zeroshot_full",
                            "Estimators trained only on simulated data, evaluated on all LiRA-CD routes (segment level, cluster-bootstrap 95\\% CIs).")]:
        p = os.path.join(RESULTS, src)
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        df = pd.DataFrame({"Model": d.model.str.replace("Z ", "", regex=False), "MAE (m/km)": [ci(r, "mae") for _, r in d.iterrows()],
                           "Spearman": [ci(r, "spearman") for _, r in d.iterrows()], "kappa": d.kappa.round(2),
                           "units": d.n_units, "clusters": d.n_clusters})
        save(df, name, cap, "tab:" + name)
    rows = []
    for src, split, lab in [("beamng/S3_iri_corr_metrics.csv", "S3: earlier split (val. and test on test track)", "legacy"),
                            ("beamng/S1_iri_corr_metrics.csv", "S1: leave-one-map-out", "legacy"),
                            ("beamng/S1_legacy_recipe_metrics.csv", "S1: leave-one-map-out", "legacy"),
                            ("beamng/S1_iri_raw_metrics.csv", "S1: leave-one-map-out", "raw profile"),
                            ("beamng/S2_iri_raw_metrics.csv", "S2: leave-one-vehicle-and-map-out", "raw profile")]:
        p = os.path.join(RESULTS, src)
        if os.path.exists(p):
            for _, r in pd.read_csv(p).iterrows():
                rows.append({"Split": split, "Label": lab, "Model": r.model, "MAE (m/km)": ci(r, "mae"), "Spearman": ci(r, "spearman"),
                             "R2": ci(r, "r2")})
    if rows:
        save(pd.DataFrame(rows), "tableS_beamng", "BeamNG corpus: all estimators and splits (segment level, cluster-bootstrap 95\\% CIs over 100 m location cells).",
             "tab:s_beamng", r">{\raggedright\arraybackslash}p{3.4cm}l>{\raggedright\arraybackslash}p{4.6cm}lll")
    p = os.path.join(RESULTS, "pvs", "pvs_auc.csv")
    if os.path.exists(p):
        d = pd.read_csv(p)
        df = pd.DataFrame({"Task": d.task, "Predictors": d.predictors,
                           "AUC [95% CI]": [f"{r.auc:.2f} [{r.auc_lo:.2f}, {r.auc_hi:.2f}]" for _, r in d.iterrows()],
                           "windows": d.n_windows, "positives": d.n_positive})
        save(df, "tableS_pvs_auc", "PVS: leave-one-route-out logistic regressions, AUC with cluster-bootstrap 95\\% CIs over GPS cells.", "tab:s_pvs")


def collect_rest():
    for key, p in [("iri_validation", os.path.join(RESULTS, "iri_validation.json")), ("sim_unit_test", os.path.join(RESULTS, "sim_unit_test.json")),
                   ("legacy_fidelity", os.path.join(RESULTS, "legacy_fidelity_check.json")), ("lira_gap", os.path.join(RESULTS, "lira", "gap_summary.json"))]:
        if os.path.exists(p):
            FINAL[key] = json.load(open(p))
    for key, p in [("beamng_S1_raw", "beamng/S1_iri_raw_metrics.csv"), ("beamng_S1_corr", "beamng/S1_iri_corr_metrics.csv"),
                   ("beamng_S2_raw", "beamng/S2_iri_raw_metrics.csv"), ("beamng_S3_corr", "beamng/S3_iri_corr_metrics.csv"),
                   ("beamng_S1_legacy_recipe", "beamng/S1_legacy_recipe_metrics.csv"), ("pvs_auc", "pvs/pvs_auc.csv"),
                   ("lira_ladder_pass", "lira/ladder_pass_metrics.csv"), ("lira_ladder_1kmblock", "lira/ladder_segment_1kmblock_metrics.csv"),
                   ("speed_exponent_by_domain", "speed_exponent_by_domain.csv")]:
        fp = os.path.join(RESULTS, p)
        if os.path.exists(fp):
            d = pd.read_csv(fp)
            if "mae" in d.columns:
                record(key, d)
            else:
                FINAL[key] = d.to_dict(orient="records")


def main():
    table_datasets(); table_baselines(); table_real_world(); table_ablations(); table_generalisation(); table_sim_ranges()
    table_supplement(); collect_rest()
    json.dump(FINAL, open(os.path.join(RESULTS, "final_results.json"), "w"), indent=1, default=float)
    pd.DataFrame(FLAT).to_csv(os.path.join(RESULTS, "final_results.csv"), index=False)
    print("sections:", list(FINAL.keys()))


if __name__ == "__main__":
    main()
