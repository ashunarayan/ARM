"""Review check 2 (read-only): how far does a 1-2 parameter vibration index calibrated on the same k km of paired
drives get, without any simulator? Uses the paper's exact block sampler (default_rng(1000*d+7), contiguous 1 km
blocks of the training routes) so every arm is paired draw by draw with the paper's arms.

Arms (all calibrated ONLY on the k km of real training-route passes; test route never used):
  idx05_level   log IRI = c + log(RMS / v^0.5)                       (1 parameter: c)
  idx05_affine  log IRI = c + b log(RMS / v^0.5)                     (2 parameters, OLS on calibration segments)
  idxcar_affine log IRI = c + b log(RMS / v^alpha_car), alpha_car = label-free within-segment speed exponent of the
                car's raw RMS estimated on the TRAINING routes' unlabelled repeated passes (2 parameters + label-free alpha)
  simidx_level  three-parameter index fitted on V0 simulated units of the training routes, + level offset (= Table S13)
Paper arms read from results/v2: real_only (LightGBM on the k km), real_only_index (3-parameter index on the k km),
sim_all_cal for V0..V8 (LightGBM on all simulated training-route profiles + level offset).
Writes only to the scratchpad (stdout)."""
import sys
import numpy as np
import pandas as pd

RR = sys.argv[1]  # research_rescue
EPS = 1e-3
FEATURE_NAMES = (["log_v_mean", "v_cv", "log_rms", "log_p95_abs", "log_max_abs", "crest", "kurtosis"]
                 + [f"log_band_{lo:g}_{hi:g}" for lo, hi in [(0.5, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 15.0)]]
                 + ["log_rms_hp1", "log_rms_spatial_lt5m"])
FI = {n: i for i, n in enumerate(FEATURE_NAMES)}
ROUTES = ["CPH1", "CPH6", "M3", "M13"]


def block_id(df, L=1000):
    return df.route.astype(str) + "_" + df.direction.astype(str) + "_" + (df.start_m // L).astype(int).astype(str)


U = pd.read_csv(f"{RR}/data/processed/lira/units.csv")
A = np.load(f"{RR}/data/processed/lira/arrays.npz")
assert list(A["feature_names"]) == FEATURE_NAMES
F = A["feat"].astype(float)
U["block"] = block_id(U)
y = U.mri.to_numpy()
lrms, lv = F[:, FI["log_rms"]], F[:, FI["log_v_mean"]]

ms = pd.read_csv(f"{RR}/data/processed/sim/p79_train_meta.csv")
with np.load(f"{RR}/data/processed/sim/p79_train_arrays.npz") as Z:
    Fs = Z["feat"].astype(float)
ys = ms.mri.to_numpy()


def sample_blocks(tr_idx, k, rng):
    blocks = U.block.to_numpy()[tr_idx]
    ub = np.unique(blocks)
    chosen = rng.choice(ub, size=min(len(ub), int(k)), replace=False)
    return tr_idx[np.isin(blocks, chosen)]


def seg_mae(idx, p):
    d = pd.DataFrame(dict(seg=U.segment.to_numpy()[idx], y=y[idx], p=p))
    g = d.groupby("seg").agg(y=("y", "first"), p=("p", "mean"))
    return float(np.mean(np.abs(g.p - g.y))), len(g), float(np.mean(g.p - g.y))


def seg_means(idx, x):
    d = pd.DataFrame(dict(seg=U.segment.to_numpy()[idx], y=y[idx], x=x))
    return d.groupby("seg").agg(y=("y", "first"), x=("x", "mean"))


def alpha_car(tr_idx):
    """label-free: within-segment slope of log RMS on log speed, segments with >=3 passes (training routes only)."""
    d = pd.DataFrame(dict(seg=U.segment.to_numpy()[tr_idx], r=lrms[tr_idx], v=lv[tr_idx]))
    n = d.groupby("seg").r.transform("size")
    d = d[n >= 3]
    dr = d.r - d.groupby("seg").r.transform("mean"); dv = d.v - d.groupby("seg").v.transform("mean")
    return float((dr * dv).sum() / (dv * dv).sum())


rows = []
for R in ROUTES:
    te = np.where(U.route == R)[0]; tr = np.where(U.route != R)[0]
    a_car = alpha_car(tr)
    # simulation-fitted three-parameter index (V0 units of the training routes), as the paper's INDEX zero-shot
    sel = (ms.route != R).to_numpy()
    Xs = np.column_stack([np.ones(sel.sum()), Fs[sel, FI["log_rms"]], Fs[sel, FI["log_v_mean"]]])
    coef_sim = np.linalg.lstsq(Xs, np.log(ys[sel] + EPS), rcond=None)[0]
    lp_simidx = np.column_stack([np.ones(len(U)), lrms, lv]) @ coef_sim
    print(f"{R}: alpha_car(label-free, train routes)={a_car:.3f}; sim index coef a={coef_sim[0]:.3f} b={coef_sim[1]:.3f} "
          f"alpha_sim={-coef_sim[2] / coef_sim[1]:.3f}")
    s05 = lrms - 0.5 * lv
    scar = lrms - a_car * lv
    for k in [1, 2, 5, 10, 20]:
        for d in range(20):
            rng = np.random.default_rng(1000 * d + 7)
            sub = sample_blocks(tr, k, rng)
            # 1-parameter level on the untrained statistic (median log ratio over calibration passes, like the paper)
            c05 = np.median(np.log(y[sub] + EPS) - s05[sub])
            p1 = np.exp(c05 + s05[te]) - EPS
            # 2-parameter affine on calibration segments (like the paper's affine calibration)
            S5 = seg_means(sub, s05[sub]); b5, a5 = np.polyfit(S5.x, np.log(S5.y + EPS), 1)
            p2 = np.exp(a5 + b5 * s05[te]) - EPS
            Sc = seg_means(sub, scar[sub]); bc, ac = np.polyfit(Sc.x, np.log(Sc.y + EPS), 1)
            p3 = np.exp(ac + bc * scar[te]) - EPS
            csim = np.median(np.log(y[sub] + EPS) - lp_simidx[sub])
            p4 = np.exp(lp_simidx[te] + csim) - EPS
            for arm, p, extra in (("idx05_level", p1, np.nan), ("idx05_affine", p2, b5), ("idxcar_affine", p3, bc),
                                  ("simidx_level", p4, np.nan)):
                mae, n, bias = seg_mae(te, np.clip(p, 0, None))
                rows.append(dict(fold=R, k_km=k, draw=d, arm=arm, seg_mae=mae, n_seg=n, seg_bias=bias, slope=extra))

D = pd.DataFrame(rows)


def pooled(D, keys):
    D = D.assign(w=D.seg_mae * D.n_seg)
    a = D.groupby(keys + ["draw"]).agg(w=("w", "sum"), n=("n_seg", "sum"), nf=("fold", "nunique")).reset_index()
    assert (a.nf == 4).all()
    a["mae"] = a.w / a.n
    return a


mine = pooled(D, ["arm", "k_km"])
R4 = pd.read_csv(f"{RR}/results/v2/value_of_simulation.csv")
real = pooled(R4[R4.arm == "real_only"], ["arm", "k_km"])
ridx = pooled(pd.read_csv(f"{RR}/results/v2/value_real_index.csv"), ["arm", "k_km"])
C = pd.read_csv(f"{RR}/results/v2/variants_calibration.csv")
C = C[(C.model == "GBM") & (C.calib == "intercept") & C.vid.isin([f"V{i}" for i in range(9)])]
simcal = pooled(C.rename(columns={"vid": "arm"}), ["arm", "k_km"])
allarms = pd.concat([mine, real, ridx, simcal], ignore_index=True)
tab = allarms.groupby(["arm", "k_km"]).mae.mean().unstack("k_km").reindex(columns=[1, 2, 5, 10, 20])
pd.set_option("display.width", 200)
print("\nPooled segment MAE (m/km), mean over the same 20 draws:")
print(tab.round(3).to_string())
# paired comparisons draw by draw at each k: arm minus V0..V8 sim_all_cal and minus real_only
piv = allarms.pivot_table(index=["k_km", "draw"], columns="arm", values="mae")
print("\nDraw-by-draw: idxcar_affine minus each sim_all_cal variant (mean diff, #draws sim better):")
for k in [1, 2, 5, 10, 20]:
    q = piv.loc[k]
    s = []
    for v in [f"V{i}" for i in range(9)]:
        dd = q[v] - q["idxcar_affine"]
        s.append(f"{v}:{dd.mean():+.3f}({int((dd < 0).sum())})")
    print(f"k={k:2d}: " + "  ".join(s))
print("\nDraw-by-draw: idxcar_affine minus real_only LightGBM (mean, #idx better):")
for k in [1, 2, 5, 10, 20]:
    q = piv.loc[k]; dd = q["idxcar_affine"] - q["real_only"]
    print(f"k={k:2d}: {dd.mean():+.3f} ({int((dd < 0).sum())}/20)   vs real_only_index: "
          f"{(q['idxcar_affine'] - q['real_only_index']).mean():+.3f} ({int(((q['idxcar_affine'] - q['real_only_index']) < 0).sum())}/20)")
print("\nFitted slope b (affine arms), mean over folds/draws:")
print(D.dropna(subset=["slope"]).groupby(["arm", "k_km"]).slope.agg(["mean", "min", "max"]).round(3).to_string())
