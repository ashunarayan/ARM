"""BeamNG unseen-vehicle effect from saved predictions: S1 (vehicle seen, map unseen) vs S2 (vehicle and map unseen)
on the identical evaluation segments (label iri_raw). Paired cluster bootstrap over location cells.
Output: results/beamng/seen_vs_unseen_vehicle.csv"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.stats import paired_diff, metrics  # noqa: E402
from common.paths import RESULTS  # noqa: E402


def load(p):
    P = pd.read_csv(os.path.join(RESULTS, "predictions", p))
    return P.groupby(["model", "unit_id"]).agg(pred=("pred", "mean"), y=("y", "first"), cluster=("cluster", "first")).reset_index()


def main():
    S1, S2 = load("beamng_S1_iri_raw.csv"), load("beamng_S2_iri_raw.csv")
    rows = []
    for m in sorted(set(S1.model) & set(S2.model)):
        a = S1[S1.model == m].set_index("unit_id"); b = S2[S2.model == m].set_index("unit_id")
        j = a.join(b, lsuffix="_seen", rsuffix="_unseen", how="inner")
        d = paired_diff(j.y_seen.to_numpy(), j.pred_unseen.to_numpy(), j.pred_seen.to_numpy(), j.cluster_seen.to_numpy(), "mae", B=2000)
        ms, mu = metrics(j.y_seen, j.pred_seen)["mae"], metrics(j.y_seen, j.pred_unseen)["mae"]
        rows.append(dict(model=m, n_segments=len(j), mae_vehicle_seen=ms, mae_vehicle_unseen=mu, diff=d["diff"], lo=d["lo"], hi=d["hi"],
                         rel=d["diff"] / ms, rel_hi=d["hi"] / ms, generalises=bool(d["hi"] / ms <= 0.10)))
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(RESULTS, "beamng", "seen_vs_unseen_vehicle.csv"), index=False)
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
