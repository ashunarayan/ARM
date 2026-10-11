"""Revision v2, class R re-analyses on LiRA-CD (PROTOCOL_V2.md, Section 4):

R2  unit-disjoint real baseline: LightGBM (inner leave-one-route-out selection, as M3) trained only on passes of
    telematics units that never drive the held-out route; size-matched control = random passes of all units with the
    same number of training units (5 draws, seeds 500 + d)
R7  anchor to Bajic et al. (2021): within-route spatial holdout on M3 (each direction: first 80 % of the chainage for
    training, last 20 % for testing); LightGBM, MLP (5 seeds), fitted index, training-mean baseline
R8  passes needed on a FIXED segment set: segments with >= 8 passes; n in {1, 2, 3, 5, 8} random passes, 20 repetitions,
    using the v1 held-out pass predictions of LightGBM, the fitted index and the simulation-trained LightGBM
Outputs: results/v2/unit_disjoint.csv, bajic_anchor.csv, passes_needed_fixed.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, LIRA_ROUTES, M, load_lira, seg_table, v1_pass_predictions  # noqa: E402


def gbm_inner(F, y, U, tr, te):
    """M3 recipe: inner leave-one-route-out over the training routes present."""
    routes = U.route.to_numpy()[tr]
    inner = [(np.where(routes != r)[0], np.where(routes == r)[0]) for r in np.unique(routes)] if len(np.unique(routes)) > 1 else None
    g = M.GBM().fit(dict(feat=F[tr], y=y[tr]), inner=inner)
    return g.predict(dict(feat=F[te], y=y[te]))


def r2_unit_disjoint(U, F, y):
    rows = []
    U = U.assign(pk=U.route + "|" + U.direction + "|" + U.task + "|" + U.pass_id)
    for R in LIRA_ROUTES:
        te = np.where(U.route == R)[0]
        units_R = set(U.unit.to_numpy()[te])
        tr_all = np.where(U.route != R)[0]
        tr_dis = tr_all[~np.isin(U.unit.to_numpy()[tr_all], list(units_R))]
        classes = sorted(set(U.cls.to_numpy()[tr_dis]))
        S = seg_table(U, te, gbm_inner(F, y, U, tr_dis, te))
        row = dict(fold=R, test_units=",".join(sorted(units_R)), n_train_units=len(tr_dis), n_train_all=len(tr_all),
                   train_classes="+".join(classes), both_classes=len(classes) == 2,
                   mae_unit_disjoint=float(np.mean(np.abs(S.p - S.y))), bias_unit_disjoint=float(np.mean(S.p - S.y)))
        ctrl = []
        passes = U.pk.to_numpy()[tr_all]
        for d in range(5):
            rng = np.random.default_rng(500 + d)
            order = rng.permutation(np.unique(passes))
            cnt = U.iloc[tr_all].groupby("pk").size().reindex(order).cumsum()
            keep = set(cnt.index[: int(np.searchsorted(cnt.to_numpy(), len(tr_dis))) + 1])
            sub = tr_all[np.isin(passes, list(keep))]
            Sc = seg_table(U, te, gbm_inner(F, y, U, sub, te))
            ctrl.append(float(np.mean(np.abs(Sc.p - Sc.y))))
        row.update(mae_size_matched_mean=float(np.mean(ctrl)), mae_size_matched_min=float(np.min(ctrl)),
                   mae_size_matched_max=float(np.max(ctrl)))
        pf = v1_pass_predictions(U, "lira_ladder.csv", "M3 LightGBM (all features)")
        Sf = seg_table(U, te, pf[te])
        row["mae_v1_all_units"] = float(np.mean(np.abs(Sf.p - Sf.y)))
        rows.append(row)
        print(row, flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "unit_disjoint.csv"), index=False)


def r7_bajic_anchor(U, F, y):
    rows = []
    m3 = U.route.to_numpy() == "M3"
    tr, te = [], []
    for d in ("HH", "VH"):
        idx = np.where(m3 & (U.direction.to_numpy() == d))[0]
        s = U.start_m.to_numpy()[idx]
        cut = s.min() + 0.8 * (s.max() + 100 - s.min())
        tr.append(idx[s + 100 <= cut]); te.append(idx[s >= cut])
    tr, te = np.concatenate(tr), np.concatenate(te)
    preds = {"train mean (baseline)": np.full(len(te), y[tr].mean()),
             "LightGBM": M.GBM().fit(dict(feat=F[tr], y=y[tr])).predict(dict(feat=F[te], y=y[te])),
             "vibration index (alpha fitted)": M.PhysicsIndex(None).fit(dict(feat=F[tr], y=y[tr])).predict(dict(feat=F[te], y=y[te]))}
    mlp = M.TorchModel("mlp", seeds=(0, 1, 2, 3, 4))
    D = dict(feat=F, seq=np.zeros((len(F), 400, 1), np.float32), y=y, group=U.segment.to_numpy())
    mlp.fit({k: v[tr] for k, v in D.items()})
    preds["MLP (5-seed mean prediction)"] = np.atleast_2d(mlp.predict_seeds({k: v[te] for k, v in D.items()})).mean(0)
    for name, p in preds.items():
        S = seg_table(U, te, p)
        e = S.p - S.y
        rows.append(dict(model=name, n_train_segments=int(len(np.unique(U.segment.to_numpy()[tr]))), n_test_segments=len(S),
                         mae=float(np.mean(np.abs(e))), rmse=float(np.sqrt(np.mean(e ** 2))),
                         r2=float(1 - np.sum(e ** 2) / np.sum((S.y - S.y.mean()) ** 2)), test_mean_iri=float(S.y.mean())))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "bajic_anchor.csv"), index=False)
    print(T.round(3).to_string(index=False))


def r8_passes_fixed(U):
    P = {"real LightGBM": v1_pass_predictions(U, "lira_ladder.csv", "M3 LightGBM (all features)"),
         "real index (M2c)": v1_pass_predictions(U, "lira_ladder.csv", "M2c RMS/v^alpha (alpha fitted on training data)"),
         "sim LightGBM (V0)": v1_pass_predictions(U, "lira_zeroshot.csv", "Z sim[p79] LightGBM")}
    npass = U.groupby("segment").segment.transform("size").to_numpy()
    keep = npass >= 8
    rows = []
    for name, p in P.items():
        df = pd.DataFrame(dict(seg=U.segment.to_numpy()[keep], cls=U.cls.to_numpy()[keep], y=U.mri.to_numpy()[keep], p=p[keep]))
        groups = {s: g for s, g in df.groupby("seg")}
        for n in (1, 2, 3, 5, 8):
            for rep in range(20):
                rng = np.random.default_rng(1000 * n + rep)
                e = {"urban": [], "motorway": []}
                for s, g in groups.items():
                    pick = rng.choice(len(g), n, replace=False)
                    e[g.cls.iloc[0]].append(abs(g.p.to_numpy()[pick].mean() - g.y.iloc[0]))
                for c, v in e.items():
                    rows.append(dict(model=name, road=c, n_passes=n, rep=rep, mae=float(np.mean(v)), n_segments=len(v)))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "passes_needed_fixed.csv"), index=False)
    print(T.groupby(["model", "road", "n_passes"]).agg(mae=("mae", "mean"), n_seg=("n_segments", "first")).round(3).unstack("n_passes").to_string())


def main():
    U, F = load_lira()
    y = U.mri.to_numpy()
    which = sys.argv[1:] or ["r2", "r7", "r8"]
    if "r8" in which:
        r8_passes_fixed(U)
    if "r7" in which:
        r7_bajic_anchor(U, F, y)
    if "r2" in which:
        r2_unit_disjoint(U, F, y)


if __name__ == "__main__":
    main()
