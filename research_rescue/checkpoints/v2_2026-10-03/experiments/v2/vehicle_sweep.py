"""Revision v2, S1 (class S, controlled simulation; PROTOCOL_V2.md Section 6): does the seen/unseen-vehicle gap
shrink with the number of training vehicles at a FIXED amount of training data?

* vehicle pool (seed 20261003): 300 training and 30 test parameter sets drawn from the documented ranges
* profiles: v1 synthetic training routes iso_routes(rng(1), 40, 'isotr') and held-out routes iso_routes(rng(2), 15, 'isote')
* N in {3, 10, 30, 100, 300} training vehicles = the first N of the pool; 1,200 training passes for every N
  (vehicle and route of each pass assigned by a balanced shuffle, seed 20261003 + N); V0 sensor mixture
* test: every held-out route driven once by each of the 30 unseen vehicles and once by each of the first min(N, 30)
  training vehicles (seen reference); random speeds, V0 sensor mixture
* models: LightGBM (first configuration) and the fitted vibration index
* v1 statistic: per-segment mean absolute error over passes, unseen minus seen on the same segments, bootstrap over
  segments (B = 2000); criterion: relative increase <= 10 % with its upper 95 % bound. A bootstrap over the 15 held-out
  routes is reported as a conservative alternative.
* N = 30: per-vehicle MAE vs standardised parameter distance to the nearest training vehicle.
Outputs: data/processed/v2/sweep_*; results/v2/vehicle_sweep.csv, vehicle_sweep_distance.csv
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, RESCUE, fit_predict_gbm, fit_predict_index  # noqa: E402
sys.path.insert(0, os.path.join(RESCUE, "experiments"))
from common import vehsim, simpipe  # noqa: E402
from common.paths import PROCESSED  # noqa: E402
from sim_generate import iso_routes, sensor_for  # noqa: E402

PROC = os.path.join(PROCESSED, "v2"); os.makedirs(PROC, exist_ok=True)
NS = [3, 10, 30, 100, 300]
N_PASSES = 1200
PARAMS = ["m_s", "r_y", "L", "a_frac", "f_s", "rear_freq_ratio", "zeta", "m_u", "k_t", "x_s"]


def pool():
    rng = np.random.default_rng(20261003)
    train = [(f"p{i:03d}", vehsim.sample_vehicle(rng)) for i in range(300)]
    test = [(f"u{i:02d}", vehsim.sample_vehicle(rng)) for i in range(30)]
    return train, test


def simulate(jobs, seed, name):
    """jobs: list of (route dict, (vehicle id, params)); one pass each. Saves meta + features."""
    path = os.path.join(PROC, f"sweep_{name}.npz")
    if os.path.exists(path):
        A = np.load(path); return pd.read_csv(os.path.join(PROC, f"sweep_{name}_meta.csv")), A["feat"]
    rng = np.random.default_rng(seed)
    rows, feats = [], []
    for P, (vid, veh) in jobs:
        sk, sens = sensor_for(rng, "mix")
        units, ft, _ = simpipe.run_pass(rng, P["z"], P["dx"], P["s0"], P["starts"], veh, sens)
        lab = dict(zip(P["starts"], P["labels"]))
        for u, f_ in zip(units, ft):
            rows.append(dict(route=P["route"], vehicle=vid, sensor=sk, segment=f"{P['route']}_{int(u['start_m'])}",
                             mri=lab[u["start_m"]], v_mean=u["v_mean"]))
            feats.append(f_)
    m = pd.DataFrame(rows)
    m.to_csv(os.path.join(PROC, f"sweep_{name}_meta.csv"), index=False)
    np.savez_compressed(path, feat=np.array(feats, np.float32))
    return m, np.array(feats, np.float32)


def train_jobs(N, train_pool, routes):
    rng = np.random.default_rng(20261003 + N)
    veh = rng.permutation(np.resize(np.arange(N), N_PASSES))
    rts = rng.permutation(np.resize(np.arange(len(routes)), N_PASSES))
    return [(routes[r], train_pool[v]) for v, r in zip(veh, rts)]


def paired(mte_u, pu, mte_s, ps, B=2000, seed=0):
    eU = pd.Series(np.abs(pu - mte_u.mri.to_numpy())).groupby(mte_u.segment.to_numpy()).mean()
    eS = pd.Series(np.abs(ps - mte_s.mri.to_numpy())).groupby(mte_s.segment.to_numpy()).mean()
    j = pd.concat([eU.rename("u"), eS.rename("s")], axis=1).dropna()
    d = (j.u - j.s).to_numpy(); base = j.s.mean()
    rng = np.random.default_rng(seed)
    bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(B)])
    return dict(mae_seen=float(j.s.mean()), mae_unseen=float(j.u.mean()), diff=float(d.mean()),
                lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), rel=float(d.mean() / base),
                rel_hi=float(np.percentile(bs, 97.5) / base), meets_v1_criterion=bool(np.percentile(bs, 97.5) / base <= 0.10),
                n_units_compared=len(j))


def main():
    t0 = time.time()
    train_pool, test_pool = pool()
    iso_tr = iso_routes(np.random.default_rng(1), 40, tag="isotr")
    iso_te = iso_routes(np.random.default_rng(2), 15, tag="isote")
    # generate (in parallel) the five training sets and the two test sets
    tasks = [(train_jobs(N, train_pool, iso_tr), 61000 + N, f"train_N{N}") for N in NS]
    tasks.append(([(P, v) for P in iso_te for v in test_pool], 62001, "test_unseen"))
    tasks.append(([(P, v) for P in iso_te for v in train_pool[:30]], 62002, "test_seen30"))
    Parallel(n_jobs=4)(delayed(simulate)(j, s, n) for j, s, n in tasks)
    mu, Fu = simulate(None, 0, "test_unseen")
    ms30, Fs30 = simulate(None, 0, "test_seen30")
    print(f"simulated ({time.time() - t0:.0f}s)", flush=True)
    rows, dist_rows = [], []
    lo_ = np.array([vehsim.RANGES["vehicle"][k if k not in ("m_u", "k_t") else {"m_u": "m_u_per_wheel", "k_t": "k_t_per_tire"}[k]]["range"]
                    for k in PARAMS], float)
    width = lo_[:, 1] - lo_[:, 0]
    for N in NS:
        mt, Ft = simulate(None, 0, f"train_N{N}")
        seen_ids = {v for v, _ in train_pool[:min(N, 30)]}
        sel = ms30.vehicle.isin(seen_ids).to_numpy()
        ms, Fs = ms30[sel].reset_index(drop=True), Fs30[sel]
        for model, fp in (("GBM", fit_predict_gbm), ("INDEX", fit_predict_index)):
            pu = fp(Ft, mt.mri.to_numpy(), Fu); ps = fp(Ft, mt.mri.to_numpy(), Fs)
            r = paired(mu, pu, ms, ps)
            # conservative: bootstrap over held-out routes of the per-segment differences
            eU = pd.Series(np.abs(pu - mu.mri.to_numpy())).groupby(mu.segment.to_numpy()).mean()
            eS = pd.Series(np.abs(ps - ms.mri.to_numpy())).groupby(ms.segment.to_numpy()).mean()
            j = pd.concat([eU.rename("u"), eS.rename("s")], axis=1).dropna()
            j["route"] = [s.split("_")[0] for s in j.index]
            g = j.groupby("route").apply(lambda q: pd.Series(dict(d=(q.u - q.s).sum(), s=q.s.sum(), n=len(q))))
            rng = np.random.default_rng(1); C = len(g)
            bs = []
            for _ in range(2000):
                w = np.bincount(rng.integers(0, C, C), minlength=C)
                bs.append((w @ g.d.to_numpy()) / (w @ g.s.to_numpy()))
            rows.append(dict(N=N, model=model, n_train_units=len(mt), **r, rel_hi_route_boot=float(np.percentile(bs, 97.5))))
            if N == 30 and model == "GBM":
                tr_par = np.array([[p[k] for k in PARAMS] for _, p in train_pool[:30]])
                e = pd.DataFrame(dict(v=mu.vehicle, ae=np.abs(pu - mu.mri.to_numpy()))).groupby("v").ae.mean()
                for vid, p in test_pool:
                    x = np.array([p[k] for k in PARAMS])
                    dmin = float(np.min(np.sqrt((((tr_par - x) / width) ** 2).sum(1))))
                    dist_rows.append(dict(vehicle=vid, dist_nearest=dmin, mae=float(e[vid]), f_s=p["f_s"], zeta=p["zeta"]))
        print(f"N={N:3d} ({time.time() - t0:.0f}s)", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(OUT, "vehicle_sweep.csv"), index=False)
    Dd = pd.DataFrame(dist_rows)
    Dd.to_csv(os.path.join(OUT, "vehicle_sweep_distance.csv"), index=False)
    print(R[["N", "model", "mae_seen", "mae_unseen", "rel", "rel_hi", "rel_hi_route_boot", "meets_v1_criterion"]].round(3).to_string(index=False))
    if len(Dd):
        print("N=30 per-vehicle MAE vs distance: Spearman", round(float(spearmanr(Dd.dist_nearest, Dd.mae)[0]), 3))


if __name__ == "__main__":
    main()
