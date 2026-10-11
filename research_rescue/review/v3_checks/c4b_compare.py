"""Compare the pooled sim+real arm (r4_pooled.csv) with the paper's real_only (R4) and sim_all_cal (R3) on the same draws."""
import sys
import numpy as np
import pandas as pd

RR, POOL = sys.argv[1], sys.argv[2]


def pooled(D, keys):
    D = D.assign(w=D.seg_mae * D.n_seg, wb=D.seg_bias * D.n_seg)
    a = D.groupby(keys + ["draw"]).agg(w=("w", "sum"), wb=("wb", "sum"), n=("n_seg", "sum"), nf=("fold", "nunique")).reset_index()
    assert (a.nf == 4).all()
    a["mae"] = a.w / a.n; a["bias"] = a.wb / a.n
    return a


P = pooled(pd.read_csv(POOL), ["vid", "k_km"]).assign(arm="pooled")
R4 = pd.read_csv(f"{RR}/results/v2/value_of_simulation.csv")
real = pooled(R4[R4.arm == "real_only"], ["k_km"])[["k_km", "draw", "mae"]].rename(columns={"mae": "real"})
C = pd.read_csv(f"{RR}/results/v2/variants_calibration.csv")
C = C[(C.model == "GBM") & C.vid.isin(["V0", "V1", "V3", "V5"])]
cal = pooled(C[C.calib == "intercept"], ["vid", "k_km"])[["vid", "k_km", "draw", "mae"]].rename(columns={"mae": "lvl"})
aff = pooled(C[C.calib == "affine"], ["vid", "k_km"])[["vid", "k_km", "draw", "mae"]].rename(columns={"mae": "aff"})
M = P[["vid", "k_km", "draw", "mae", "bias"]].rename(columns={"mae": "pool", "bias": "pool_bias"})
M = M.merge(real, on=["k_km", "draw"]).merge(cal, on=["vid", "k_km", "draw"]).merge(aff, on=["vid", "k_km", "draw"])
rows = []
for (v, k), g in M.groupby(["vid", "k_km"]):
    rows.append(dict(vid=v, k=k, real=g.real.mean(), level=g.lvl.mean(), affine=g.aff.mean(), pooled=g.pool.mean(),
                     pool_minus_real=(g.pool - g.real).mean(), n_pool_better_real=int((g.pool < g.real).sum()),
                     pool_minus_level=(g.pool - g.lvl).mean(), n_pool_better_level=int((g.pool < g.lvl).sum()),
                     pool_bias=g.pool_bias.mean()))
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).round(3).to_string(index=False))
# per route at k=20 for the worst variants
Dp = pd.read_csv(POOL)
r4 = R4[R4.arm == "real_only"][["fold", "k_km", "draw", "seg_mae"]].rename(columns={"seg_mae": "real"})
q = Dp.merge(r4, on=["fold", "k_km", "draw"])
q["d"] = q.seg_mae - q.real
print("\nper route: pooled minus real_only (mean over draws, #pooled better)")
print(q.groupby(["vid", "k_km", "fold"]).agg(d=("d", "mean"), nb=("d", lambda x: int((x < 0).sum()))).unstack("fold").round(3).to_string())
