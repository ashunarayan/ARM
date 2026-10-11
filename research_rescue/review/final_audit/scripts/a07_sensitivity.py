"""Audit step 7: (a) sensitivity of the real-only k-km comparator to the LightGBM configuration (all six frozen configs,
and inner leave-one-route-out selection within the drawn blocks, as the Method sentence implies); (b) per-route joint
cells at 20 km; (c) 10 km level-offset wins for V1/V3/V5; (d) M7 within-route rho; (e) traces of secondary numbers."""
import os
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from scipy.stats import rankdata

RR = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue"
ROUTES = ["CPH1", "CPH6", "M3", "M13"]
EPS = 1e-3
GRID = [dict(num_leaves=nl, min_child_samples=mc) for nl in (7, 15, 31) for mc in (20, 60)]
U = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "units.csv"))
F = np.load(os.path.join(RR, "data", "processed", "lira", "arrays.npz"))["feat"]
y = U.mri.to_numpy(); seg_of = U.segment.to_numpy(); route = U.route.to_numpy()
U["blk1"] = U.route + "_" + U.direction + "_" + (U.start_m // 1000).astype(int).astype(str)


def fitpred(X, t, Xte, p):
    m = LGBMRegressor(n_estimators=400, learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.9,
                      reg_lambda=1.0, verbose=-1, random_state=0, **p)
    return np.clip(np.exp(m.fit(X, np.log(t + EPS)).predict(Xte)) - EPS, 0, None)


def draw_blocks(tr, k, d):
    rng = np.random.default_rng(1000 * d + 7)
    b = U.blk1.to_numpy()[tr]; ub = np.unique(b)
    return tr[np.isin(b, rng.choice(ub, size=min(len(ub), k), replace=False))]


def seg_ae(idx, p):
    s = pd.DataFrame(dict(seg=seg_of[idx], p=p, y=y[idx])).groupby("seg", sort=True).agg(p=("p", "mean"), y=("y", "first"))
    return np.abs(s.p - s.y).to_numpy()


# (a)
import sys
for k in ((5, 20) if "a" in sys.argv[1:] else ()):
    tot = np.zeros((len(GRID) + 1, 20)); per_route = {}
    for R in ROUTES:
        te = np.where(route == R)[0]; tr = np.where(route != R)[0]
        for d in range(20):
            sub = draw_blocks(tr, k, d)
            preds = [fitpred(F[sub], y[sub], F[te], p) for p in GRID]
            for j, p in enumerate(preds):
                tot[j, d] += seg_ae(te, p).sum()
            # inner leave-one-route-out among the training routes present in the sample
            rs = np.unique(route[sub])
            if len(rs) >= 2:
                sc = []
                for p in GRID:
                    e = [np.mean(np.abs(fitpred(F[sub[route[sub] != r]], y[sub[route[sub] != r]], F[sub[route[sub] == r]], p)
                                        - y[sub[route[sub] == r]])) for r in rs]
                    sc.append(np.mean(e))
                j = int(np.argmin(sc))
            else:
                j = 0
            tot[-1, d] += seg_ae(te, preds[j]).sum()
    tot /= 1678
    print(f"(a) real-only k={k}: pooled MAE by config " + ", ".join(f"{GRID[j]['num_leaves']}/{GRID[j]['min_child_samples']}: {tot[j].mean():.3f}"
                                                              for j in range(len(GRID))) + f"; inner-LORO selected: {tot[-1].mean():.3f}")

# (b) per-route joint cells at 20 km and (c) 10 km level-offset wins: from stored per-route files
PB = pd.read_csv(os.path.join(RR, "results", "v3", "pooled_by_route.csv"))
print("(b) pooled_by_route.csv columns:", PB.columns.tolist())
q = PB[(PB.k_km == 20) & (PB.vid.isin([f"V{i}" for i in range(9)]))]
dcol = "d"
print(f"    k=20 cells: {len(q)}, negative {int((q[dcol] < 0).sum())}, positive {int((q[dcol] > 0).sum())} "
      f"(by route {q[q[dcol] > 0].fold.value_counts().to_dict() if 'fold' in q else ''}), max positive {q[dcol].max():+.4f}")
PV = pd.read_csv(os.path.join(RR, "results", "v2", "paired_vs_real.csv"))
w = PV[(PV.arm == "sim_all_cal") & (PV.k_km == 10) & PV.vid.isin(["V1", "V3", "V5"])]
print("(c) level offset 10 km, draws better than real-only:", w.set_index("vid").n_better.to_dict())
s = PV[(PV.arm == "sim_same") & (PV.k_km == 20) & PV.vid.isin([f"V{i}" for i in range(9)])]
print("    equal budget 20 km diff range %.3f..%.3f; top3 %s" % (s["diff"].min(), s["diff"].max(), s.nlargest(3, "diff").vid.tolist()))
s1 = PV[(PV.arm == "sim_same") & (PV.k_km == 1) & PV.vid.isin([f"V{i}" for i in range(9)])]
print("    equal budget 1 km: better than real LightGBM in", s1.n_better.min(), "-", s1.n_better.max(), "; vs index", s1.n_better_idx.min(), "-", s1.n_better_idx.max())

# (d) M7 within-route rho and MAE
PI = pd.read_csv(os.path.join(RR, "results", "v2", "physics_inversion_segments.csv"))
for mod, g in PI.groupby("model"):
    g = g.merge(U.groupby("segment").agg(route=("route", "first")), left_on="segment", right_index=True)
    rh = [np.corrcoef(rankdata(d.p), rankdata(d.y))[0, 1] for _, d in g.groupby("route")]
    print(f"(d) {mod}: n={len(g)} per route {g.route.value_counts().to_dict()} within rho {np.mean(rh):.3f} pooled MAE {np.mean(np.abs(g.p - g.y)):.3f}")

# (e) precise within-route MAE of M3 and V2 after offset
T = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "a02_table.csv"), index_col=0)
print("(e) M3 within-route MAE = %.5f" % T.loc["M3 LightGBM (all features)", "within_mae"])
NS = pd.read_csv(os.path.join(RR, "results", "v3", "nosim_index.csv"))
print("    nosim_index.csv arms:", NS.arm.unique().tolist() if "arm" in NS else NS.columns.tolist())
