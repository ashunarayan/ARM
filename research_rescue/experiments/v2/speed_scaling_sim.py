"""Revision v2, E7 (PROTOCOL_V2.md, Section 8): speed scaling of the raw vibration, simulation vs real car.

Within-segment elasticity of log RMS (feature `log_rms`) on log mean speed with segment fixed effects, by road class,
for the real LiRA-CD units and for the simulated units of every measured-profile variant on the same segments.
Simulated passes are restricted to the speed range [min, max] of the real passes over the same segment, so both
slopes are local to the speeds actually driven. Segments with < 3 units are dropped. 95 % interval: bootstrap over
5 km blocks (2000 resamples). Output: results/v2/speed_scaling_sim.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, FI, CLASS, load_lira, variant_training_set, block_id  # noqa: E402

B = 2000


def elasticity(d, seed=0):
    d = d[d.groupby("s").s.transform("size") >= 3].copy()
    d["xc"] = d.x - d.groupby("s").x.transform("mean"); d["yc"] = d.y - d.groupby("s").y.transform("mean")
    blk = pd.factorize(d.b)[0]; C = blk.max() + 1
    sxy = np.bincount(blk, weights=d.xc * d.yc, minlength=C); sxx = np.bincount(blk, weights=d.xc ** 2, minlength=C)
    rng = np.random.default_rng(seed)
    bs = [(w @ sxy) / (w @ sxx) for w in (np.bincount(rng.integers(0, C, C), minlength=C) for _ in range(B))]
    return dict(elasticity=sxy.sum() / sxx.sum(), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5),
                n_segments=d.s.nunique(), n_units=len(d), n_blocks=C, median_sd_logv=float(d.groupby("s").x.std().median()))


def main():
    U, F = load_lira()
    R = pd.DataFrame(dict(s=U.segment.to_numpy(), x=np.log(U.v_mean.to_numpy()), y=F[:, FI["log_rms"]], cls=U.cls.to_numpy(),
                          b=U.block5.to_numpy()))
    rng_seg = R.groupby("s").x.agg(["min", "max"])
    rows = []
    for cls in ("urban", "motorway"):
        rows.append(dict(source="real", cls=cls, **elasticity(R[R.cls == cls])))
    for vid in ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]:
        m, X, _ = variant_training_set(vid, None)
        seg = (m.route + "_" + m.direction + "_" + m.start_m.astype(int).astype(str)).to_numpy()
        D = pd.DataFrame(dict(s=seg, x=np.log(m.v_mean.to_numpy()), y=X[:, FI["log_rms"]], cls=m.route.map(CLASS).to_numpy(),
                              b=block_id(m, 5000).to_numpy())).join(rng_seg, on="s")
        D = D[(D.x >= D["min"]) & (D.x <= D["max"])]
        for cls in ("urban", "motorway"):
            rows.append(dict(source=vid, cls=cls, **elasticity(D[D.cls == cls])))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "speed_scaling_sim.csv"), index=False)
    print(T.round(3).to_string())


if __name__ == "__main__":
    main()
