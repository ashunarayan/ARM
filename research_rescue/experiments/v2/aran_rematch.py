"""Revision v2, R9: ARAN9000 vs P79 agreement with a validated alignment (PROTOCOL_V2.md, Section 4).

Differences to v1 (evaluation/iri_unit_test.py): every ARAN record is matched to the P79 track of the same direction
with a heading constraint (ARAN 'Heading' column, compass degrees; tolerance 60 deg), records with zero or negative IRI
(invalid) are excluded, and the comparison is reported per route. ARAN 100 m values = mean of the matched records'
mean wheel-path IRI (>= 5 records). Reference: P79 IRI recomputed from the P79 profile (v1 labels).
Note: ARAN surveys 12-08-2020 (CPH1, M3, M13) and 30-08-2021 (CPH6); P79 survey 10-09-2020 (LiRA-CD paper).
Output: results/v2/aran_rematch.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, LIRA_ROUTES  # noqa: E402
from common import lira, geo  # noqa: E402
from common.paths import PROCESSED, LIRA_REF, LIRA_DIRS  # noqa: E402


def main():
    seg = pd.read_csv(os.path.join(PROCESSED, "lira", "p79_segments_100m.csv"))
    rows, per = [], []
    for route in LIRA_ROUTES:
        for d in LIRA_DIRS:
            zp = lira.load_zp(route, d)
            lat0, lon0 = zp.lat.median(), zp.lon.median()
            pl = geo.Polyline(geo.to_local_xy(zp.lat.to_numpy(), zp.lon.to_numpy(), lat0, lon0)[::10], zp.dist.to_numpy()[::10])
            raw = pd.read_csv(os.path.join(LIRA_REF, f"{route.lower()}_aran_{d.lower()}.csv"), sep=";", encoding="latin-1")
            raw.columns = [c.strip() for c in raw.columns]
            iri_cols = [c for c in raw.columns if "IRI" in c]
            a = pd.DataFrame(dict(lat=pd.to_numeric(raw.Lat, errors="coerce"), lon=pd.to_numeric(raw.Lon, errors="coerce"),
                                  head=pd.to_numeric(raw.Heading, errors="coerce"),
                                  il=pd.to_numeric(raw[iri_cols[0]], errors="coerce"), ir=pd.to_numeric(raw[iri_cols[1]], errors="coerce"))).dropna()
            n0 = len(a)
            a = a[(a.il > 0) & (a.ir > 0)]
            xy = geo.to_local_xy(a.lat.to_numpy(), a.lon.to_numpy(), lat0, lon0)
            ch, dist = pl.match(xy, heading=np.deg2rad(90.0 - a["head"].to_numpy()))
            a = a.assign(ch=ch, dist=dist)
            a = a[np.isfinite(a.dist) & (a.dist < 10)]
            s = seg[(seg.route == route) & (seg.direction == d)]
            for st, y in zip(s.start_m, s.mri_profile):
                w = a[(a.ch >= st) & (a.ch < st + 100)]
                if len(w) >= 5 and np.isfinite(y):
                    per.append(dict(route=route, direction=d, start_m=st, p79=y, aran=float(0.5 * (w.il + w.ir).mean())))
            rows.append(dict(route=route, direction=d, n_records=n0, n_valid_matched=len(a)))
    P = pd.DataFrame(per)
    out = []
    for scope, g in [("all", P)] + [(r, g) for r, g in P.groupby("route")] + \
                    [("urban", P[P.route.str.startswith("CPH")]), ("motorway", P[P.route.str.startswith("M")])]:
        e = g.aran - g.p79
        out.append(dict(scope=scope, n_segments=len(g), mae=float(np.mean(np.abs(e))), bias=float(np.mean(e)),
                        pearson=float(np.corrcoef(g.aran, g.p79)[0, 1]), spearman=float(spearmanr(g.aran, g.p79)[0]),
                        median_ratio=float(np.median(g.aran / g.p79)), share_above_15=float(np.mean(g.aran > 15))))
    T = pd.DataFrame(out)
    T.to_csv(os.path.join(OUT, "aran_rematch.csv"), index=False)
    P.to_csv(os.path.join(OUT, "aran_rematch_segments.csv"), index=False)
    print(pd.DataFrame(rows).to_string(index=False)); print(T.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
