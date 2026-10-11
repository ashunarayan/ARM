"""(1) Spatial overlap of val/test trips on automation_test_track.
(2) Is the 'mesh tessellation' profile jitter fixed geometry or a sampling-timing artifact?"""
import os
import sys
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.path.insert(0, r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model\iri_compliant")
import iri_calculation as ic  # the exact label code used for readings_2.csv

BASE = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model_work\data\simulation\data\IRI_new_experiments"


def load(car, route, trip):
    tp = os.path.join(BASE, car, route, trip)
    df = pd.read_csv(os.path.join(tp, "imu_speed_data.csv")).merge(
        pd.read_csv(os.path.join(tp, "iri_sensor_data.csv")), on=["sample_number", "sim_time"])
    return df[(df.pos_x != 0) & (df.road_elevation_left != 0)].reset_index(drop=True)


# ---------------- (1) spatial overlap ----------------
print("=== (1) Spatial overlap on automation_test_track ===")
val = {c: load(c, "automation_test_track", "trip_1") for c in ["hopper", "sunburst2", "vivace"]}
val_xy = np.vstack([v[["pos_x", "pos_y"]].values for v in val.values()])
tree = cKDTree(val_xy)
tests = [("hopper", "trip_2"), ("hopper", "trip_3"), ("sunburst2", "trip_2"), ("vivace", "trip_2")]
for car, trip in tests:
    t = load(car, "automation_test_track", trip)
    t = t[t.speed_ms > 1]
    d, _ = tree.query(t[["pos_x", "pos_y"]].values)
    # also overlap with the SAME car's val trip
    own = cKDTree(val[car][["pos_x", "pos_y"]].values)
    d_own, _ = own.query(t[["pos_x", "pos_y"]].values)
    print(f"{car:10s} {trip}: within 2 m of ANY val trip: {100*np.mean(d<2):5.1f}%  within 5 m: {100*np.mean(d<5):5.1f}%"
          f" | within 2 m of SAME-car val trip: {100*np.mean(d_own<2):5.1f}%")

# label similarity at matched locations: segment-level IRI of test vs val at nearest location
print("\nLabel agreement between test windows and spatially matched val samples:")
val_r2 = []
for c in ["hopper", "sunburst2", "vivace"]:
    r = pd.read_csv(os.path.join(BASE, c, "automation_test_track", "trip_1", "readings_2.csv"))
    g = load(c, "automation_test_track", "trip_1")
    m = g.merge(r[["sample_number", "IRI"]], on="sample_number")
    val_r2.append(m[["pos_x", "pos_y", "IRI"]])
val_r2 = pd.concat(val_r2)
tree2 = cKDTree(val_r2[["pos_x", "pos_y"]].values)
all_t, all_v = [], []
for car, trip in tests:
    r = pd.read_csv(os.path.join(BASE, car, "automation_test_track", trip, "readings_2.csv"))
    g = load(car, "automation_test_track", trip)
    m = g.merge(r[["sample_number", "IRI"]], on="sample_number")
    m = m[m.speed_ms > 1]
    d, idx = tree2.query(m[["pos_x", "pos_y"]].values)
    ok = d < 2
    all_t.append(m.IRI.values[ok]); all_v.append(val_r2.IRI.values[idx[ok]])
all_t, all_v = np.concatenate(all_t), np.concatenate(all_v)
print(f"  matched samples: {len(all_t)}; Pearson r(test IRI, nearest-val IRI) = {np.corrcoef(all_t, all_v)[0,1]:.3f}")
ss_res = np.sum((all_t - all_v) ** 2); ss_tot = np.sum((all_t - all_t.mean()) ** 2)
print(f"  'nearest val label' as a predictor of test label: R2 = {1-ss_res/ss_tot:.3f}, MAE = {np.mean(np.abs(all_t-all_v)):.3f}")

# ---------------- (2) jitter vs speed & grade ----------------
print("\n=== (2) Profile jitter: geometry or timing? ===")
recs = []
for car in ["hopper", "sunburst2", "vivace"]:
    for route in ["automation_test_track", "east_coast_usa", "west_coast_usa"]:
        for trip in sorted(os.listdir(os.path.join(BASE, car, route))):
            if not trip.startswith("trip_"):
                continue
            df = load(car, route, trip)
            dxp = np.diff(df.pos_x.values, prepend=df.pos_x.values[0])
            dyp = np.diff(df.pos_y.values, prepend=df.pos_y.values[0])
            cd = np.cumsum(np.hypot(dxp, dyp))
            mask = np.concatenate([[True], np.diff(cd) > 0])
            grid = np.arange(0, cd.max(), 0.25)
            z = np.interp(grid, cd[mask], df.road_elevation_left.values[mask])
            spd = np.interp(grid, cd[mask], df.speed_ms.values[mask])
            zc = ic.correct_mesh_tessellation(z, 0.25)
            k = 21  # 5 m MA
            zs = np.convolve(np.pad(z, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
            kd = 41  # 10 m MA for grade
            zd = np.convolve(np.pad(z, (kd // 2, kd // 2), mode="edge"), np.ones(kd) / kd, mode="valid")
            grade = np.gradient(zd, 0.25)
            seg = 400
            for s in range(80, len(grid) - seg, seg):
                sl = slice(s, s + seg)
                lead = slice(s - 80, s + seg)
                iri_raw, _ = ic.compute_iri(z[lead], 0.25, 80)
                iri_cor, _ = ic.compute_iri(zc[lead], 0.25, 80)
                recs.append(dict(car=car, route=route, trip=trip,
                                 jitter=np.sqrt(np.mean((z[sl] - zs[sl]) ** 2)),
                                 abs_grade=np.mean(np.abs(grade[sl])), speed=np.mean(spd[sl]),
                                 iri_raw=iri_raw, iri_cor=iri_cor))
J = pd.DataFrame(recs)
J = J[(J.speed > 3) & (J.abs_grade > 1e-4) & (J.jitter > 0)]
X = np.column_stack([np.ones(len(J)), np.log(J.abs_grade), np.log(J.speed)])
coef, *_ = np.linalg.lstsq(X, np.log(J.jitter), rcond=None)
pred = X @ coef
r2 = 1 - np.sum((np.log(J.jitter) - pred) ** 2) / np.sum((np.log(J.jitter) - np.log(J.jitter).mean()) ** 2)
print(f"segments: {len(J)}")
print(f"log(jitter_rms) = {coef[0]:.2f} + {coef[1]:.2f}*log|grade| + {coef[2]:.2f}*log(speed)   (R2={r2:.3f})")
J["gs"] = J.abs_grade * J.speed
print("Spearman rho(jitter, |grade|*speed) =", round(J[["jitter", "gs"]].corr("spearman").iloc[0, 1], 3))
print("Spearman rho(jitter, |grade|)       =", round(J[["jitter", "abs_grade"]].corr("spearman").iloc[0, 1], 3))
print("Spearman rho(jitter, speed)         =", round(J[["jitter", "speed"]].corr("spearman").iloc[0, 1], 3))
J["iri_removed"] = J.iri_raw - J.iri_cor
print("Spearman rho(IRI removed by correction, |grade|*speed) =", round(J[["iri_removed", "gs"]].corr("spearman").iloc[0, 1], 3))
print("\nIRI change due to correction (m/km): median %.2f, mean %.2f, p90 %.2f, max %.2f; segments changed >0.5: %.1f%%" % (
    J.iri_removed.median(), J.iri_removed.mean(), J.iri_removed.quantile(0.9), J.iri_removed.max(), 100 * np.mean(J.iri_removed > 0.5)))
print("\nBy grade x speed quintile:")
J["q"] = pd.qcut(J.gs, 5, labels=False)
print(J.groupby("q")[["abs_grade", "speed", "jitter", "iri_raw", "iri_cor", "iri_removed"]].median().round(4).to_string())
J.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "jitter_segments.csv"), index=False)
