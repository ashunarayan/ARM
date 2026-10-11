"""Revision v2, E10 (PROTOCOL_V2.md, Section 8): within-route ranking by untrained vibration statistics.

Spearman correlation within a route is invariant to monotone calibration, so a fixed statistic such as RMS/v^0.5
ranks segments without any training data. Its within-route Spearman (and partial Spearman given segment speed) is the
part of the ranking that needs no learning. Computed like the estimators' metrics: segment means of the pass values
(seg_table), per held-out route, averaged over the four routes. Output: results/v2/ranking_untrained.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, LIRA_ROUTES, load_lira, seg_table, partial_spearman  # noqa: E402


def main():
    U, _ = load_lira()
    rms, v = U.a_rms.to_numpy(), U.v_mean.to_numpy()
    stats = {"raw RMS": rms, "RMS/v^0.5": rms / np.sqrt(v), "RMS/v": rms / v}
    rows = []
    for name, x in stats.items():
        for R in LIRA_ROUTES:
            te = np.where(U.route == R)[0]
            S = seg_table(U, te, x[te])
            rows.append(dict(statistic=name, route=R, n_seg=len(S), rho=spearmanr(S.p, S.y)[0],
                             prho=partial_spearman(S.p.to_numpy(), S.y.to_numpy(), S.v.to_numpy())))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "ranking_untrained.csv"), index=False)
    print(T.round(3).to_string())
    print(T.groupby("statistic")[["rho", "prho"]].mean().round(3))


if __name__ == "__main__":
    main()
