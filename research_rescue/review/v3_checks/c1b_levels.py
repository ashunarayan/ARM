"""Per-route log level (mean log(p/y)) of each variant and of the real-trained model; band association in log terms."""
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

R = sys.argv[1]
S = pd.read_csv(f"{R}/variants_zeroshot.csv")
S = S[S.model == "GBM"].set_index("vid")
cols = ["level_CPH1", "level_CPH6", "level_M3", "level_M13"]
T = S.loc[["REAL", "V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10"], cols + ["bias_urban", "bias_motorway", "bias"]].copy()
T["lvl_urban"] = T[["level_CPH1", "level_CPH6"]].mean(1); T["lvl_motorway"] = T[["level_M3", "level_M13"]].mean(1)
T["lvl_mean"] = T[cols].mean(1); T["lvl_spread"] = T.lvl_motorway - T.lvl_urban
pd.set_option("display.width", 220)
print(T.round(3).to_string())
B = pd.read_csv(f"{R}/band_gain.csv").pivot(index="vid", columns="feature", values="mean_log_ratio")
v = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
for f in B.columns:
    print(f"{f:16s} Spearman with mean log level {spearmanr(B.loc[v, f], T.loc[v, 'lvl_mean'])[0]:+.3f}  "
          f"with urban/motorway level spread {spearmanr(B.loc[v, f], T.loc[v, 'lvl_spread'])[0]:+.3f}")
