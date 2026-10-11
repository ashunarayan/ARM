"""Review check 1 (read-only): does the zero-shot bias track the 10-15 Hz ratio specifically, or broadband gain?
Reads results/v2/summary_variants.csv and band_gain.csv; writes nothing into the repository."""
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr

R = sys.argv[1]  # path to research_rescue/results/v2
S = pd.read_csv(f"{R}/summary_variants.csv")
S = S[S.model == "GBM"].set_index("vid")
B = pd.read_csv(f"{R}/band_gain.csv")
P = B.pivot(index="vid", columns="feature", values="mean_log_ratio")
vids = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
T = pd.DataFrame({
    "bias": S.loc[vids, "bias"],
    "bias_urb": S.loc[vids, "bias_urban"],
    "bias_mot": S.loc[vids, "bias_motorway"],
    "mae": S.loc[vids, "mae"],
    "mae_within": S.loc[vids, "mae_within_mean"],
    "lvl5": S.loc[vids, "intercept_k5_mean"],
})
for f in P.columns:
    T["r_" + f.replace("log_", "")] = P.loc[vids, f]
pd.set_option("display.width", 200)
print(T.round(3).to_string())
print()
for f in P.columns:
    c = "r_" + f.replace("log_", "")
    rs = spearmanr(T[c], T.bias)[0]
    rp = pearsonr(T[c], T.bias)[0]
    print(f"{c:16s} Spearman with pooled bias {rs:+.3f}   Pearson {rp:+.3f}")
# leave-one-out sensitivity of the 10-15 Hz Spearman
print()
for v in vids:
    t = T.drop(v)
    print(f"drop {v}: Spearman(10-15) {spearmanr(t['r_band_10_15'], t.bias)[0]:+.3f}  Spearman(rms) {spearmanr(t['r_rms'], t.bias)[0]:+.3f}")
# simple linear fits: bias ~ ratio(10-15), residual of V4
x = T["r_band_10_15"].to_numpy(); y = T.bias.to_numpy()
b, a = np.polyfit(x, y, 1)
print()
print("OLS bias = a + b*lnratio(10-15):", round(a, 3), round(b, 3))
print((pd.Series(y - (a + b * x), index=vids)).round(3).to_string())
x2 = T["r_rms"].to_numpy(); b2, a2 = np.polyfit(x2, y, 1)
print("OLS bias = a + b*lnratio(rms):", round(a2, 3), round(b2, 3), " R2:", round(np.corrcoef(x2, y)[0, 1] ** 2, 3),
      " vs R2(10-15):", round(np.corrcoef(x, y)[0, 1] ** 2, 3))
print((pd.Series(y - (a2 + b2 * x2), index=vids)).round(3).to_string())
