"""Revision v3, item V3-6 (evaluation/PROTOCOL_V3.md): paired test of within-route ranking (class E).

Within-route Spearman (and partial Spearman given segment speed) of segment means, for real-trained LightGBM (v1
ladder), and V0- and V1-trained LightGBM (zero-shot), each minus the untrained statistic RMS/v^0.5 on the same
segments; per route and mean over routes; 95 % intervals from 5 km blocks resampled within each route (B = 2000,
seed 2026). Ported from review/v3_checks/c3_rank_paired.py. Output: results/v3/rank_paired.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v3 import OUT, RESCUE, LIRA_ROUTES, load_lira, v1_pass_predictions  # noqa: E402

B = 2000
REF = "untrained RMS/v^0.5"


def spearman(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def partial(a, b, v):
    rx, ry, rz = rankdata(a), rankdata(b), rankdata(v)
    Z = np.column_stack([np.ones_like(rz), rz])
    ex = rx - Z @ np.linalg.lstsq(Z, rx, rcond=None)[0]; ey = ry - Z @ np.linalg.lstsq(Z, ry, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1])


def main():
    U, _ = load_lira()
    VP = pd.read_csv(os.path.join(RESCUE, "results", "v2", "variants_pass_predictions.csv.gz"))

    def variant(vid):
        q = VP[(VP.vid == vid) & (VP.model == "GBM")]
        out = np.full(len(U), np.nan); out[q.unit.to_numpy()] = q.pred.to_numpy(); return out
    preds = {"real LightGBM": v1_pass_predictions(U, "lira_ladder.csv", "M3 LightGBM (all features)"),
             "V0 LightGBM (zero-shot)": variant("V0"), "V1 LightGBM (zero-shot)": variant("V1"),
             REF: U.a_rms.to_numpy() / np.sqrt(U.v_mean.to_numpy())}
    S = pd.DataFrame(dict(segment=U.segment, route=U.route, b5=U.block5, y=U.mri, v=U.v_mean, **preds))
    G = S.groupby("segment").agg(route=("route", "first"), b5=("b5", "first"), y=("y", "first"), v=("v", "mean"),
                                 **{k: (k, "mean") for k in preds}).reset_index()
    comps = [k for k in preds if k != REF]
    rng = np.random.default_rng(2026)
    rows = []
    for metric in ("rho", "partial rho"):
        fn = (lambda d, k: spearman(d[k], d.y)) if metric == "rho" else (lambda d, k: partial(d[k], d.y, d.v))
        groups = {r: G[G.route == r].reset_index(drop=True) for r in LIRA_ROUTES}
        bl = {r: pd.factorize(groups[r].b5)[0] for r in LIRA_ROUTES}
        idx_by_block = {r: [np.where(bl[r] == b)[0] for b in range(bl[r].max() + 1)] for r in LIRA_ROUTES}
        boot = {c: {r: [] for r in LIRA_ROUTES + ["mean"]} for c in comps}
        for _ in range(B):
            per = {}
            for r in LIRA_ROUTES:
                bs = rng.integers(0, len(idx_by_block[r]), len(idx_by_block[r]))
                per[r] = groups[r].iloc[np.concatenate([idx_by_block[r][b] for b in bs])]
            for c in comps:
                diffs = [fn(per[r], c) - fn(per[r], REF) for r in LIRA_ROUTES]
                for r, x in zip(LIRA_ROUTES, diffs):
                    boot[c][r].append(x)
                boot[c]["mean"].append(float(np.mean(diffs)))
        for c in comps + [REF]:
            for r in LIRA_ROUTES:
                rows.append(dict(metric=metric, model=c, route=r, value=fn(groups[r], c), diff=np.nan, lo=np.nan,
                                 hi=np.nan, n_blocks=len(idx_by_block[r])))
        for c in comps:
            pt = {r: fn(groups[r], c) - fn(groups[r], REF) for r in LIRA_ROUTES}
            pt["mean"] = float(np.mean([pt[r] for r in LIRA_ROUTES]))
            for r in LIRA_ROUTES + ["mean"]:
                rows.append(dict(metric=metric, model=c, route=r, value=np.nan, diff=pt[r],
                                 lo=float(np.percentile(boot[c][r], 2.5)), hi=float(np.percentile(boot[c][r], 97.5)),
                                 n_blocks=len(idx_by_block[r]) if r != "mean" else np.nan))
                print(metric, c, r, f"{pt[r]:+.3f} [{rows[-1]['lo']:+.3f}, {rows[-1]['hi']:+.3f}]", flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "rank_paired.csv"), index=False)


if __name__ == "__main__":
    main()
