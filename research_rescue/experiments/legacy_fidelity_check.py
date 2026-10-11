"""Fidelity check of the PyTorch legacy-recipe re-implementation.

Trains common/models_legacy.LegacyRecipe on the rejected paper's own cached tensors
(ml_model/iri_v2/output/iri_v2_data.npz) with the paper's split (train east+west, validation = test-track
trip 1, test = test-track trips 2-3) and compares with the published Run-1 5-seed numbers
(MAE 1.650, R^2 0.521 with isotonic calibration). This check uses the legacy protocol on purpose: its only
purpose is to show that later 'legacy recipe under a clean protocol' results are not artefacts of the
re-implementation.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.models_legacy import LegacyRecipe  # noqa: E402
from common.stats import metrics  # noqa: E402
from common.paths import LEGACY_V2_NPZ, RESULTS  # noqa: E402


def main():
    d = np.load(LEGACY_V2_NPZ)
    m = LegacyRecipe().fit(d["x_train_raw"], d["x_train_ctx"], d["y_train"], d["x_val_raw"], d["x_val_ctx"], d["y_val"])
    y = d["y_test"]
    cal = m.predict_seeds(d["x_test_raw"], d["x_test_ctx"], calibrated=True)
    raw = m.predict_seeds(d["x_test_raw"], d["x_test_ctx"], calibrated=False)
    rows = []
    for k in range(len(cal)):
        keep = raw[k] < 40.0
        rows.append(dict(seed=k, cal=metrics(y, cal[k]), raw=metrics(y, raw[k]),
                         raw_with_legacy_discard_rule=metrics(y[keep], raw[k][keep]), n_discarded=int((~keep).sum())))
    summ = {key: {s: float(np.mean([r[key][s] for r in rows])) for s in ("mae", "r2", "spearman")}
            for key in ("cal", "raw", "raw_with_legacy_discard_rule")}
    out = dict(published_run1=dict(mae=1.650, r2=0.521), reimplementation_mean=summ, per_seed=rows)
    json.dump(out, open(os.path.join(RESULTS, "legacy_fidelity_check.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1))
    print("n discarded per seed by the legacy >=40 rule:", [r["n_discarded"] for r in rows])


if __name__ == "__main__":
    main()
