"""Final-audit correction (review/final_audit/audit.md, issue B1): scope of the within-route ranking statement.

Point estimates only, derived from existing result files (no model is trained): for every real-data estimator of
Table S-routes and for LightGBM trained on each measured-profile variant V0-V8, the per-route within-route Spearman rho
minus that of the untrained statistic RMS/v^0.5 on the same segments.
Inputs: results/v2/summary_real_estimators.csv (real-data estimators; neural nets as 5-seed ensembles),
        results/v2/variants_zeroshot.csv (zero-shot LightGBM of every variant), results/v2/ranking_untrained.csv.
Check: for real-trained LightGBM, V0 and V1 the differences equal the point estimates of results/v3/rank_paired.csv.
Output: results/v3/rank_scope.csv (one row per estimator; `scope` = 1 for the estimators covered by the statement
"within rpAbsMax on every route": real-trained LightGBM, MLP, CNN, the quarter-car inversion M7 and simulation-trained
LightGBM V0-V8; 0 for M2c, LightGBM without speed inputs and the speed-only model).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v3 import OUT, RESCUE, MEAS, LIRA_ROUTES  # noqa: E402

V2 = os.path.join(RESCUE, "results", "v2")
REAL = {"M3 LightGBM": ("real-trained LightGBM", 1), "M4 MLP": ("MLP", 1), "M5 1D-CNN": ("1D-CNN", 1),
        "M7 quarter-car inversion": ("M7 quarter-car inversion", 1), "M2c vibration index": ("M2c vibration index", 0),
        "M3 LightGBM, no speed": ("LightGBM without speed inputs", 0), "M1 speed only": ("M1 speed only", 0)}


def main():
    RK = pd.read_csv(os.path.join(V2, "ranking_untrained.csv"))
    ref = RK[RK.statistic == "RMS/v^0.5"].set_index("route").rho
    E = pd.read_csv(os.path.join(V2, "summary_real_estimators.csv")).set_index("estimator")
    Z = pd.read_csv(os.path.join(V2, "variants_zeroshot.csv"))
    Z = Z[Z.model == "GBM"].set_index("vid")
    rows = []
    for est, (lab, scope) in REAL.items():
        rows.append(dict(estimator=lab, source="summary_real_estimators.csv", scope=scope,
                         **{f"d_{r}": float(E.loc[est, f"rho_{r}"] - ref[r]) for r in LIRA_ROUTES}))
    for v in MEAS:
        rows.append(dict(estimator=f"{v} LightGBM (zero-shot)", source="variants_zeroshot.csv", scope=1,
                         **{f"d_{r}": float(Z.loc[v, f"rho_{r}"] - ref[r]) for r in LIRA_ROUTES}))
    T = pd.DataFrame(rows)
    T["max_abs"] = T[[f"d_{r}" for r in LIRA_ROUTES]].abs().max(1)
    # consistency with the paired test (same segments, same statistic)
    RP = pd.read_csv(os.path.join(OUT, "rank_paired.csv"))
    RP = RP[(RP.metric == "rho") & RP["diff"].notna()]
    for lab, m in (("real-trained LightGBM", "real LightGBM"), ("V0 LightGBM (zero-shot)", "V0 LightGBM (zero-shot)"),
                   ("V1 LightGBM (zero-shot)", "V1 LightGBM (zero-shot)")):
        q = RP[RP.model == m].set_index("route")["diff"]
        for r in LIRA_ROUTES:
            x = float(T.loc[T.estimator == lab, f"d_{r}"].iloc[0])
            assert abs(x - q[r]) < 1e-6, (lab, r, x, q[r])
    T.to_csv(os.path.join(OUT, "rank_scope.csv"), index=False)
    with pd.option_context("display.width", 200):
        print(T.round(3).to_string(index=False))
    print("max |d| in scope:", round(float(T[T.scope == 1].max_abs.max()), 4))


if __name__ == "__main__":
    main()
