"""LiRA-CD real-car experiments (protocol section 1). Parts (select with argv):

  ladder     supervised real-data baseline ladder M0-M6, leave-one-route-out (LORO)
  zeroshot   models trained ONLY on simulation (parametric simulator; and the legacy BeamNG data) -> LiRA
  fewshot    value of simulation: real-only vs. simulation-pretrained/augmented, k km of real labels
  gap        simulated vs. measured vibration on the SAME P79 road segments (simulator check)

Evaluation granularity: segment level (mean of pass-level predictions per 100 m segment) is primary; pass level
is secondary. CIs: cluster bootstrap over segments (B=2000); a conservative 1 km-block bootstrap is reported as a
sensitivity analysis. No test-route data enter training, early stopping, alpha, calibration or model selection.
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
from common.features import FEATURE_NAMES  # noqa: E402
from common.paths import PROCESSED, RESULTS, LIRA_ROUTES  # noqa: E402

OUT = os.path.join(RESULTS, "lira"); os.makedirs(OUT, exist_ok=True)
PRED = os.path.join(RESULTS, "predictions"); os.makedirs(PRED, exist_ok=True)
CFG = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "models.json")))
REF_MODEL = "M3 LightGBM (all features)"


# ------------------------------------------------------------------------------------------------- data
def load_lira():
    U = pd.read_csv(os.path.join(PROCESSED, "lira", "units.csv"))
    A = np.load(os.path.join(PROCESSED, "lira", "arrays.npz"))
    assert list(A["feature_names"]) == list(FEATURE_NAMES)
    U["block"] = U.route + "_" + U.direction + "_" + (U.start_m // 1000).astype(int).astype(str)
    D = dict(feat=A["feat"], seq=A["X_zv"][:, :, :1], y=U.mri.to_numpy(), group=U.segment.to_numpy())
    return U, D


def load_sim(name):
    m = pd.read_csv(os.path.join(PROCESSED, "sim", f"{name}_meta.csv"))
    A = np.load(os.path.join(PROCESSED, "sim", f"{name}_arrays.npz"))
    D = dict(feat=A["feat"], seq=A["X_zv"][:, :, :1], y=m.mri.to_numpy(), group=m.segment.to_numpy())
    return m, D


def take(D, idx):
    return {k: (v[idx] if isinstance(v, np.ndarray) else v) for k, v in D.items()}


def cat(*Ds):
    return {k: np.concatenate([d[k] for d in Ds]) for k in ("feat", "seq", "y", "group")}


def seg_level(U, idx, P):
    """Aggregate pass-level predictions to segments. P: (n,) or (S, n). Returns (seg_ids, y_seg, P_seg, blocks)."""
    P = np.atleast_2d(P)
    df = pd.DataFrame({"seg": U.segment.to_numpy()[idx], "y": U.mri.to_numpy()[idx], "blk": U.block.to_numpy()[idx]})
    for s in range(P.shape[0]):
        df[f"p{s}"] = P[s]
    g = df.groupby("seg", sort=True)
    agg = g.agg({"y": "first", "blk": "first", **{f"p{s}": "mean" for s in range(P.shape[0])}})
    return agg.index.to_numpy(), agg.y.to_numpy(), agg[[f"p{s}" for s in range(P.shape[0])]].to_numpy().T, agg.blk.to_numpy()


def inner_loro(U, tr_idx):
    routes = U.route.to_numpy()[tr_idx]
    out = []
    for r in np.unique(routes):
        out.append((np.where(routes != r)[0], np.where(routes == r)[0]))
    return out


def predict_any(m, D):
    return m.predict_seeds(D) if isinstance(m, M.TorchModel) else m.predict(D)


def write_preds(U, idx, P, model, part, fold, fname):
    P = np.atleast_2d(P)
    rows = []
    for s in range(P.shape[0]):
        rows.append(pd.DataFrame(dict(part=part, fold=fold, segment=U.segment.to_numpy()[idx], task=U.task.to_numpy()[idx],
                                      pass_id=U.pass_id.to_numpy()[idx], y=U.mri.to_numpy()[idx], model=model,
                                      seed=s if P.shape[0] > 1 else -1, pred=P[s])))
    pd.concat(rows).to_csv(fname, mode="a", header=not os.path.exists(fname), index=False)


def summarise(U, preds_by_model, idx_all, tag, ref=REF_MODEL):
    """preds_by_model: name -> (S, n_units) aligned with idx_all (pooled over folds)."""
    out = {}
    seg_P = {}
    for k, P in preds_by_model.items():
        seg, y, Ps, blk = seg_level(U, idx_all, P)
        seg_P[k] = Ps
    df_seg = report.evaluate(y, seg_P, seg, ref=ref if ref in seg_P else None, label=f"{tag}_segment")
    df_blk = report.evaluate(y, seg_P, blk, label=f"{tag}_segment_1kmblock")
    yu = U.mri.to_numpy()[idx_all]
    df_pass = report.evaluate(yu, preds_by_model, U.segment.to_numpy()[idx_all], label=f"{tag}_pass", B=500)
    for d, nm in [(df_seg, "segment"), (df_blk, "segment_1kmblock"), (df_pass, "pass")]:
        d.to_csv(os.path.join(OUT, f"{tag}_{nm}_metrics.csv"), index=False)
    # per held-out route (segment level, point estimates)
    rows = []
    for r in LIRA_ROUTES:
        m = U.route.to_numpy()[idx_all] == r
        if m.sum() == 0:
            continue
        for k, P in preds_by_model.items():
            seg, y_r, Ps, _ = seg_level(U, idx_all[m], np.atleast_2d(P)[:, m])
            from common.stats import metrics
            mm = [metrics(y_r, p) for p in Ps]
            rows.append(dict(route=r, model=k, n_segments=len(seg), **{s: float(np.mean([x[s] for x in mm])) for s in ("mae", "rmse", "bias", "spearman", "r2", "kappa")}))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, f"{tag}_per_route.csv"), index=False)
    return df_seg


# ------------------------------------------------------------------------------------------------- parts
def part_ladder(U, D):
    fname = os.path.join(PRED, "lira_ladder.csv")
    if os.path.exists(fname):
        os.remove(fname)
    allP, allidx, sel_log = {}, [], []
    for R in LIRA_ROUTES:
        tr = np.where(U.route != R)[0]; te = np.where(U.route == R)[0]
        Dtr, Dte = take(D, tr), take(D, te)
        inner = inner_loro(U, tr)
        ladder = M.standard_ladder()
        preds, inner_mae = {}, {}
        for m in ladder:
            t0 = time.time()
            if isinstance(m, M.TorchModel):
                m.fit(Dtr)
            else:
                m.fit(Dtr, inner=inner)
            preds[m.name] = predict_any(m, Dte)
            write_preds(U, te, preds[m.name], m.name, "ladder", R, fname)
            print(f"  [ladder {R}] {m.name:58s} unit MAE={np.mean(np.abs(np.atleast_2d(preds[m.name]).mean(0) - Dte['y'])):.3f} ({time.time()-t0:.0f}s)", flush=True)
        # M6: inner-LORO selection among M2c, M3, M4, M5 (neural nets with 2 seeds for selection)
        cands = {"M2c": lambda: M.PhysicsIndex(None), "M3": lambda: M.GBM(), "M4": lambda: M.TorchModel("mlp", seeds=(0, 1)),
                 "M5": lambda: M.TorchModel("cnn", seeds=(0, 1))}
        for key, mk in cands.items():
            errs = []
            for itr, iva in inner:
                mm = mk()
                Di, Dv = take(Dtr, itr), take(Dtr, iva)
                mm.fit(Di) if isinstance(mm, M.TorchModel) else mm.fit(Di, inner=None)
                pv = np.atleast_2d(predict_any(mm, Dv)).mean(0)
                _, yv, pvs, _ = seg_level(U.iloc[tr].reset_index(drop=True), iva, pv)
                errs.append(float(np.mean(np.abs(pvs[0] - yv))))
            inner_mae[key] = float(np.mean(errs))
        best = min(inner_mae, key=inner_mae.get)
        name_map = {"M2c": "M2c RMS/v^alpha (alpha fitted on training data)", "M3": REF_MODEL, "M4": "M4 MLP", "M5": "M5 1D-CNN"}
        preds["M6 inner-validation-selected model"] = preds[name_map[best]]
        sel_log.append(dict(test_route=R, selected=best, **{f"inner_mae_{k}": v for k, v in inner_mae.items()}))
        print(f"  [ladder {R}] M6 selects {best} (inner LORO MAE {inner_mae})", flush=True)
        for k, P in preds.items():
            allP.setdefault(k, []).append(np.atleast_2d(P))
        allidx.append(te)
    idx = np.concatenate(allidx)
    nseed = {k: max(p.shape[0] for p in v) for k, v in allP.items()}
    P = {k: np.concatenate([np.repeat(p, nseed[k], 0) if p.shape[0] == 1 else p for p in v], axis=1) for k, v in allP.items()}
    pd.DataFrame(sel_log).to_csv(os.path.join(OUT, "ladder_model_selection.csv"), index=False)
    df = summarise(U, P, idx, "ladder")
    print(report.fmt(df).to_string(index=False))
    return df


SIM_SETS = {"p79": "p79_train", "p79-fixedvehicle": "p79_train_fixedvehicle", "p79-idealsensor": "p79_train_idealsensor",
            "p79-measuredsensor": "p79_train_measuredsensor",   # post-hoc sensitivity analysis only
            "p79-measuredmix": "p79_train_measuredmix"}          # post-hoc sensitivity analysis only


def sim_training_set(test_route, which):
    """which: 'iso', 'p79', 'p79+iso', 'p79-fixedvehicle', 'p79-idealsensor'. P79-based sets never include the
    test route's own profile."""
    parts = []
    p79_key = which.replace("+iso", "")
    if p79_key in SIM_SETS:
        m, Ds = load_sim(SIM_SETS[p79_key])
        parts.append(take(Ds, np.where(m.route.to_numpy() != test_route)[0]))
    if "iso" in which:
        _, Di = load_sim("iso_train")
        parts.append(Di)
    return cat(*parts)


def part_zeroshot(U, D):
    fname = os.path.join(PRED, "lira_zeroshot.csv")
    if os.path.exists(fname):
        os.remove(fname)
    allP, allidx = {}, []
    for R in LIRA_ROUTES:
        te = np.where(U.route == R)[0]; Dte = take(D, te)
        preds = {}
        for which in ["iso", "p79", "p79+iso", "p79-fixedvehicle", "p79-idealsensor"]:
            Dsim = sim_training_set(R, which)
            ms = [M.PhysicsIndex(None, label=f"Z sim[{which}] physics index (alpha fitted in sim)"), M.GBM(label=f"Z sim[{which}] LightGBM")]
            if which in ("iso", "p79+iso"):     # compute allocation fixed before results: 3 seeds, 2 sim sets
                ms.append(M.TorchModel("cnn", seeds=(0, 1, 2), label=f"Z sim[{which}] 1D-CNN"))
            for m in ms:
                t0 = time.time()
                m.fit(Dsim)
                preds[m.name] = predict_any(m, Dte)
                write_preds(U, te, preds[m.name], m.name, "zeroshot", R, fname)
                print(f"  [zeroshot {R}] {m.name:55s} unit MAE={np.mean(np.abs(np.atleast_2d(preds[m.name]).mean(0) - Dte['y'])):.3f} ({time.time()-t0:.0f}s)", flush=True)
        # legacy BeamNG data -> LiRA (vertical-only features, both BeamNG label definitions)
        bm = pd.read_csv(os.path.join(PROCESSED, "beamng", "meta.csv")); bA = np.load(os.path.join(PROCESSED, "beamng", "arrays.npz"))
        for lab in ["iri_raw", "iri_corr"]:
            ok = bm[lab].notna().to_numpy()
            Db = dict(feat=bA["feat"][ok], seq=bA["X_zv"][ok][:, :, :1], y=bm[lab].to_numpy()[ok], group=bm.cluster.to_numpy()[ok])
            m = M.GBM(label=f"Z BeamNG[{lab}] LightGBM").fit(Db)
            preds[m.name] = m.predict(Dte); write_preds(U, te, preds[m.name], m.name, "zeroshot", R, fname)
            m = M.PhysicsIndex(None, label=f"Z BeamNG[{lab}] physics index").fit(Db)
            preds[m.name] = m.predict(Dte); write_preds(U, te, preds[m.name], m.name, "zeroshot", R, fname)
        for k, P in preds.items():
            allP.setdefault(k, []).append(np.atleast_2d(P))
        allidx.append(te)
    idx = np.concatenate(allidx)
    nseed = {k: max(p.shape[0] for p in v) for k, v in allP.items()}
    P = {k: np.concatenate([np.repeat(p, nseed[k], 0) if p.shape[0] == 1 else p for p in v], axis=1) for k, v in allP.items()}
    df = summarise(U, P, idx, "zeroshot", ref=None)
    print(report.fmt(df).to_string(index=False))
    return df


def part_zeroshot_sensor(U, D):
    """POST-HOC sensitivity analysis (added after the primary zero-shot results): the primary simulation set
    (telematics configuration 55-62 Hz mixed with a smartphone configuration) vs. the same vehicles and profiles with a
    telematics sensor matched to the measured LiRA-CD sensor statistics. Paired comparison on the same test units;
    written to separate files (zeroshot_sensor_*), the primary results are not changed."""
    fname = os.path.join(PRED, "lira_zeroshot_sensor.csv")
    if os.path.exists(fname):
        os.remove(fname)
    allP, allidx = {}, []
    for R in LIRA_ROUTES:
        te = np.where(U.route == R)[0]; Dte = take(D, te)
        preds = {}
        for which in ["p79", "p79-measuredsensor", "p79-measuredmix"]:
            Dsim = sim_training_set(R, which)
            for m in [M.PhysicsIndex(None, label=f"Z sim[{which}] physics index (alpha fitted in sim)"), M.GBM(label=f"Z sim[{which}] LightGBM")]:
                m.fit(Dsim)
                preds[m.name] = m.predict(Dte); write_preds(U, te, preds[m.name], m.name, "zeroshot_sensor", R, fname)
        for k, P in preds.items():
            allP.setdefault(k, []).append(np.atleast_2d(P))
        allidx.append(te)
    idx = np.concatenate(allidx)
    P = {k: np.concatenate(v, axis=1) for k, v in allP.items()}
    df = summarise(U, P, idx, "zeroshot_sensor", ref="Z sim[p79] LightGBM")
    print(report.fmt(df).to_string(index=False))
    return df


def sample_blocks(U, tr, k_km, rng):
    """Contiguous 1 km blocks (10 consecutive P79 segments of one route-direction) from the training routes."""
    if k_km == "all":
        return tr
    blocks = U.block.to_numpy()[tr]
    ub = np.unique(blocks)
    chosen = rng.choice(ub, size=min(len(ub), int(k_km)), replace=False)
    return tr[np.isin(blocks, chosen)]


def part_fewshot(U, D, k_list=None, draws=None, cnn_k=None):
    fs = CFG["few_shot"]
    k_list = k_list or fs["k_km"]; draws = draws or fs["draws"]
    cnn_k = cnn_k or [1, 5, 20, "all"]
    fname = os.path.join(PRED, "lira_fewshot.csv")
    if os.path.exists(fname):
        os.remove(fname)
    rows = []
    for R in LIRA_ROUTES:
        tr = np.where(U.route != R)[0]; te = np.where(U.route == R)[0]; Dte = take(D, te)
        Dsim = sim_training_set(R, "p79+iso")
        sim_pi = M.PhysicsIndex(None).fit(Dsim)
        sim_cnn = M.TorchModel("cnn", seeds=(0, 1, 2)).fit(Dsim)
        sim_states = sim_cnn.states()
        for k in k_list:
            for d in range(1 if k == "all" else draws):
                rng = np.random.default_rng(1000 * d + 7)
                sub = sample_blocks(U, tr, k, rng)
                Dk = take(D, sub)
                km = len(np.unique(U.segment.to_numpy()[sub])) / 10.0
                preds = {}
                preds["real-only physics index"] = M.PhysicsIndex(None).fit(Dk).predict(Dte)
                preds["sim physics index + real intercept"] = copy_pi(sim_pi).recalibrate_intercept(Dk).predict(Dte)
                preds["real-only LightGBM"] = M.GBM().fit(Dk).predict(Dte)
                w = np.concatenate([np.full(len(Dsim["y"]), 1.0), np.full(len(Dk["y"]), len(Dsim["y"]) / max(len(Dk["y"]), 1))])
                preds["sim+real LightGBM (balanced weights)"] = M.GBM().fit(cat(Dsim, Dk), weights=w).predict(Dte)
                preds["sim-only LightGBM (k=0 reference)"] = None
                if k in cnn_k:
                    scratch = M.TorchModel("cnn", seeds=(0, 1, 2)).fit(Dk, epochs=fs["scratch_epochs"])
                    preds["real-only 1D-CNN"] = scratch.predict_seeds(Dte)
                    ft = M.TorchModel("cnn", seeds=(0, 1, 2))
                    ft.mu_x, ft.sd_x, ft.sd_s, ft.mu_c, ft.sd_c = sim_cnn.mu_x, sim_cnn.sd_x, sim_cnn.sd_s, sim_cnn.mu_c, sim_cnn.sd_c
                    ft.fit(Dk, init_states=sim_states, epochs=fs["finetune_epochs"], lr=fs["finetune_lr"], keep_norm=True)
                    preds["sim-pretrained 1D-CNN + real fine-tuning"] = ft.predict_seeds(Dte)
                for name, P in preds.items():
                    if P is None:
                        continue
                    seg, y, Ps, blk = seg_level(U, te, P)
                    mae = float(np.mean([np.mean(np.abs(p - y)) for p in Ps]))
                    rows.append(dict(test_route=R, k_km=str(k), real_km=km, draw=d, model=name, seg_mae=mae, n_seg=len(seg)))
                    write_preds(U, te, P, f"{name}|k={k}|draw={d}", "fewshot", R, fname)
                print(f"  [fewshot {R}] k={k} draw={d} real_km={km:.1f} " + " ".join(f"{r['model'][:22]}={r['seg_mae']:.3f}" for r in rows[-len([p for p in preds.values() if p is not None]):]), flush=True)
        # zero real labels (sim only) for the same models
        for name, P in [("sim-only physics index", sim_pi.predict(Dte)), ("sim-only 1D-CNN", sim_cnn.predict_seeds(Dte)),
                        ("sim-only LightGBM", M.GBM().fit(Dsim).predict(Dte))]:
            seg, y, Ps, blk = seg_level(U, te, P)
            rows.append(dict(test_route=R, k_km="0", real_km=0.0, draw=0, model=name, seg_mae=float(np.mean([np.mean(np.abs(p - y)) for p in Ps])), n_seg=len(seg)))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "fewshot_raw.csv"), index=False)
    return df


def copy_pi(pi):
    q = M.PhysicsIndex(pi.alpha, pi.feature, pi.name); q.coef = pi.coef.copy(); return q


def part_gap(U):
    """Simulated (p79_test vehicles) vs measured (LiRA) vibration on identical P79 segments."""
    m, Ds = load_sim("p79_test")
    lr_i = FEATURE_NAMES.index("log_rms")
    sim = pd.DataFrame(dict(segment=m.segment, lr=Ds["feat"][:, lr_i], lv=Ds["feat"][:, FEATURE_NAMES.index("log_v_mean")], y=m.mri, sensor=m.sensor))
    A = np.load(os.path.join(PROCESSED, "lira", "arrays.npz"))
    real = pd.DataFrame(dict(segment=U.segment, lr=A["feat"][:, lr_i], lv=A["feat"][:, FEATURE_NAMES.index("log_v_mean")], y=U.mri))
    out = {}
    for name, d in [("sim", sim), ("real", real)]:
        X = np.column_stack([np.ones(len(d)), np.log(d.y + 1e-3), d.lv])
        b, *_ = np.linalg.lstsq(X, d.lr.to_numpy(), rcond=None)
        out[name] = dict(n=len(d), coef_log_iri=float(b[1]), coef_log_v=float(b[2]), alpha_equiv=float(b[2] / b[1]) if b[1] != 0 else np.nan)
    # segment-level comparison at matched speed band (60-100 km/h) to avoid speed confounding
    sb = lambda d: d[(np.exp(d.lv) * 3.6 > 60) & (np.exp(d.lv) * 3.6 < 100)].groupby("segment").lr.mean()
    j = pd.concat([sb(sim).rename("sim"), sb(real).rename("real")], axis=1).dropna()
    from scipy.stats import spearmanr
    out["segment_match"] = dict(n_segments=len(j), spearman=float(spearmanr(j.sim, j.real)[0]),
                                pearson=float(np.corrcoef(j.sim, j.real)[0, 1]), mean_log_ratio_real_minus_sim=float((j.real - j.sim).mean()))
    j.to_csv(os.path.join(OUT, "gap_segment_logrms.csv"))
    json.dump(out, open(os.path.join(OUT, "gap_summary.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    return out


def main():
    U, D = load_lira()
    print("LiRA units", len(U), "segments", U.segment.nunique(), "routes", U.route.unique().tolist())
    parts = sys.argv[1:] or ["ladder", "gap", "zeroshot", "fewshot"]
    if "ladder" in parts:
        part_ladder(U, D)
    if "gap" in parts:
        part_gap(U)
    if "zeroshot" in parts:
        part_zeroshot(U, D)
    if "fewshot" in parts:
        part_fewshot(U, D)
    if "zeroshot_sensor" in parts:          # post-hoc sensitivity analysis, never part of the default run
        part_zeroshot_sensor(U, D)


if __name__ == "__main__":
    main()
