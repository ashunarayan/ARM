"""Audit step 4: retrain headline models with independent code and compare with the stored predictions.

1. M3 real-trained LightGBM with inner leave-one-route-out configuration selection (6 configs) -> ladder predictions
2. V0 zero-shot LightGBM (simulated units of the training routes only) -> stored held-out predictions
3. Joint training (equal total weight) for V0 and V5 at k = 5 -> pooled_segpred.npz
4. Band-limited intervention (features without content above 10 Hz; and without the 10-15 Hz band) for V0-V8
5. Pass density m = 1 at k = 5 with an INDEPENDENT random pass subsample (robustness, not exact reproduction)
"""
import os, sys, time
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

RR = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue"
ROUTES = ["CPH1", "CPH6", "M3", "M13"]
EPS = 1e-3
GRID = [dict(num_leaves=nl, min_child_samples=mc) for nl in (7, 15, 31) for mc in (20, 60)]
FN = ['log_v_mean', 'v_cv', 'log_rms', 'log_p95_abs', 'log_max_abs', 'crest', 'kurtosis', 'log_band_0.5_2', 'log_band_2_5',
      'log_band_5_10', 'log_band_10_15', 'log_rms_hp1', 'log_rms_spatial_lt5m']
which = sys.argv[1:] or ["1", "2", "3", "4", "5"]

U = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "units.csv"))
A = np.load(os.path.join(RR, "data", "processed", "lira", "arrays.npz"))
assert [str(s) for s in A["feature_names"]] == FN
F = A["feat"]; y = U.mri.to_numpy(); seg_of = U.segment.to_numpy(); route = U.route.to_numpy()
U["blk1"] = U.route + "_" + U.direction + "_" + (U.start_m // 1000).astype(int).astype(str)


def lgbm(p=GRID[0]):
    return LGBMRegressor(n_estimators=400, learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.9,
                         reg_lambda=1.0, verbose=-1, random_state=0, **p)


def fitpred(X, t, Xte, p=GRID[0], w=None):
    return np.clip(np.exp(lgbm(p).fit(X, np.log(t + EPS), sample_weight=w).predict(Xte)) - EPS, 0, None)


def segmean(idx, p):
    return pd.DataFrame(dict(seg=seg_of[idx], p=p, y=y[idx])).groupby("seg", sort=True).agg(p=("p", "mean"), y=("y", "first"))


def draw_blocks(tr, k, d):
    rng = np.random.default_rng(1000 * d + 7)
    b = U.blk1.to_numpy()[tr]; ub = np.unique(b)
    return tr[np.isin(b, rng.choice(ub, size=min(len(ub), k), replace=False))]


SIMC = {}
def sim(name):
    if name not in SIMC:
        m = pd.read_csv(os.path.join(RR, "data", "processed", "sim", f"{name}_meta.csv"))
        with np.load(os.path.join(RR, "data", "processed", "sim", f"{name}_arrays.npz")) as z:
            SIMC[name] = (m, z["feat"])
    return SIMC[name]


VAR = {"V0": ("p79_train", None), "V1": ("p79_train", ("sensor", "autopi")), "V2": ("p79_train", ("sensor", "phone")),
       "V3": ("p79_train_idealsensor", None), "V4": ("p79_train_fixedvehicle", None),
       "V5": ("p79_train_measuredsensor", None), "V6": ("p79_train_measuredmix", None),
       "V7": ("p79_train_telecompliant", "half"), "V8": ("p79_train_phonerigid", "half")}


def simset(vid, R):
    name, filt = VAR[vid]
    m, f = sim(name)
    sel = (m.route != R).to_numpy()
    if filt == "half":
        keys = m.route.astype(str) + "|" + m.direction.astype(str) + "|" + m.vehicle.astype(str) + "|" + m.v0_kmh.round(6).astype(str)
        uk = np.unique(keys)
        keep = set(np.random.default_rng(7).choice(uk, size=len(uk) // 2, replace=False).tolist())
        sel &= keys.isin(keep).to_numpy()
    elif filt is not None:
        sel &= (m[filt[0]] == filt[1]).to_numpy()
    return m[sel], f[sel], m.mri.to_numpy()[sel]


t0 = time.time()
if "1" in which:
    L = pd.read_csv(os.path.join(RR, "results", "predictions", "lira_ladder.csv.gz"))
    L = L[L.model == "M3 LightGBM (all features)"]
    stored = L.groupby("segment").pred.mean()
    mx, chosen = 0.0, {}
    for R in ROUTES:
        te = np.where(route == R)[0]; tr = np.where(route != R)[0]
        scores = []
        for p in GRID:
            e = []
            for r in np.unique(route[tr]):
                itr, iva = tr[route[tr] != r], tr[route[tr] == r]
                e.append(np.mean(np.abs(fitpred(F[itr], y[itr], F[iva], p) - y[iva])))
            scores.append(np.mean(e))
        best = GRID[int(np.argmin(scores))]; chosen[R] = best
        s = segmean(te, fitpred(F[tr], y[tr], F[te], best))
        mx = max(mx, float(np.max(np.abs(s.p - stored.reindex(s.index)))))
    print(f"[1] M3 retrain with inner LORO: chosen configs {chosen}; max |seg pred - stored| = {mx:.2e} ({time.time() - t0:.0f}s)")

if "2" in which:
    VP = pd.read_csv(os.path.join(RR, "results", "v2", "variants_pass_predictions.csv.gz"))
    q = VP[(VP.vid == "V0") & (VP.model == "GBM")]
    m0, _ = sim("p79_train")
    print("[2] sim p79_train routes:", m0.route.value_counts().to_dict(), " units:", len(m0), " sensors:", m0.sensor.value_counts().to_dict())
    mx = 0.0
    for R in ROUTES:
        mm, X, t = simset("V0", R)
        assert not (mm.route == R).any()
        te = np.where(route == R)[0]
        p = fitpred(X, t, F[te])
        qq = q[q.fold == R].set_index("unit").pred.reindex(te).to_numpy()
        mx = max(mx, float(np.max(np.abs(p - qq))))
    print(f"[2] V0 zero-shot retrain: max |pass pred - stored| = {mx:.2e} ({time.time() - t0:.0f}s)")

if "3" in which:
    PS = np.load(os.path.join(RR, "results", "v3", "pooled_segpred.npz"))
    for vid in ("V0", "V5"):
        mx = 0.0
        for R in ROUTES:
            te = np.where(route == R)[0]; tr = np.where(route != R)[0]
            mm, Xs, ys = simset(vid, R)
            for d in range(20):
                sub = draw_blocks(tr, 5, d)
                w = np.concatenate([np.ones(len(ys)), np.full(len(sub), len(ys) / len(sub))])
                p = fitpred(np.vstack([Xs, F[sub]]), np.concatenate([ys, y[sub]]), F[te], w=w)
                s = segmean(te, p)
                mx = max(mx, float(np.max(np.abs(s.p.to_numpy() - PS[f"{vid}|{R}|5"][d]))))
        print(f"[3] joint training {vid} k=5 retrain: max |seg pred - stored| = {mx:.2e} ({time.time() - t0:.0f}s)")

if "4" in which:
    sets = {"full": FN, "no1015": [f for f in FN if f != "log_band_10_15"],
            "lt10": ["log_v_mean", "v_cv", "log_band_0.5_2", "log_band_2_5", "log_band_5_10"]}
    rows = []
    for vid in VAR:
        for sn, fs in sets.items():
            cols = [FN.index(f) for f in fs]
            lv, ae, err = {}, 0.0, []
            for R in ROUTES:
                mm, X, t = simset(vid, R)
                te = np.where(route == R)[0]
                s = segmean(te, fitpred(X[:, cols], t, F[te][:, cols]))
                lv[R] = float(np.mean(np.log((s.p + EPS) / (s.y + EPS))))
                err.append((s.p - s.y).to_numpy())
            e = np.concatenate(err)
            rows.append(dict(vid=vid, set=sn, mae=np.mean(np.abs(e)), bias=np.mean(e), lvl_mean=np.mean(list(lv.values())),
                             lvl_urban=(lv["CPH1"] + lv["CPH6"]) / 2, lvl_mw=(lv["M3"] + lv["M13"]) / 2))
    B = pd.DataFrame(rows)
    print(B.pivot(index="vid", columns="set", values=["bias", "lvl_mean"]).round(3).to_string())
    sens = B[B.vid != "V4"]
    for col in ("bias", "lvl_mean", "lvl_urban", "lvl_mw"):
        sp = sens.groupby("set")[col].agg(lambda x: x.max() - x.min())
        print(f"[4] spread over 8 sensor variants of {col}: " + ", ".join(f"{k} {v:.3f}" for k, v in sp.items())
              + f"; ratio lt10/full {sp['lt10'] / sp['full']:.2f}; no1015/full {sp['no1015'] / sp['full']:.3f}")
    print("[4] V4 lt10 lvl_mean %.3f; sensor variants lt10 lvl_mean %.3f..%.3f" % (
        B[(B.vid == "V4") & (B.set == "lt10")].lvl_mean.iloc[0], sens[sens.set == "lt10"].lvl_mean.min(),
        sens[sens.set == "lt10"].lvl_mean.max()))
    BL = pd.read_csv(os.path.join(RR, "results", "v3", "band_limited.csv"))
    mg = B.merge(BL, left_on=["vid", "set"], right_on=["vid", "features"], suffixes=("", "_st"))
    print("[4] max |own - stored|: bias %.2e, lvl_mean %.2e (%.0fs)" % (np.max(np.abs(mg.bias - mg.bias_st)),
                                                                     np.max(np.abs(mg.lvl_mean - mg.lvl_mean_st)), time.time() - t0))

if "5" in which:
    # independent subsample: one pass per segment, own RNG (seed 424242 + d)
    PSv = {}
    res = {"real": np.zeros(20)}
    with_vids = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
    Z = {}
    for vid in with_vids:
        with np.load(os.path.join(RR, "data", "processed", "v3", f"zeroshot_allunits_{vid}.npz")) as z:
            Z[vid] = {R: z[R] for R in ROUTES}
        res["cal " + vid] = np.zeros(20)
    for vid in ("V0", "V5"):
        res["joint " + vid] = np.zeros(20)
    nunits = []
    for R in ROUTES:
        te = np.where(route == R)[0]; tr = np.where(route != R)[0]
        sims = {vid: simset(vid, R) for vid in ("V0", "V5")}
        for d in range(20):
            sub = draw_blocks(tr, 5, d)
            rng = np.random.default_rng(424242 + d)
            sm = np.sort(np.array([rng.choice(sub[seg_of[sub] == s_]) for s_ in np.unique(seg_of[sub])]))
            nunits.append(len(sm))
            s = segmean(te, fitpred(F[sm], y[sm], F[te])); res["real"][d] += np.abs(s.p - s.y).sum()
            for vid in with_vids:
                c = np.median(np.log((y[sm] + EPS) / (Z[vid][R][sm] + EPS)))
                s = segmean(te, np.clip(np.exp(np.log(Z[vid][R][te] + EPS) + c) - EPS, 0, None))
                res["cal " + vid][d] += np.abs(s.p - s.y).sum()
            for vid in ("V0", "V5"):
                mm, Xs, ys = sims[vid]
                w = np.concatenate([np.ones(len(ys)), np.full(len(sm), len(ys) / len(sm))])
                s = segmean(te, fitpred(np.vstack([Xs, F[sm]]), np.concatenate([ys, y[sm]]), F[te], w=w))
                res["joint " + vid][d] += np.abs(s.p - s.y).sum()
    print(f"[5] m=1 own subsample: mean calibration units {np.mean(nunits):.0f}")
    for k, v in res.items():
        v = v / 1678
        print(f"[5]   {k:9s} pooled MAE {v.mean():.3f}; better than real-only in {int((v < res['real'] / 1678).sum())}/20 draws")
    print(f"({time.time() - t0:.0f}s)")
