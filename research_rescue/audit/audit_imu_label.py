"""Does the vehicle IMU 'feel' the content removed by the mesh correction?
Per 100 m segment: compare how well IMU vibration explains raw-profile IRI vs corrected IRI,
controlling for speed. Also checks what kinetic normalisation does to az (gravity included)."""
import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model\iri_compliant")
import iri_calculation as ic

BASE = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model_work\data\simulation\data\IRI_new_experiments"
DX = 0.25
recs = []
for car in ["hopper", "sunburst2", "vivace"]:
    for route in ["automation_test_track", "east_coast_usa", "west_coast_usa"]:
        for trip in sorted(os.listdir(os.path.join(BASE, car, route))):
            if not trip.startswith("trip_"):
                continue
            tp = os.path.join(BASE, car, route, trip)
            df = pd.read_csv(os.path.join(tp, "imu_speed_data.csv")).merge(
                pd.read_csv(os.path.join(tp, "iri_sensor_data.csv")), on=["sample_number", "sim_time"])
            df = df[(df.pos_x != 0) & (df.road_elevation_left != 0)].reset_index(drop=True)
            cd = np.cumsum(np.hypot(np.diff(df.pos_x, prepend=df.pos_x[0]), np.diff(df.pos_y, prepend=df.pos_y[0])))
            m = np.concatenate([[True], np.diff(cd) > 0])
            grid = np.arange(0, cd.max(), DX)
            prof = {}
            for side in ["left", "right"]:
                z = np.interp(grid, cd[m], df[f"road_elevation_{side}"].values[m])
                prof[side] = (z, ic.correct_mesh_tessellation(z, DX))
            for s in range(80, len(grid) - 400, 400):
                seg = slice(s - 80, s + 400)
                d0, d1 = grid[s], grid[s + 399]
                w = df[(cd >= d0) & (cd < d1)]
                if len(w) < 50 or w.speed_ms.mean() < 3:
                    continue
                iri_raw = np.mean([ic.compute_iri(prof[sd][0][seg], DX, 80)[0] for sd in prof])
                iri_cor = np.mean([ic.compute_iri(prof[sd][1][seg], DX, 80)[0] for sd in prof])
                azd = w.az - w.az.mean()
                v = w.speed_ms.values
                kn = w.az.values * (22.22 / np.maximum(v, 5.0)) ** 2  # exactly as in data_pipeline.py
                recs.append(dict(route=route, car=car, speed=v.mean(), iri_raw=iri_raw, iri_cor=iri_cor,
                                 rms_az=np.sqrt(np.mean(azd ** 2)), rms_wx=np.sqrt(np.mean((w.wx - w.wx.mean()) ** 2)),
                                 kn_mean=kn.mean(), kn_dyn_rms=np.std(kn)))
D = pd.DataFrame(recs)
print(f"segments: {len(D)}")


def r2_ols(y, X):
    X = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return 1 - np.sum((y - X @ b) ** 2) / np.sum((y - y.mean()) ** 2)


D = D[(D.iri_raw > 0) & (D.iri_cor > 0)]
ly = {k: np.log(D[k].values) for k in ["iri_raw", "iri_cor"]}
lv, la, lw = np.log(D.speed.values), np.log(D.rms_az.values + 1e-6), np.log(D.rms_wx.values + 1e-6)
print("\nHow much of each label is explained by the IMU (log-linear OLS)?")
for k in ["iri_raw", "iri_cor"]:
    print(f"  {k}: R2[speed only]={r2_ols(ly[k], [lv]):.3f}  R2[rms_az + speed]={r2_ols(ly[k], [la, lv]):.3f}  "
          f"R2[rms_az + rms_wx + speed]={r2_ols(ly[k], [la, lw, lv]):.3f}")
print("\nWithin-speed-bin Spearman(rms_az, label):")
D["vb"] = pd.cut(D.speed * 3.6, [0, 30, 50, 70, 90, 200])
for vb, g in D.groupby("vb", observed=True):
    if len(g) > 20:
        print(f"  {str(vb):12s} n={len(g):4d}  raw: {spearmanr(g.rms_az, g.iri_raw)[0]:.3f}   corrected: {spearmanr(g.rms_az, g.iri_cor)[0]:.3f}")

print("\nSpeed-roughness confound: Spearman(speed, corrected IRI) =", round(spearmanr(D.speed, D.iri_cor)[0], 3),
      "| Spearman(speed, raw IRI) =", round(spearmanr(D.speed, D.iri_raw)[0], 3))

print("\nKinetic normalisation applied to gravity-including az:")
print("  Spearman(mean of normalised az, speed) =", round(spearmanr(D.kn_mean, D.speed)[0], 3))
print("  mean normalised az at <20 km/h: %.1f m/s^2 | 40-60 km/h: %.1f | >80 km/h: %.1f" % (
    D.kn_mean[D.speed * 3.6 < 20].mean(), D.kn_mean[(D.speed * 3.6 > 40) & (D.speed * 3.6 < 60)].mean(), D.kn_mean[D.speed * 3.6 > 80].mean()))
print("  Spearman(label, mean normalised az) =", round(spearmanr(D.kn_mean, D.iri_cor)[0], 3),
      " vs Spearman(label, rms_az raw) =", round(spearmanr(D.rms_az, D.iri_cor)[0], 3))
# exponent of physical speed scaling of rms_az at fixed roughness
b = np.linalg.lstsq(np.column_stack([np.ones(len(D)), np.log(D.speed), np.log(D.iri_raw)]), np.log(D.rms_az + 1e-6), rcond=None)[0]
print(f"\nEmpirical scaling: rms_az ~ speed^{b[1]:.2f} * IRI_raw^{b[2]:.2f}   (paper assumes speed^2)")
b = np.linalg.lstsq(np.column_stack([np.ones(len(D)), np.log(D.speed), np.log(D.iri_cor)]), np.log(D.rms_az + 1e-6), rcond=None)[0]
print(f"Empirical scaling: rms_az ~ speed^{b[1]:.2f} * IRI_cor^{b[2]:.2f}")
D.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "imu_label_segments.csv"), index=False)
