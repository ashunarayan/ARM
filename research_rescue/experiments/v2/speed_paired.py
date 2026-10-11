"""Revision v2, E8 (PROTOCOL_V2.md, Section 8): paired speed-elasticity differences on real roads.

For a simulation-trained estimator s and the real-trained estimator r of the same family, the difference of their
within-segment elasticities equals the within-segment slope of log(p_s / p_r) on log speed (same passes, same
segments), so a paired interval follows from the same block bootstrap. 5 km blocks (the inference rule of the
protocol). Output: results/v2/speed_paired.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, EPS, load_lira  # noqa: E402
from speed_real import pass_predictions, within_elasticity  # noqa: E402


def main():
    U, _ = load_lira()
    P = pass_predictions(U)
    lv = np.log(U.v_mean.to_numpy())
    rows = []
    pairs = [(k, "REAL_GBM") for k in P if k.startswith("SIM_") and k.endswith("_GBM")] + \
            [(k, "REAL_INDEX") for k in P if k.startswith("SIM_") and k.endswith("_INDEX")]
    for s, r in pairs:
        d = np.log(np.asarray(P[s], float) + EPS) - np.log(np.asarray(P[r], float) + EPS)
        for scope, m in (("pooled", np.ones(len(U), bool)), ("urban", (U.cls == "urban").to_numpy()),
                         ("motorway", (U.cls == "motorway").to_numpy())):
            ok = m & np.isfinite(d)
            b, lo, hi, nseg, _ = within_elasticity(d[ok], lv[ok], U.segment.to_numpy()[ok], U.block5.to_numpy()[ok])
            rows.append(dict(model=s, reference=r, scope=scope, diff_elasticity=b, lo=lo, hi=hi, n_segments=nseg))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "speed_paired.csv"), index=False)
    print(T.round(3).to_string())


if __name__ == "__main__":
    main()
