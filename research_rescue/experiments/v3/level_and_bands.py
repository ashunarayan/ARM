"""Revision v3, items V3-4 and V3-5 (evaluation/PROTOCOL_V3.md): band associations (E) and level decomposition (R).

V3-5: per variant (V0-V10 and the real-trained model), the urban, motorway and mean log level (mean over segments of
log(prediction / label), averaged over the routes of a class) and the motorway-minus-urban spread, from the `level_*`
columns of results/v2/variants_zeroshot.csv; next to the pooled and within-route MAE after a 5 km level offset
(results/v2/variants_calibration.csv, 20 draws).
V3-4: over V0-V8, Spearman and Pearson correlations and the R^2 of a linear fit between the log real/simulated
amplitude ratio of each feature in results/v2/band_gain.csv and (i) the pooled zero-shot bias, (ii) the mean log
level, (iii) the class spread; all features reported.
Outputs: results/v3/level_decomposition.csv, results/v3/band_associations.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v3 import OUT, RESCUE, MEAS  # noqa: E402

V2 = os.path.join(RESCUE, "results", "v2")


def main():
    Z = pd.read_csv(os.path.join(V2, "variants_zeroshot.csv")); Z = Z[Z.model == "GBM"].set_index("vid")
    C = pd.read_csv(os.path.join(V2, "variants_calibration.csv"))
    C = C[(C.model == "GBM") & (C.calib == "intercept") & (C.k_km == 5)]
    C = C.assign(w=C.seg_mae * C.n_seg)
    pooled5 = (C.groupby(["vid", "draw"]).w.sum() / C.groupby(["vid", "draw"]).n_seg.sum()).groupby("vid").mean()
    within5 = C.groupby(["vid", "draw"]).seg_mae.mean().groupby("vid").mean()
    rows = []
    for v in ["REAL"] + MEAS + ["V9", "V10"]:
        r = Z.loc[v]
        u, m = np.mean([r.level_CPH1, r.level_CPH6]), np.mean([r.level_M3, r.level_M13])
        rows.append(dict(vid=v, lvl_urban=u, lvl_motorway=m, lvl_mean=np.mean([r.level_CPH1, r.level_CPH6, r.level_M3, r.level_M13]),
                         spread=m - u, pct_urban=100 * (np.exp(u) - 1), pct_motorway=100 * (np.exp(m) - 1),
                         bias=r.bias, mae=r.mae, mae_within=r.mae_within_mean,
                         mae_level5km=pooled5.get(v, np.nan), mae_within_level5km=within5.get(v, np.nan)))
    L = pd.DataFrame(rows)
    L.to_csv(os.path.join(OUT, "level_decomposition.csv"), index=False)
    Lm = L.set_index("vid").loc[MEAS]
    print(L.round(3).to_string(index=False))
    print("Spearman over V0-V8, class spread vs pooled MAE after a 5 km offset:",
          round(spearmanr(Lm.spread, Lm.mae_level5km)[0], 3))

    B = pd.read_csv(os.path.join(V2, "band_gain.csv"))
    out = []
    for f, g in B.groupby("feature"):
        g = g.set_index("vid").loc[MEAS]
        x = np.log(g.ratio.to_numpy())
        for target in ("bias", "lvl_mean", "spread"):
            yv = Lm[target].to_numpy()
            b, a = np.polyfit(x, yv, 1)
            r2 = 1 - np.sum((yv - (a + b * x)) ** 2) / np.sum((yv - yv.mean()) ** 2)
            out.append(dict(feature=f, target=target, spearman=spearmanr(x, yv)[0], pearson=pearsonr(x, yv)[0], r2=r2,
                            slope=b, n=len(x)))
    A = pd.DataFrame(out)
    A.to_csv(os.path.join(OUT, "band_associations.csv"), index=False)
    print(A.round(3).to_string(index=False))
    # residuals of the bias fit on the 10-15 Hz ratio and on the overall RMS ratio (which variant departs most)
    for f in ("log_band_10_15", "log_rms"):
        g = B[B.feature == f].set_index("vid").loc[MEAS]
        x = np.log(g.ratio.to_numpy()); yv = Lm.bias.to_numpy(); b, a = np.polyfit(x, yv, 1)
        print(f, "residuals:", dict(zip(MEAS, np.round(yv - (a + b * x), 3))))


if __name__ == "__main__":
    main()
