"""Review check 4 (read-only): is "real drives alone beat the worst-matched variants from 10 km" a property of the
simulators or of level-offset calibration? Re-runs the v1 pre-specified pooled arm ("sim+real LightGBM, balanced
weights", exp_lira.part_fewshot) for V0, V1, V3, V5 on the paper's exact draws (default_rng(1000*d+7), contiguous 1 km
training-route blocks), and pairs it with the paper's real_only (R4) and sim_all_cal (R3) arms.
Writes a CSV to the scratchpad only."""
import sys
import time
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

RR, OUTF = sys.argv[1], sys.argv[2]
EPS = 1e-3
ROUTES = ["CPH1", "CPH6", "M3", "M13"]


def block_id(df, L=1000):
    return df.route.astype(str) + "_" + df.direction.astype(str) + "_" + (df.start_m // L).astype(int).astype(str)


U = pd.read_csv(f"{RR}/data/processed/lira/units.csv")
F = np.load(f"{RR}/data/processed/lira/arrays.npz")["feat"].astype(np.float32)
U["block"] = block_id(U)
y = U.mri.to_numpy()

SIMSETS = {"V0": ("p79_train", None), "V1": ("p79_train", "autopi"), "V3": ("p79_train_idealsensor", None),
           "V5": ("p79_train_measuredsensor", None)}
cache = {}


def simset(name):
    if name not in cache:
        m = pd.read_csv(f"{RR}/data/processed/sim/{name}_meta.csv")
        with np.load(f"{RR}/data/processed/sim/{name}_arrays.npz") as Z:
            cache[name] = (m, Z["feat"].astype(np.float32))
    return cache[name]


def gbm():
    return LGBMRegressor(n_estimators=400, learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.9,
                         reg_lambda=1.0, verbose=-1, random_state=0, num_leaves=7, min_child_samples=20)


def sample_blocks(tr_idx, k, rng):
    blocks = U.block.to_numpy()[tr_idx]
    ub = np.unique(blocks)
    chosen = rng.choice(ub, size=min(len(ub), int(k)), replace=False)
    return tr_idx[np.isin(blocks, chosen)]


def seg_mae(idx, p):
    d = pd.DataFrame(dict(seg=U.segment.to_numpy()[idx], y=y[idx], p=p))
    g = d.groupby("seg").agg(y=("y", "first"), p=("p", "mean"))
    return float(np.mean(np.abs(g.p - g.y))), len(g), float(np.mean(g.p - g.y))


rows = []
t0 = time.time()
vids = sys.argv[3].split(",") if len(sys.argv) > 3 else list(SIMSETS)
ks = [5, 10, 20]
for vid in vids:
    name, sens = SIMSETS[vid]
    m, Xs_all = simset(name)
    for R in ROUTES:
        te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
        sel = (m.route != R).to_numpy()
        if sens is not None:
            sel &= (m.sensor == sens).to_numpy()
        Xs, ys = Xs_all[sel], m.mri.to_numpy()[sel]
        for k in ks:
            for d in range(20):
                rng = np.random.default_rng(1000 * d + 7)
                sub = sample_blocks(tr, k, rng)
                X = np.vstack([Xs, F[sub]]); yy = np.concatenate([ys, y[sub]])
                w = np.concatenate([np.ones(len(ys)), np.full(len(sub), len(ys) / max(len(sub), 1))])
                g = gbm().fit(X, np.log(yy + EPS), sample_weight=w)
                p = np.clip(np.exp(g.predict(F[te])) - EPS, 0, None)
                mae, n, bias = seg_mae(te, p)
                rows.append(dict(vid=vid, fold=R, k_km=k, draw=d, arm="sim_real_pooled", seg_mae=mae, n_seg=n, seg_bias=bias))
            print(f"{vid} {R} k={k} done ({time.time() - t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(OUTF, index=False)
pd.DataFrame(rows).to_csv(OUTF, index=False)
print("finished", flush=True)
