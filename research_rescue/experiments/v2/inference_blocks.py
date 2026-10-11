"""Revision v2, R6 + Section 2 of PROTOCOL_V2.md: inference with dependence-aware units.

* paired MAE differences vs the real-trained LightGBM with cluster bootstrap at three levels (segment, 1 km block,
  5 km block; B = 2000, paired resamples, Holm within each level); a difference is "supported" only if the 5 km-block
  interval excludes 0
* route-level descriptive interval: mean of the 4 per-route differences, t distribution with 3 df
* residual autocorrelation of segment errors by lag (100 m ... 5 km)
* variance components of pass-level log errors: segment effects vs telematics-unit (vehicle) effects vs residual

Inputs: v1 prediction files (results/predictions/lira_ladder.csv, lira_zeroshot.csv) - the confirmatory v1 models.
Outputs: results/v2/inference_blocks.csv, residual_acf.csv, variance_components.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, EPS, LIRA_ROUTES, load_lira  # noqa: E402
from common.paths import RESULTS  # noqa: E402
from common.stats import holm  # noqa: E402

B = 2000
REF = "REAL_GBM"


def seg_preds(U, file, model):
    """(segment, seed) -> segment-mean prediction; returns a DataFrame indexed by segment with one column per seed."""
    P = pd.read_csv(os.path.join(RESULTS, "predictions", file))
    P = P[P.model == model]
    s = P.groupby(["segment", "seed"]).pred.mean().unstack("seed")
    return s


def cluster_sums(abs_err, cl):
    """abs_err: (S, n) absolute errors; cl: (n,) cluster codes -> (S, C) per-cluster sums and (C,) counts."""
    C = cl.max() + 1
    sums = np.stack([np.bincount(cl, weights=a, minlength=C) for a in abs_err])
    cnt = np.bincount(cl, minlength=C).astype(float)
    return sums, cnt


def boot_diff(ea, eb, cl, seed=0):
    """MAE(a) - MAE(b) (each = mean over its seeds of the per-seed MAE) with a cluster bootstrap of the clusters cl."""
    sa, n = cluster_sums(ea, cl); sb, _ = cluster_sums(eb, cl)
    rng = np.random.default_rng(seed)
    C = len(n)
    W = np.stack([np.bincount(rng.integers(0, C, C), minlength=C) for _ in range(B)]).astype(float)   # (B, C)
    tot = W @ n
    da = (W @ sa.T) / tot[:, None]; db = (W @ sb.T) / tot[:, None]
    d = da.mean(1) - db.mean(1)
    d0 = (sa.sum(1) / n.sum()).mean() - (sb.sum(1) / n.sum()).mean()
    p = 2 * min(np.mean(d <= 0), np.mean(d >= 0))
    return float(d0), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float(min(p, 1.0)), int(C)


def main():
    U, _ = load_lira()
    seg = U.groupby("segment").agg(route=("route", "first"), direction=("direction", "first"), start=("start_m", "first"),
                                   y=("mri", "first"), block=("block", "first"), block5=("block5", "first")).sort_index()
    M = {
        "REAL_GBM": seg_preds(U, "lira_ladder.csv", "M3 LightGBM (all features)"),
        "MLP": seg_preds(U, "lira_ladder.csv", "M4 MLP"),
        "CNN": seg_preds(U, "lira_ladder.csv", "M5 1D-CNN"),
        "SPEED": seg_preds(U, "lira_ladder.csv", "M1 speed-only (LightGBM on speed features)"),
        "INDEX": seg_preds(U, "lira_ladder.csv", "M2c RMS/v^alpha (alpha fitted on training data)"),
        "SIM_P79": seg_preds(U, "lira_zeroshot.csv", "Z sim[p79] LightGBM"),
        "SIM_P79ISO": seg_preds(U, "lira_zeroshot.csv", "Z sim[p79+iso] LightGBM"),
    }
    pair = {"CPH1": "CPH6", "CPH6": "CPH1", "M3": "M13", "M13": "M3"}
    med = seg.groupby("route").y.median()
    M["MAP"] = pd.DataFrame({-1: seg.route.map(lambda r: med[pair[r]])})
    for k in M:
        M[k] = M[k].reindex(seg.index)
        assert M[k].notna().all().all(), k
    # ensembles of the neural nets (average of the 5 seeds' predictions) in addition to the per-seed convention
    M["MLP_ens"] = M["MLP"].mean(1).to_frame()
    M["CNN_ens"] = M["CNN"].mean(1).to_frame()
    y = seg.y.to_numpy()
    E = {k: np.abs(v.to_numpy().T - y[None, :]) for k, v in M.items()}          # (S, n)
    codes = {"segment": np.arange(len(seg)), "block1km": pd.factorize(seg.block)[0], "block5km": pd.factorize(seg.block5)[0]}

    comps = [("SIM_P79", REF), ("SIM_P79ISO", REF), ("MLP", REF), ("MLP_ens", REF), ("CNN", REF), ("CNN_ens", REF),
             ("SPEED", REF), ("INDEX", REF), ("MAP", REF), ("MAP", "SPEED")]
    rows = []
    for lvl, cl in codes.items():
        res = {}
        for a, b in comps:
            res[(a, b)] = boot_diff(E[a], E[b], cl, seed=1)
        padj = holm({k: v[3] for k, v in res.items()})
        for (a, b), (d0, lo, hi, p, C) in res.items():
            rows.append(dict(level=lvl, model=a, reference=b, diff=d0, lo=lo, hi=hi, p=p, p_holm=padj[(a, b)], n_clusters=C))
    T = pd.DataFrame(rows)
    # route-level descriptive interval (t, 3 df) on the per-route MAE differences
    rr = []
    for a, b in comps:
        dd = []
        for r in LIRA_ROUTES:
            m = (seg.route == r).to_numpy()
            dd.append(E[a][:, m].mean(1).mean() - E[b][:, m].mean(1).mean())
        dd = np.array(dd); mu = dd.mean(); se = dd.std(ddof=1) / 2.0
        q = st.t.ppf(0.975, 3)
        rr.append(dict(level="route_t3", model=a, reference=b, diff=float(mu), lo=float(mu - q * se), hi=float(mu + q * se),
                       p=np.nan, p_holm=np.nan, n_clusters=4,
                       **{f"diff_{r}": float(x) for r, x in zip(LIRA_ROUTES, dd)},
                       n_routes_a_better=int(np.sum(dd < 0))))
    T = pd.concat([T, pd.DataFrame(rr)], ignore_index=True)
    T["supported_5km"] = T.apply(lambda r: (r.lo > 0 or r.hi < 0) if r.level == "block5km" else np.nan, axis=1)
    T.to_csv(os.path.join(OUT, "inference_blocks.csv"), index=False)

    # residual autocorrelation by lag (segments of one route-direction, exact lag)
    acf = []
    for k in ("REAL_GBM", "SIM_P79", "INDEX"):
        e = pd.Series(M[k].to_numpy().mean(1) - y, index=seg.index)
        df = seg.assign(e=e).set_index(["route", "direction", "start"]).e
        for lag in [1, 2, 3, 5, 10, 20, 30, 50]:
            a_, b_ = [], []
            for (r, d), g in df.groupby(level=[0, 1]):
                g = g.droplevel([0, 1])
                nxt = g.reindex(g.index + 100.0 * lag)
                ok = nxt.notna().to_numpy()
                a_.append(g.to_numpy()[ok]); b_.append(nxt.to_numpy()[ok])
            a_, b_ = np.concatenate(a_), np.concatenate(b_)
            acf.append(dict(model=k, lag_m=100 * lag, r=float(np.corrcoef(a_, b_)[0, 1]), n_pairs=len(a_)))
    pd.DataFrame(acf).to_csv(os.path.join(OUT, "residual_acf.csv"), index=False)

    # variance components of pass-level log errors: segment effects + telematics-unit effects (two-way, alternating LS)
    vc = []
    L = pd.read_csv(os.path.join(RESULTS, "predictions", "lira_ladder.csv"))
    Z = pd.read_csv(os.path.join(RESULTS, "predictions", "lira_zeroshot.csv"))
    for name, df, model in (("REAL_GBM", L, "M3 LightGBM (all features)"), ("SIM_P79", Z, "Z sim[p79] LightGBM")):
        q = df[df.model == model].copy(); q["task"] = q.task.astype(str)
        q = q.merge(U[["segment", "task", "pass_id", "unit", "route"]], on=["segment", "task", "pass_id"], how="left")
        q["logerr"] = np.log((q.pred + EPS) / (q.y + EPS))

        def decompose(d):
            s_eff = pd.Series(0.0, index=d.segment.unique()); u_eff = pd.Series(0.0, index=d.unit.unique())
            for _ in range(50):
                u_eff = (d.logerr - d.segment.map(s_eff)).groupby(d.unit).mean()
                s_eff = (d.logerr - d.unit.map(u_eff)).groupby(d.segment).mean()
            u_eff = u_eff - u_eff.mean()
            res = d.logerr - d.segment.map(s_eff) - d.unit.map(u_eff)
            return float(u_eff.std(ddof=1)), float(s_eff.std(ddof=1)), float(res.std(ddof=1)), u_eff
        sd_u, sd_s, sd_r, u_eff = decompose(q)
        rng = np.random.default_rng(3); blocks = q.segment.map(U.drop_duplicates("segment").set_index("segment").block).to_numpy()
        ub = np.unique(blocks); bs = []
        for _ in range(200):
            pick = rng.choice(ub, len(ub))
            idx = np.concatenate([np.where(blocks == b_)[0] for b_ in pick])
            bs.append(decompose(q.iloc[idx])[0])
        vc.append(dict(model=name, sd_unit_effect=sd_u, sd_unit_lo=float(np.percentile(bs, 2.5)), sd_unit_hi=float(np.percentile(bs, 97.5)),
                       sd_segment_effect=sd_s, sd_residual=sd_r, n_units=int(q.unit.nunique()),
                       **{f"unit_{k}": float(v) for k, v in u_eff.items()}))
    pd.DataFrame(vc).to_csv(os.path.join(OUT, "variance_components.csv"), index=False)

    print(T[T.level != "route_t3"].pivot_table(index=["model", "reference"], columns="level",
                                               values=["diff", "lo", "hi"]).round(3).to_string())
    print(T[T.level == "route_t3"][["model", "reference", "diff", "lo", "hi", "n_routes_a_better"]].round(3).to_string(index=False))
    print(pd.DataFrame(acf).pivot(index="lag_m", columns="model", values="r").round(2).to_string())
    print(pd.DataFrame(vc)[["model", "sd_unit_effect", "sd_unit_lo", "sd_unit_hi", "sd_segment_effect", "sd_residual"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
