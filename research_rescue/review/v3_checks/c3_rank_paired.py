"""Review check 3 (read-only): is "an untrained RMS/v^0.5 ranks segments within routes as well as any trained model"
supported by a paired test? Within-route Spearman of segment means (as in the paper), paired differences
trained-minus-untrained per route and averaged over routes, block bootstrap within route (5 km and 1 km blocks)."""
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata

RR = sys.argv[1]
ROUTES = ["CPH1", "CPH6", "M3", "M13"]


def block_id(df, L):
    return df.route.astype(str) + "_" + df.direction.astype(str) + "_" + (df.start_m // L).astype(int).astype(str)


U = pd.read_csv(f"{RR}/data/processed/lira/units.csv")
U["b5"] = block_id(U, 5000); U["b1"] = block_id(U, 1000)
lad = pd.read_csv(f"{RR}/results/predictions/lira_ladder.csv")


def ladder_pred(model):
    P = lad[lad.model == model]
    out = np.full(len(U), np.nan)
    for fold, d in P.groupby("fold", sort=False):
        te = np.where(U.route.to_numpy() == fold)[0]
        ds = d[d.seed == d.seed.min()]
        assert len(ds) == len(te) and np.allclose(ds.y.to_numpy(), U.mri.to_numpy()[te])
        out[te] = ds.pred.to_numpy()
    return out


VP = pd.read_csv(f"{RR}/results/v2/variants_pass_predictions.csv.gz")


def variant_pred(vid, model="GBM"):
    q = VP[(VP.vid == vid) & (VP.model == model)]
    out = np.full(len(U), np.nan); out[q.unit.to_numpy()] = q.pred.to_numpy(); return out


preds = {"real GBM": ladder_pred("M3 LightGBM (all features)"),
         "real MLP": None,
         "sim V0 GBM": variant_pred("V0"), "sim V1 GBM": variant_pred("V1"),
         "untrained RMS/v^0.5": U.a_rms.to_numpy() / np.sqrt(U.v_mean.to_numpy())}
preds.pop("real MLP")
S = pd.DataFrame(dict(segment=U.segment, route=U.route, b5=U.b5, b1=U.b1, y=U.mri, v=U.v_mean, **preds))
G = S.groupby("segment").agg(route=("route", "first"), b5=("b5", "first"), b1=("b1", "first"), y=("y", "first"),
                             v=("v", "mean"), **{k: (k, "mean") for k in preds}).reset_index()


def rho(d, k):
    return spearmanr(d[k], d.y)[0]


def prho(d, k):
    rx, ry, rz = rankdata(d[k]), rankdata(d.y), rankdata(d.v)
    Z = np.column_stack([np.ones_like(rz), rz])
    ex = rx - Z @ np.linalg.lstsq(Z, rx, rcond=None)[0]; ey = ry - Z @ np.linalg.lstsq(Z, ry, rcond=None)[0]
    return float(np.corrcoef(ex, ey)[0, 1])


ref = "untrained RMS/v^0.5"
comps = ["real GBM", "sim V0 GBM", "sim V1 GBM"]
rng = np.random.default_rng(2026)
B = 2000
for metric, fn in (("rho", rho), ("partial rho", prho)):
    print(f"\n=== within-route {metric}: point estimates ===")
    for r in ROUTES:
        d = G[G.route == r]
        print(r, {k: round(fn(d, k), 3) for k in comps + [ref]})
    for blk in ("b5", "b1"):
        print(f"--- paired differences (model - untrained), bootstrap over {blk} blocks within route, B={B}")
        groups = {r: G[G.route == r] for r in ROUTES}
        blocks = {r: groups[r][blk].unique() for r in ROUTES}
        boot = {c: {r: [] for r in ROUTES + ["mean"]} for c in comps}
        for _ in range(B):
            per = {}
            for r in ROUTES:
                bs = rng.choice(blocks[r], len(blocks[r]), replace=True)
                d = pd.concat([groups[r][groups[r][blk] == b] for b in bs])
                per[r] = d
            for c in comps:
                diffs = [fn(per[r], c) - fn(per[r], ref) for r in ROUTES]
                for r, x in zip(ROUTES, diffs):
                    boot[c][r].append(x)
                boot[c]["mean"].append(np.mean(diffs))
        for c in comps:
            pt = {r: fn(groups[r], c) - fn(groups[r], ref) for r in ROUTES}
            pt["mean"] = np.mean([pt[r] for r in ROUTES])
            s = "  ".join(f"{r}:{pt[r]:+.3f}[{np.percentile(boot[c][r], 2.5):+.3f},{np.percentile(boot[c][r], 97.5):+.3f}]"
                          for r in ROUTES + ["mean"])
            print(f"{c:12s} {s}")
        if blk == "b5":
            print("n 5 km blocks per route:", {r: len(blocks[r]) for r in ROUTES})
