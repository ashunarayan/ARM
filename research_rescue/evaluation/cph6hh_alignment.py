"""Can LiRA-CD's CPH6-HH reported IRI be aligned with IRI recomputed from its own profile file?

For each (route, direction) the 10 m IRI recomputed from the P79 laser profile is correlated with the P79-reported
10 m IRI after shifting the reported series by -3000..+3000 m (10 m steps), with and without reversing its direction.
The maximum Pearson r over all shifts is reported per wheel path (results/iri_alignment_search.json). A consistent
file should peak near shift 0 with r ~ 1; this is the evidence behind excluding the reported CPH6-HH IRI
(labels are recomputed from the profile instead).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import lira  # noqa: E402
from common.paths import RESULTS  # noqa: E402
from evaluation.iri_unit_test import canonical_bins  # noqa: E402

STEP = 10.0
MAX_SHIFT = 3000.0


def best_alignment(rec: np.ndarray, rep: np.ndarray, min_overlap: int = 100):
    """rec, rep on the same 10 m grid (NaN where missing). Returns (best r, shift in m) over integer-bin shifts."""
    best = (-np.inf, 0.0)
    n = len(rec)
    for k in range(-int(MAX_SHIFT / STEP), int(MAX_SHIFT / STEP) + 1):
        a = rec[max(0, k):n + min(0, k)]
        b = rep[max(0, -k):n - max(0, k)]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < min_overlap:
            continue
        r = float(np.corrcoef(a[ok], b[ok])[0, 1])
        if r > best[0]:
            best = (r, k * STEP)
    return best


def main():
    out = {}
    for route, direction in [("CPH6", "HH"), ("CPH6", "VH"), ("CPH1", "HH")]:     # the inconsistent file + two controls
        zp = lira.load_zp(route, direction); ref = lira.load_p79_iri(route, direction)
        lo = np.floor(min(zp.dist.min(), ref.dist.min()) / STEP) * STEP
        hi = np.ceil(max(zp.dist.max(), ref.dist.max()) / STEP) * STEP
        grid = np.arange(lo, hi, STEP)
        rec = canonical_bins(zp, grid, STEP, 0.1)
        res = {}
        for side in ["left", "right"]:
            rep = np.full(len(grid), np.nan)
            idx = np.round((ref.dist.to_numpy() - lo) / STEP).astype(int)
            ok = (idx >= 0) & (idx < len(grid))
            rep[idx[ok]] = ref[f"iri_{side}"].to_numpy()[ok]
            r_fwd, s_fwd = best_alignment(rec[side], rep)
            r_rev, s_rev = best_alignment(rec[side], rep[::-1].copy())
            ok0 = np.isfinite(rec[side]) & np.isfinite(rep)
            r0 = float(np.corrcoef(rec[side][ok0], rep[ok0])[0, 1]) if ok0.sum() > 10 else float("nan")
            res[side] = dict(r_at_zero_shift=r0, best_r_forward=r_fwd, best_shift_forward_m=s_fwd,
                             best_r_reversed=r_rev, best_shift_reversed_m=s_rev)
        out[f"{route}_{direction}"] = res
        print(route, direction, json.dumps(res), flush=True)
    json.dump(out, open(os.path.join(RESULTS, "iri_alignment_search.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
