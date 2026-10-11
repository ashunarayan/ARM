"""Are the four LiRA-CD routes spatially disjoint? For every 100 m segment (P79 GPS at the segment start), the distance
to the nearest segment start of each OTHER route is computed; segments closer than 15 m (and 30 m) are counted.
Leave-one-route-out is only route-disjoint if these counts are ~0 (results/route_overlap.json)."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.paths import PROCESSED, RESULTS  # noqa: E402
from common.geo import to_local_xy  # noqa: E402


def main():
    seg = pd.read_csv(os.path.join(PROCESSED, "lira", "p79_segments_100m.csv")).dropna(subset=["lat", "lon"])
    U = pd.read_csv(os.path.join(PROCESSED, "lira", "units.csv"))
    used = set(U.segment)
    seg["segment"] = seg.route + "_" + seg.direction + "_" + seg.start_m.astype(int).astype(str)
    seg = seg[seg.segment.isin(used)]
    lat0, lon0 = seg.lat.median(), seg.lon.median()
    xy = to_local_xy(seg.lat.to_numpy(), seg.lon.to_numpy(), lat0, lon0)
    seg["x"], seg["y"] = xy[:, 0], xy[:, 1]
    out = {}
    for r in sorted(seg.route.unique()):
        a = seg[seg.route == r]
        b = seg[seg.route != r]
        d, j = cKDTree(b[["x", "y"]].to_numpy()).query(a[["x", "y"]].to_numpy())
        out[r] = dict(n_segments=int(len(a)), within_15m=int((d < 15).sum()), within_30m=int((d < 30).sum()),
                      nearest_other_route_m_median=float(np.median(d)),
                      routes_within_30m=sorted(set(b.route.to_numpy()[j[d < 30]].tolist())))
    out["total_segments"] = int(len(seg)); out["total_within_15m"] = int(sum(v["within_15m"] for k, v in out.items() if isinstance(v, dict)))
    json.dump(out, open(os.path.join(RESULTS, "route_overlap.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
