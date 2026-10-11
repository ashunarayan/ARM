"""Audit step 3: value-of-simulation numbers (Table III, abstract) recomputed with independent code.

(a) real-only LightGBM at k = 5, 20: RETRAINED here (own LightGBM call, own block sampler) and compared per draw with
    results/v2/value_of_simulation.csv
(b) level offset at k = 5, 20 for V0-V8: recomputed from cached zero-shot all-unit predictions (cache first checked
    against the held-out predictions in variants_pass_predictions.csv.gz)
(c) joint training at k = 5, 20 for V0-V8: recomputed from saved per-draw segment predictions (pooled_segpred.npz)
(d) 5 km-block bootstrap of the draw-averaged differences (test-route intervals)
(e) mean-of-route class levels vs segment-weighted class levels
"""
import os, time
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

RR = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue"
ROUTES = ["CPH1", "CPH6", "M3", "M13"]
EPS = 1e-3
MEAS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]

U = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "units.csv"))
F = np.load(os.path.join(RR, "data", "processed", "lira", "arrays.npz"))["feat"]
y = U.mri.to_numpy()
U["blk1"] = U.route + "_" + U.direction + "_" + (U.start_m // 1000).astype(int).astype(str)
U["blk5"] = U.route + "_" + U.direction + "_" + (U.start_m // 5000).astype(int).astype(str)
seg_of = U.segment.to_numpy()


def draw_blocks(tr, k, d):
    rng = np.random.default_rng(1000 * d + 7)
    b = U.blk1.to_numpy()[tr]
    ub = np.unique(b)
    ch = rng.choice(ub, size=min(len(ub), k), replace=False)
    return tr[np.isin(b, ch)]


def lgbm():
    return LGBMRegressor(n_estimators=400, learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.9,
                         reg_lambda=1.0, verbose=-1, random_state=0, num_leaves=7, min_child_samples=20)


def segmean(idx, p):
    s = pd.DataFrame(dict(seg=seg_of[idx], p=p, y=y[idx])).groupby("seg", sort=True).agg(p=("p", "mean"), y=("y", "first"))
    return s


SEGS = {R: np.unique(seg_of[U.route.to_numpy() == R]) for R in ROUTES}
VS = pd.read_csv(os.path.join(RR, "results", "v2", "value_of_simulation.csv"))

# ---------------- (a) real-only retrain
t0 = time.time()
real_seg = {}       # (k, R) -> (20, nseg) segment predictions
maxdiff = 0.0
res_a = {}
for k in (5, 20):
    per_draw = np.zeros(20); n_units = []
    for R in ROUTES:
        te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
        P = []
        for d in range(20):
            sub = draw_blocks(tr, k, d)
            if R == ROUTES[0]:
                n_units.append(len(sub))
            g = lgbm().fit(F[sub], np.log(y[sub] + EPS))
            p = np.clip(np.exp(g.predict(F[te])) - EPS, 0, None)
            s = segmean(te, p)
            mae = np.mean(np.abs(s.p - s.y))
            ref = VS[(VS.arm == "real_only") & (VS.fold == R) & (VS.k_km == k) & (VS.draw == d)].seg_mae.iloc[0]
            maxdiff = max(maxdiff, abs(mae - ref))
            per_draw[d] += np.sum(np.abs(s.p - s.y))
            P.append(s.p.to_numpy())
        real_seg[(k, R)] = np.array(P)
    per_draw /= 1678
    res_a[k] = per_draw
    print(f"real-only k={k}: pooled MAE mean over draws {per_draw.mean():.4f} [2.5-97.5%: {np.percentile(per_draw, 2.5):.2f}, "
          f"{np.percentile(per_draw, 97.5):.2f}]  (CPH1-fold calibration units/draw mean {np.mean(n_units):.0f})")
print(f"  max |own retrain - stored| per fold-draw MAE: {maxdiff:.2e}   ({time.time() - t0:.0f}s)")

# ---------------- (b) level offset from cached zero-shot predictions
VP = pd.read_csv(os.path.join(RR, "results", "v2", "variants_pass_predictions.csv.gz"))
cal_seg = {}
rows = []
for vid in MEAS:
    with np.load(os.path.join(RR, "data", "processed", "v3", f"zeroshot_allunits_{vid}.npz")) as z:
        Z = {R: z[R] for R in ROUTES}
    q = VP[(VP.vid == vid) & (VP.model == "GBM")]
    for R in ROUTES:
        qq = q[q.fold == R]
        assert np.allclose(Z[R][qq.unit.to_numpy()], qq.pred.to_numpy(), atol=1e-5), (vid, R)
    for k in (5, 20):
        per_draw = np.zeros(20)
        for R in ROUTES:
            te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
            P = []
            for d in range(20):
                sub = draw_blocks(tr, k, d)
                c = np.median(np.log((y[sub] + EPS) / (Z[R][sub] + EPS)))
                p = np.clip(np.exp(np.log(Z[R][te] + EPS) + c) - EPS, 0, None)
                s = segmean(te, p)
                per_draw[d] += np.sum(np.abs(s.p - s.y))
                P.append(s.p.to_numpy())
            cal_seg[(vid, k, R)] = np.array(P)
        per_draw /= 1678
        rows.append(dict(vid=vid, arm="level_offset", k=k, mae=per_draw.mean(), better=int((per_draw < res_a[k]).sum()),
                         diff=(per_draw - res_a[k]).mean()))

# ---------------- (c) joint training from saved segment predictions
PS = np.load(os.path.join(RR, "results", "v3", "pooled_segpred.npz"))
for R in ROUTES:
    assert list(PS[f"seg|{R}"]) == list(SEGS[R])
for vid in MEAS:
    for k in (5, 20):
        per_draw = np.zeros(20)
        for R in ROUTES:
            ys = segmean(np.where(U.route == R)[0], np.zeros((U.route == R).sum())).y.to_numpy()
            per_draw += np.abs(PS[f"{vid}|{R}|{k}"] - ys).sum(1)
        per_draw /= 1678
        rows.append(dict(vid=vid, arm="joint", k=k, mae=per_draw.mean(), better=int((per_draw < res_a[k]).sum()),
                         diff=(per_draw - res_a[k]).mean()))
A = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(A.pivot_table(index="vid", columns=["arm", "k"], values=["mae", "diff", "better"]).round(3).to_string())
for arm in ("level_offset", "joint"):
    for k in (5, 20):
        q = A[(A.arm == arm) & (A.k == k)]
        print(f"{arm:12s} k={k:2d}: MAE {q.mae.min():.3f}-{q.mae.max():.3f}; diff {q['diff'].min():+.3f}..{q['diff'].max():+.3f}; "
              f"better draws {q.better.min()}-{q.better.max()} of 20")

# cross-check joint arm against pooled_vs_real.csv
PV = pd.read_csv(os.path.join(RR, "results", "v3", "pooled_vs_real.csv"))
PV["w"] = PV.seg_mae * PV.n_seg
g = PV.groupby(["vid", "k_km", "draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
g["mae"] = g.w / g.n
gm = g.groupby(["vid", "k_km"]).mae.mean().unstack()
print("pooled_vs_real.csv pooled MAE (mean over draws):"); print(gm.round(3).to_string())

# ---------------- (d) test-route intervals: draw-averaged segment error differences, 5 km block bootstrap
segtab = U.groupby("segment").agg(blk5=("blk5", "first"))
blk = np.concatenate([segtab.loc[SEGS[R], "blk5"].to_numpy() for R in ROUTES])
bid = pd.factorize(blk)[0]; C = bid.max() + 1
rng = np.random.default_rng(99)
W = rng.multinomial(C, np.ones(C) / C, size=2000)
cnt = np.bincount(bid, minlength=C)
yseg = {R: segmean(np.where(U.route == R)[0], np.zeros((U.route == R).sum())).y.to_numpy() for R in ROUTES}
out = []
for vid in MEAS:
    for k in (5, 20):
        for arm in ("level_offset", "joint"):
            dif = []
            for R in ROUTES:
                Pm = cal_seg[(vid, k, R)] if arm == "level_offset" else PS[f"{vid}|{R}|{k}"]
                dif.append((np.abs(Pm - yseg[R]) - np.abs(real_seg[(k, R)] - yseg[R])).mean(0))
            dseg = np.concatenate(dif)
            bs = (W @ np.bincount(bid, dseg, C)) / (W @ cnt)
            out.append(dict(vid=vid, k=k, arm=arm, diff=dseg.mean(), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5)))
O = pd.DataFrame(out)
print(O.round(3).to_string(index=False))
CU = pd.read_csv(os.path.join(RR, "results", "v3", "calib_uncertainty.csv"))
print("stored calib_uncertainty.csv:"); print(CU[["vid", "arm", "k_km", "diff", "lo", "hi"]].round(3).to_string(index=False))
