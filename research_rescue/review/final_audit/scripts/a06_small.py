"""Audit step 6: small checks (definitions, data facts, speed elasticities)."""
import os
import numpy as np
import pandas as pd

RR = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue"
HERE = os.path.dirname(os.path.abspath(__file__))
ROUTES = ["CPH1", "CPH6", "M3", "M13"]
EPS = 1e-3
U = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "units.csv"))
seg_pred = pd.read_pickle(os.path.join(HERE, "a02_segpred.pkl"))
SEG = U.groupby("segment").agg(route=("route", "first"), y=("mri", "first"))

# 1. class level: segment-pooled vs mean of the two route levels
print("1. class levels (seg-pooled | mean of route levels):")
for k in ["M3 LightGBM (all features)"] + [f"ZS V{i}" for i in range(9)]:
    d = SEG.assign(p=seg_pred[k].reindex(SEG.index))
    d["l"] = np.log((d.p + EPS) / (d.y + EPS))
    rl = d.groupby("route").l.mean()
    pooled_u = d[d.route.isin(["CPH1", "CPH6"])].l.mean(); pooled_m = d[d.route.isin(["M3", "M13"])].l.mean()
    print(f"   {k:28s} urban {pooled_u:+.3f} | {(rl.CPH1 + rl.CPH6) / 2:+.3f}   motorway {pooled_m:+.3f} | {(rl.M3 + rl.M13) / 2:+.3f}"
          f"   spread(route-mean) {(rl.M3 + rl.M13) / 2 - (rl.CPH1 + rl.CPH6) / 2:.3f}")

# 2. which variants have the largest 10-15 Hz deficit
BG = pd.read_csv(os.path.join(RR, "results", "v2", "band_gain.csv"))
print("\n2. band_gain.csv columns:", BG.columns.tolist()[:14])
print(BG.head(12).to_string())

# 3. data facts
print("\n3. telematics units:", U.unit.value_counts().to_dict())
P = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "p79_segments_100m.csv"))
ok = P.consistent_reported.astype(bool) & P.mri_reported.notna() & P.mri_profile.notna()
print("   P79 label validation over all P79 segments: n=%d r=%.4f" % (ok.sum(), np.corrcoef(P.mri_profile[ok], P.mri_reported[ok])[0, 1]))

# 4. fixed-road speed elasticity of the raw RMS (real car): slope of log a_rms on log v with segment fixed effects
def fe_slope(df, ycol, xcol="lv"):
    g = df.groupby("segment")
    yd = df[ycol] - g[ycol].transform("mean"); xd = df[xcol] - g[xcol].transform("mean")
    return float((xd * yd).sum() / (xd * xd).sum())

U["lv"] = np.log(U.v_mean); U["lr"] = np.log(U.a_rms)
U["cls"] = U.route.map({"CPH1": "urban", "CPH6": "urban", "M3": "motorway", "M13": "motorway"})
print("\n4. raw RMS elasticity: pooled %.3f, urban %.3f, motorway %.3f" % (fe_slope(U, "lr"), fe_slope(U[U.cls == "urban"], "lr"),
                                                                       fe_slope(U[U.cls == "motorway"], "lr")))
print("   median within-segment SD of log speed: %.3f" % U.groupby("segment").lv.std().median())
# estimator elasticities: real M3 (positional alignment of the ladder file) and V0 zero-shot
L = pd.read_csv(os.path.join(RR, "results", "predictions", "lira_ladder.csv.gz"))
L = L[L.model == "M3 LightGBM (all features)"]
pr = np.full(len(U), np.nan)
for fold, d in L.groupby("fold", sort=False):
    te = np.where(U.route.to_numpy() == fold)[0]
    assert len(d) == len(te) and np.allclose(d.y.to_numpy(), U.mri.to_numpy()[te])
    pr[te] = d.pred.to_numpy()
VP = pd.read_csv(os.path.join(RR, "results", "v2", "variants_pass_predictions.csv.gz"))
q = VP[(VP.vid == "V0") & (VP.model == "GBM")]
pz = np.full(len(U), np.nan); pz[q.unit.to_numpy()] = q.pred.to_numpy()
U["lp_real"] = np.log(pr + EPS); U["lp_v0"] = np.log(pz + EPS); U["dlp"] = U.lp_v0 - U.lp_real
for c in ("all", "urban", "motorway"):
    d = U if c == "all" else U[U.cls == c]
    print(f"   {c:8s} real GBM {fe_slope(d, 'lp_real'):+.3f}  V0 {fe_slope(d, 'lp_v0'):+.3f}  paired V0-real {fe_slope(d, 'dlp'):+.3f}")
print("   %% change 40->100 km/h for elasticity e: e=0.66 -> %+.0f%%, e=-0.15 -> %+.0f%%, e=-0.06 -> %+.0f%%" % (
    100 * (2.5 ** 0.66 - 1), 100 * (2.5 ** -0.15 - 1), 100 * (2.5 ** -0.06 - 1)))
