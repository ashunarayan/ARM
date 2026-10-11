"""Re-evaluate the saved Run-1 models honestly and compare with trivial baselines."""
import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.linear_model import LinearRegression
from lightgbm import LGBMRegressor

tf.get_logger().setLevel("ERROR")
ROOT = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model"
BASE = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model_work\data\simulation\data\IRI_new_experiments"
d = np.load(os.path.join(ROOT, "iri_v2", "output", "iri_v2_data.npz"))
Xtr, Ctr, ytr = d["x_train_raw"], d["x_train_ctx"], d["y_train"]
Xva, Cva, yva = d["x_val_raw"], d["x_val_ctx"], d["y_val"]
Xte, Cte, yte = d["x_test_raw"], d["x_test_ctx"], d["y_test"]


# ---- reconstruct trip membership of test windows (same loop as data_pipeline, counting only) ----
def n_windows(car, trip):
    df = pd.read_csv(os.path.join(BASE, car, "automation_test_track", trip, "readings_2.csv"))
    df = df[df.speed_ms >= 1.0].sort_values("sample_number")
    t = df.sample_number * 0.01
    dt = t.diff().fillna(0.01)
    cd = (df.speed_ms * dt).cumsum().values
    phantom = (df.speed_ms * dt)[dt > 0.011].sum()
    print(f"    {car} {trip}: phantom distance from stops = {phantom:.1f} m over {int((dt > 0.011).sum())} gaps")
    n, seg_ids = 0, []
    for s in np.arange(0, cd.max() - 100, 10):
        if np.sum((cd >= s) & (cd < s + 100)) >= 20:
            n += 1
            seg_ids.append(int(s // 100))
    return n


groups = []
for car, trip in [("hopper", "trip_2"), ("hopper", "trip_3"), ("sunburst2", "trip_2"), ("vivace", "trip_2")]:
    groups += [f"{car}_{trip}"] * n_windows(car, trip)
groups = np.array(groups)
print("reconstructed test windows:", len(groups), "(stored:", len(yte), ")")
print(pd.Series(groups).value_counts().to_string())
assert len(groups) == len(yte)
# 100 m label blocks for the block bootstrap: consecutive windows sharing a 100 m block (10 windows each)
blocks = np.array([f"{g}_{i // 10}" for g, i in zip(groups, np.concatenate([np.arange(np.sum(groups == g)) for g in pd.unique(groups)]))])
print("independent-ish 100 m blocks in test:", len(np.unique(blocks)))


def metrics(y, p):
    e = np.abs(y - p)
    return dict(MAE=mean_absolute_error(y, p), R2=r2_score(y, p), r=np.corrcoef(y, p)[0, 1],
                w10=100 * np.mean(e <= 1.0), w15=100 * np.mean(e <= 1.5), w20=100 * np.mean(e <= 2.0))


def block_boot(y, p, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    ub = np.unique(blocks)
    idx_by = {b: np.where(blocks == b)[0] for b in ub}
    out = []
    for _ in range(B):
        pick = rng.choice(ub, len(ub), replace=True)
        ii = np.concatenate([idx_by[b] for b in pick])
        out.append([mean_absolute_error(y[ii], p[ii]), r2_score(y[ii], p[ii])])
    return np.percentile(np.array(out), [2.5, 97.5], axis=0)


rows = {}
# ---- the paper's model: 5 seeds, val-fitted PICA LUT ----
preds = []
for s in [42, 43, 44, 45, 46]:
    sd = os.path.join(ROOT, "iri_v3", "outputs", "run_01", f"seed_{s}")
    m = tf.keras.models.load_model(os.path.join(sd, "best_model.keras"), compile=False)
    raw = np.expm1(m.predict([Xte, Cte], verbose=0).ravel())
    lut = json.load(open(os.path.join(sd, "calibration_lut.json")))
    cal = np.interp(raw, lut["x_raw"], lut["y_calibrated"])  # isotonic w/ clip == piecewise-linear interp of thresholds
    preds.append(cal)
    rows[f"Run1 seed {s} (+PICA)"] = metrics(yte, cal)
    rows[f"Run1 seed {s} raw"] = metrics(yte, raw)
P = np.mean(preds, axis=0)

# ---- trivial / shortcut baselines trained ONLY on train split ----
rows["constant = train median"] = metrics(yte, np.full_like(yte, np.median(ytr)))
rows["constant = train mean"] = metrics(yte, np.full_like(yte, ytr.mean()))
lr = LinearRegression().fit(np.column_stack([np.log(Ctr[:, 0]), Ctr[:, 1]]), np.log1p(ytr))
rows["speed-only log-linear (train)"] = metrics(yte, np.expm1(lr.predict(np.column_stack([np.log(Cte[:, 0]), Cte[:, 1]]))))
gb = LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=50, verbose=-1, random_state=0)
gb.fit(Ctr[:, :2], np.log1p(ytr))
rows["speed-only LightGBM (speed_mean, speed_std)"] = metrics(yte, np.expm1(gb.predict(Cte[:, :2])))
gb2 = LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=15, min_child_samples=50, verbose=-1, random_state=0)
gb2.fit(Ctr, np.log1p(ytr))
rows["13 context features only, LightGBM log-target"] = metrics(yte, np.expm1(gb2.predict(Cte)))
# isotonic fitted on val on top of the 13-feature GBM (same PICA protocol as paper)
from sklearn.isotonic import IsotonicRegression
iso = IsotonicRegression(out_of_bounds="clip").fit(np.expm1(gb2.predict(Cva)), yva)
rows["13 ctx LightGBM + val-PICA"] = metrics(yte, iso.predict(np.expm1(gb2.predict(Cte))))
# 'oracle-ish' leakage: isotonic on val labels vs val SPEED only (speed->IRI map learned on the test track)
iso_sp = IsotonicRegression(increasing=False, out_of_bounds="clip").fit(Cva[:, 0], yva)
rows["speed-only isotonic fitted on VAL (same track)"] = metrics(yte, iso_sp.predict(Cte[:, 0]))

R = pd.DataFrame(rows).T
pd.set_option("display.width", 200)
print("\n", R.round(3).to_string())
mets = R.loc[[f"Run1 seed {s} (+PICA)" for s in [42, 43, 44, 45, 46]]]
print("\nRun1 5-seed mean:", mets.mean().round(3).to_dict())

lo, hi = block_boot(yte, preds[0])
print(f"\nSeed-42 model, 100 m-block bootstrap 95% CI: MAE [{lo[0]:.2f}, {hi[0]:.2f}], R2 [{lo[1]:.2f}, {hi[1]:.2f}]")
lo, hi = block_boot(yte, np.expm1(gb2.predict(Cte)))
print(f"13-ctx LightGBM, 100 m-block bootstrap 95% CI: MAE [{lo[0]:.2f}, {hi[0]:.2f}], R2 [{lo[1]:.2f}, {hi[1]:.2f}]")

print("\nPer-trip (seed-42, +PICA):")
for g in pd.unique(groups):
    ii = groups == g
    mm = metrics(yte[ii], preds[0][ii])
    print(f"  {g:18s} n_win={ii.sum():4d} n_100m={len(np.unique(blocks[ii])):3d}  MAE={mm['MAE']:.2f}  R2={mm['R2']:.2f}  label mean={yte[ii].mean():.2f} sd={yte[ii].std():.2f}")
print("\nTest label bins [0,4) [4,8) [8,14) [14,inf):", np.histogram(yte, [0, 4, 8, 14, 1e9])[0])
e = np.abs(yte - preds[0])
for lo_, hi_ in [(0, 4), (4, 8), (8, 14), (14, 1e9)]:
    ii = (yte >= lo_) & (yte < hi_)
    print(f"  bin [{lo_},{hi_}): n={ii.sum()}, blocks={len(np.unique(blocks[ii]))}, MAE={e[ii].mean():.2f}, mean bias={np.mean(preds[0][ii]-yte[ii]):+.2f}")
print("\nSpearman(speed_mean, y) train/val/test:",
      [round(pd.Series(C[:, 0]).corr(pd.Series(y), method='spearman'), 3) for C, y in [(Ctr, ytr), (Cva, yva), (Cte, yte)]])
print("Label distribution train/val/test mean,median,p90:",
      [(round(float(y.mean()), 2), round(float(np.median(y)), 2), round(float(np.percentile(y, 90)), 2)) for y in [ytr, yva, yte]])
