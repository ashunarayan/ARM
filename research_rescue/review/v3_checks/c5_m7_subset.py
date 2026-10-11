"""Why is M7 evaluated on 119 of 228 M13 segments? Compare the M13 segments with/without an acceleration PSD and with/
without a profile spectrum; report IRI and speed of the excluded vs included segments and real LightGBM error on both."""
import sys
import numpy as np
import pandas as pd

RR = sys.argv[1]
U = pd.read_csv(f"{RR}/data/processed/lira/units.csv")
psd = np.load(f"{RR}/data/processed/v2/spectra_real.npz")["psd50"].astype(float)
seg = pd.read_csv(f"{RR}/results/v2/physics_inversion_segments.csv")
m7 = set(seg[(seg.fold == "M13") & seg.model.str.startswith("M7 ")].segment)
u = U[U.route == "M13"].copy()
u["has_psd"] = np.isfinite(psd[U.route.to_numpy() == "M13"]).all(1)
g = u.groupby("segment").agg(y=("mri", "first"), v=("v_mean", "mean"), dur=("dur_s", "mean"), n=("mri", "size"),
                             psd_share=("has_psd", "mean"), direction=("direction", "first"), start=("start_m", "first"))
g["in_m7"] = g.index.isin(m7)
print(g.groupby("in_m7").agg(n_seg=("y", "size"), iri_mean=("y", "mean"), v_kmh=("v", lambda x: 3.6 * x.mean()),
                             dur_s=("dur", "mean"), psd_share=("psd_share", "mean")).round(3))
print(g.groupby(["direction", "in_m7"]).size())
# real-trained LightGBM error on included vs excluded M13 segments
lad = pd.read_csv(f"{RR}/results/predictions/lira_ladder.csv")
P = lad[(lad.model == "M3 LightGBM (all features)") & (lad.fold == "M13")]
te = np.where(U.route.to_numpy() == "M13")[0]
assert len(P) == len(te)
d = pd.DataFrame(dict(segment=U.segment.to_numpy()[te], y=U.mri.to_numpy()[te], p=P.pred.to_numpy()))
s = d.groupby("segment").agg(y=("y", "first"), p=("p", "mean"))
s["in_m7"] = s.index.isin(m7)
s["ae"] = (s.p - s.y).abs()
print("real LightGBM MAE on M13 by M7 inclusion:\n", s.groupby("in_m7").ae.mean().round(3))
print("M7 MAE on its 119:", round(seg[(seg.fold == "M13") & seg.model.str.startswith("M7 ")].eval("abs(p-y)").mean(), 3))
print("units: total M13", len(te), " with psd:", int(u.has_psd.sum()))
