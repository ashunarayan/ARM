"""Revision v3, item V3-1 (evaluation/PROTOCOL_V3.md): pooled simulation + real training ("sim_real_pooled").

Design from the v1 protocol (section 1, "simulation-pretrained + real fine-tuned"), implemented for LightGBM exactly as
in v1 (`experiments/exp_lira.py`, part_fewshot: "sim+real LightGBM (balanced weights)") and omitted in v2:
for held-out route R, simulator variant v, k km and draw d, LightGBM (first configuration) is trained on the union of
  - the variant's simulated units over the training-route profiles (`variant_training_set(v, R)`), weight 1 each, and
  - the real units of the k km of training-route blocks drawn by the shared sampler (`sample_blocks`,
    `default_rng(1000 * d + 7)`, identical to every other arm), weight n_sim / n_real each (equal total weight),
and predicts every unit of R. Class R (design pre-specified in v1, evaluated on routes whose results are known).

Outputs (results/v3/):
  pooled_vs_real.csv          one row per variant, fold, k, draw (seg_mae, seg_bias, n_seg, n_sim, n_real)
  pooled_segpred.npz          per-draw segment predictions for k in {5, 20} (item V3-2)
Usage: python pooled_vs_real.py [V0 V1 ...]   (several processes in parallel, then: python pooled_vs_real.py merge)
"""
from __future__ import annotations

import glob
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
from common_v2 import (RESCUE, M, LIRA_ROUTES, load_lira, variant_training_set, sample_blocks, seg_table)  # noqa: E402

OUT = os.path.join(RESCUE, "results", "v3"); os.makedirs(OUT, exist_ok=True)
VIDS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V10"]
KS = [1, 2, 5, 10, 20]
DRAWS = 20
KEEP_SEGPRED = (5, 20)


def fit_pooled(Xs, ys, Xr, yr):
    """v1 recipe: equal total weight for simulated and real units, first LightGBM configuration."""
    w = np.concatenate([np.ones(len(ys)), np.full(len(yr), len(ys) / max(len(yr), 1))])
    g = M.GBM()
    g.fit(dict(feat=np.vstack([Xs, Xr]), y=np.concatenate([ys, yr])), weights=w)
    return g


def main(vids):
    tag = "_" + "-".join(vids)
    t0 = time.time()
    U, F = load_lira()
    y = U.mri.to_numpy()
    rows, segpred = [], {}
    for vid in vids:
        for R in LIRA_ROUTES:
            te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
            m, Xs, ys = variant_training_set(vid, R)
            assert not (m.route == R).any(), "test-route profile in the simulated training set"
            for k in KS:
                P = []
                for d in range(DRAWS):
                    sub = sample_blocks(U, tr, k, np.random.default_rng(1000 * d + 7))
                    assert set(U.route.to_numpy()[sub]) <= set(LIRA_ROUTES) - {R}
                    g = fit_pooled(Xs, ys, F[sub], y[sub])
                    p = g.predict(dict(feat=F[te], y=np.zeros(len(te))))
                    St = seg_table(U, te, p)
                    rows.append(dict(vid=vid, fold=R, k_km=k, draw=d, arm="sim_real_pooled",
                                     seg_mae=float(np.mean(np.abs(St.p - St.y))), seg_bias=float(np.mean(St.p - St.y)),
                                     n_seg=len(St), n_sim=len(ys), n_real=len(sub)))
                    if k in KEEP_SEGPRED:
                        P.append(St.p.to_numpy())
                        segpred[f"seg|{R}"] = St.segment.to_numpy().astype(str)
                if k in KEEP_SEGPRED:
                    segpred[f"{vid}|{R}|{k}"] = np.array(P)
                print(f"{vid} {R:5s} k={k:2d} mean seg MAE {np.mean([r['seg_mae'] for r in rows[-DRAWS:]]):.3f} "
                      f"({time.time() - t0:.0f}s)", flush=True)
            pd.DataFrame(rows).to_csv(os.path.join(OUT, f"pooled_vs_real{tag}.csv"), index=False)   # checkpoint
    pd.DataFrame(rows).to_csv(os.path.join(OUT, f"pooled_vs_real{tag}.csv"), index=False)
    np.savez_compressed(os.path.join(OUT, f"pooled_segpred{tag}.npz"), **segpred)
    print("done", tag, f"({time.time() - t0:.0f}s)", flush=True)


def merge():
    parts = sorted(glob.glob(os.path.join(OUT, "pooled_vs_real_V*.csv")))
    D = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    assert sorted(D.vid.unique()) == sorted(VIDS), D.vid.unique()
    assert len(D) == len(VIDS) * len(LIRA_ROUTES) * len(KS) * DRAWS, len(D)
    D.to_csv(os.path.join(OUT, "pooled_vs_real.csv"), index=False)
    Z = {}
    for p in sorted(glob.glob(os.path.join(OUT, "pooled_segpred_V*.npz"))):
        with np.load(p) as z:
            Z.update({k: z[k] for k in z.files})
    np.savez_compressed(os.path.join(OUT, "pooled_segpred.npz"), **Z)
    for p in parts + sorted(glob.glob(os.path.join(OUT, "pooled_segpred_V*.npz"))):
        os.remove(p)
    print(len(D), "rows merged;", len(Z), "prediction arrays")


if __name__ == "__main__":
    if sys.argv[1:] == ["merge"]:
        merge()
    else:
        main(sys.argv[1:] or VIDS)
