"""Revision v2, E4 (class E): band-level gain/offset between real and simulated vibration (PROTOCOL_V2.md, Section 5).

For each simulator variant and each vibration feature (log RMS and the four log band RMS features), cell means over
(segment x 10 km/h speed band) are computed for the real units and for the variant's simulated units on the same
segments; OLS real = a + b * sim over common cells gives the offset at the median sim level and the slope b
(b = 1: pure gain difference; b < 1: compressed dynamic range). Output: results/v2/band_gain.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, FI, load_lira, variant_training_set  # noqa: E402

FEATS = ["log_rms", "log_band_0.5_2", "log_band_2_5", "log_band_5_10", "log_band_10_15"]


def cells(seg, v, X):
    key = pd.Series(seg).astype(str) + "|" + pd.Series((v * 3.6 // 10).astype(int)).astype(str)
    return pd.DataFrame(X, columns=FEATS).assign(key=key.to_numpy()).groupby("key").mean()


def main():
    U, F = load_lira()
    real = cells(U.segment.to_numpy(), U.v_mean.to_numpy(), F[:, [FI[f] for f in FEATS]])
    rows = []
    for vid in ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9"]:
        m, X, _ = variant_training_set(vid, None)
        if "direction" not in m or vid == "V9":
            continue                                        # synthetic profiles have no real counterpart segments
        seg = (m.route + "_" + m.direction + "_" + m.start_m.astype(int).astype(str)).to_numpy()
        sim = cells(seg, m.v_mean.to_numpy(), X[:, [FI[f] for f in FEATS]])
        common = real.index.intersection(sim.index)
        for f in FEATS:
            r, s = real.loc[common, f].to_numpy(), sim.loc[common, f].to_numpy()
            b, a = np.polyfit(s, r, 1)
            rows.append(dict(vid=vid, feature=f, n_cells=len(common), mean_log_ratio=float(np.mean(r - s)),
                             ratio=float(np.exp(np.mean(r - s))), slope=float(b),
                             offset_at_median=float(a + (b - 1) * np.median(s)), corr=float(np.corrcoef(r, s)[0, 1])))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "band_gain.csv"), index=False)
    print(T.pivot(index="vid", columns="feature", values="ratio").round(2).to_string())
    print(T.pivot(index="vid", columns="feature", values="slope").round(2).to_string())


def by_class():
    """Same comparison split by road class (urban: CPH1, CPH6; motorway: M3, M13). Diagnostic (E4, class E).
    Output: results/v2/band_gain_by_class.csv"""
    from common_v2 import CLASS
    U, F = load_lira()
    rows = []
    for cls in ("urban", "motorway"):
        u = (U.route.map(CLASS) == cls).to_numpy()
        real = cells(U.segment.to_numpy()[u], U.v_mean.to_numpy()[u], F[u][:, [FI[f] for f in FEATS]])
        for vid in ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]:
            m, X, _ = variant_training_set(vid, None)
            s_ = (m.route.map(CLASS) == cls).to_numpy()
            m, X = m[s_], X[s_]
            seg = (m.route + "_" + m.direction + "_" + m.start_m.astype(int).astype(str)).to_numpy()
            sim = cells(seg, m.v_mean.to_numpy(), X[:, [FI[f] for f in FEATS]])
            common = real.index.intersection(sim.index)
            for f in FEATS:
                r, s = real.loc[common, f].to_numpy(), sim.loc[common, f].to_numpy()
                rows.append(dict(cls=cls, vid=vid, feature=f, n_cells=len(common), mean_log_ratio=float(np.mean(r - s)),
                                 ratio=float(np.exp(np.mean(r - s)))))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "band_gain_by_class.csv"), index=False)
    print(T[T.feature == "log_band_10_15"].pivot(index="vid", columns="cls", values="ratio").round(2).to_string())
    print(T[T.feature == "log_rms"].pivot(index="vid", columns="cls", values="ratio").round(2).to_string())


if __name__ == "__main__":
    if sys.argv[1:] == ["by_class"]:
        by_class()
    else:
        main()
