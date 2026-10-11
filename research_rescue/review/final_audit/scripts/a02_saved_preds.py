"""Audit step 2: recompute headline metrics from SAVED predictions with independent code (no project imports).

Covers: Table I (real estimators), V0 vs real paired 5 km-block bootstrap, variant zero-shot bias/levels/rho (Table II),
untrained RMS/v^0.5 ranking bound, residual ACF.
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import rankdata

RR = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue"
ROUTES = ["CPH1", "CPH6", "M3", "M13"]
CLS = {"CPH1": "urban", "CPH6": "urban", "M3": "motorway", "M13": "motorway"}
EPS = 1e-3

U = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "units.csv"))
U["blk5"] = U.route + "_" + U.direction + "_" + (U.start_m // 5000).astype(int).astype(str)
U["blk1"] = U.route + "_" + U.direction + "_" + (U.start_m // 1000).astype(int).astype(str)

# ---- labels: constant within segment? equal to the P79-profile label?
chk = U.groupby("segment").mri.agg(["min", "max"])
print("label constant within segment:", bool(np.allclose(chk["min"], chk["max"])))
P79 = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "p79_segments_100m.csv"))
P79["segment"] = P79.route + "_" + P79.direction + "_" + P79.start_m.astype(int).astype(str)
SEG = U.groupby("segment").agg(route=("route", "first"), direction=("direction", "first"), start=("start_m", "first"),
                               y=("mri", "first"), v=("v_mean", "mean"), blk5=("blk5", "first"), blk1=("blk1", "first"),
                               rep=("mri_reported", "first"), npass=("mri", "size"))
SEG["cls"] = SEG.route.map(CLS)
m = SEG.join(P79.set_index("segment")[["mri_profile", "consistent_reported"]], how="left")
print("segments:", len(SEG), " km:", len(SEG) / 10, " units:", len(U), " passes(task,pass)?", U.groupby(["task", "pass_id"]).ngroups,
      " telematics units:", U.unit.nunique())
print("U.mri == p79 mri_profile (max abs diff):", float(np.nanmax(np.abs(m.y - m.mri_profile))))
ok = m.consistent_reported.astype(bool) & m.rep.notna()
print("label vs P79-reported IRI: n=%d r=%.4f bias=%+.3f" % (ok.sum(), np.corrcoef(m.y[ok], m.rep[ok])[0, 1], (m.y[ok] - m.rep[ok]).mean()))
print("segments per route:", SEG.route.value_counts().to_dict(), " 5km blocks:", SEG.blk5.nunique())
print("mean IRI urban %.2f motorway %.2f; speed urban %.0f motorway %.0f km/h" % (
    SEG[SEG.cls == "urban"].y.mean(), SEG[SEG.cls == "motorway"].y.mean(),
    U[U.route.map(CLS) == "urban"].v_mean.mean() * 3.6, U[U.route.map(CLS) == "motorway"].v_mean.mean() * 3.6))
print("passes per segment: mean %.2f" % SEG.npass.mean())


def spear(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def pspear(a, b, z):
    ra, rb, rz = rankdata(a), rankdata(b), rankdata(z)
    res = lambda r: r - np.polyval(np.polyfit(rz, r, 1), rz)
    return float(np.corrcoef(res(ra), res(rb))[0, 1])


def summ(p, name, out=None):
    """p: Series indexed by segment (segment mean prediction)."""
    d = SEG.assign(p=p.reindex(SEG.index))
    assert d.p.notna().all(), name
    r = dict(name=name, pooled_mae=np.mean(np.abs(d.p - d.y)), bias=np.mean(d.p - d.y))
    for R in ROUTES:
        q = d[d.route == R]
        r["mae_" + R] = np.mean(np.abs(q.p - q.y)); r["rho_" + R] = spear(q.p, q.y); r["prho_" + R] = pspear(q.p, q.y, q.v)
    r["within_mae"] = np.mean([r["mae_" + R] for R in ROUTES])
    r["within_rho"] = np.mean([r["rho_" + R] for R in ROUTES])
    r["within_prho"] = np.mean([r["prho_" + R] for R in ROUTES])
    for c in ("urban", "motorway"):
        q = d[d.cls == c]
        r["level_" + c] = np.mean(np.log((q.p + EPS) / (q.y + EPS)))
        r["relerr_" + c] = np.mean(np.abs(q.p - q.y)) / q.y.mean()
    return r


# ---- real-trained ladder (segment means straight from the prediction file; seeds averaged = ensemble)
L = pd.read_csv(os.path.join(RR, "results", "predictions", "lira_ladder.csv.gz"))
print("ladder models:", L.model.unique().tolist())
seg_pred = {}
for mod, g in L.groupby("model"):
    seg_pred[mod] = g.groupby("segment").pred.mean()
# M0b map prior
pair = {"CPH1": "CPH6", "CPH6": "CPH1", "M3": "M13", "M13": "M3"}
med = SEG.groupby("route").y.median()
seg_pred["M0b map prior"] = SEG.route.map(lambda r: med[pair[r]])
# M7
PI = pd.read_csv(os.path.join(RR, "results", "v2", "physics_inversion_segments.csv"))
print("M7 file columns:", PI.columns.tolist()[:12], len(PI))
rows = [summ(p, k) for k, p in seg_pred.items()]
# zero-shot variants
VP = pd.read_csv(os.path.join(RR, "results", "v2", "variants_pass_predictions.csv.gz"))
VP["segment"] = U.segment.to_numpy()[VP.unit.to_numpy()]
for (vid, mod), g in VP.groupby(["vid", "model"]):
    if mod == "GBM":
        seg_pred["ZS " + vid] = g.groupby("segment").pred.mean()
        rows.append(summ(seg_pred["ZS " + vid], "ZS " + vid))
# untrained statistic
U["stat"] = U.a_rms / np.sqrt(U.v_mean)
seg_pred["untrained RMS/v^0.5"] = U.groupby("segment").stat.mean()
rows.append(summ(seg_pred["untrained RMS/v^0.5"] * 0 + seg_pred["untrained RMS/v^0.5"], "untrained RMS/v^0.5"))
T = pd.DataFrame(rows).set_index("name")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(T[["within_mae", "pooled_mae", "bias", "within_rho", "within_prho", "level_urban", "level_motorway",
         "relerr_urban", "relerr_motorway"]].round(3).to_string())
print(T[["mae_CPH1", "mae_CPH6", "mae_M3", "mae_M13"]].round(3).to_string())

# ---- ranking bound: |rho(model) - rho(untrained)| per route
ref = T.loc["untrained RMS/v^0.5"]
D = pd.DataFrame({R: T["rho_" + R] - ref["rho_" + R] for R in ROUTES})
D["max_abs"] = D.abs().max(1)
print("\nPer-route rho difference to the untrained statistic (model minus untrained):")
print(D.round(3).to_string())

# ---- 5 km block bootstrap of paired MAE differences (own implementation)
def boot(pa, pb, B=2000, seed=11, level="blk5"):
    d = SEG.assign(a=pa.reindex(SEG.index), b=pb.reindex(SEG.index))
    e = (np.abs(d.a - d.y) - np.abs(d.b - d.y)).to_numpy()
    cl = pd.factorize(d[level])[0] if level != "seg" else np.arange(len(d))
    C = cl.max() + 1
    s = np.bincount(cl, e, C); n = np.bincount(cl, minlength=C)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(C, np.ones(C) / C, size=B)
    bs = (W @ s) / (W @ n)
    return e.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5), C

REF = seg_pred["M3 LightGBM (all features)"]
for k in ["ZS V0", "ZS V10", "M4 MLP", "M5 1D-CNN", "M7", "M2c RMS/v^alpha (alpha fitted on training data)",
          "M1 speed-only (LightGBM on speed features)", "M0b map prior"]:
    if k == "M7":
        continue
    for lvl in ("blk5", "seg"):
        d0, lo, hi, C = boot(seg_pred[k], REF, level=lvl)
        print(f"diff {k:50s} - M3 [{lvl}]: {d0:+.3f} [{lo:+.3f}, {hi:+.3f}]  clusters={C}")

# ---- residual autocorrelation at 100 m and 1 km for the real GBM
e = (REF.reindex(SEG.index) - SEG.y)
for lag in (1, 10):
    a_, b_ = [], []
    for (r, dd), g in SEG.assign(e=e).groupby(["route", "direction"]):
        s = g.set_index("start").e
        nx = s.reindex(s.index + 100.0 * lag)
        ok = nx.notna().to_numpy()
        a_.append(s.to_numpy()[ok]); b_.append(nx.to_numpy()[ok])
    print(f"ACF lag {100 * lag} m: {np.corrcoef(np.concatenate(a_), np.concatenate(b_))[0, 1]:.3f}")

T.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "a02_table.csv"))
pd.to_pickle(seg_pred, os.path.join(os.path.dirname(os.path.abspath(__file__)), "a02_segpred.pkl"))
