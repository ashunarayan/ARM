"""Does the sim-trained model add anything over trivial signals on PVS?"""
import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_predict

PVS = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model_work\data\raw\multi_class_kaggle"
P = pd.read_csv(r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model\pvs_comparision\output\pvs_all_predictions.csv", keep_default_na=False)

feats = []
for t in range(1, 10):
    L = pd.read_csv(os.path.join(PVS, f"PVS {t}", "dataset_gps_mpu_left.csv"))
    R = pd.read_csv(os.path.join(PVS, f"PVS {t}", "dataset_gps_mpu_right.csv"))
    order = np.argsort(L.timestamp.values, kind="stable")
    az = ((L.acc_z_dashboard.values + R.acc_z_dashboard.values) / 2)[order]
    azb = ((L.acc_z_below_suspension.values + R.acc_z_below_suspension.values) / 2)[order]
    for _, w in P[P.trip_num == t].iterrows():
        seg = az[int(w.start_sample_idx): int(w.end_sample_idx) + 1]
        segb = azb[int(w.start_sample_idx): int(w.end_sample_idx) + 1]
        feats.append(dict(rms_az=np.std(seg), rms_az_below=np.std(segb)))
P = pd.concat([P.reset_index(drop=True), pd.DataFrame(feats)], axis=1)
P = P[(P.speed_bump == "None") & (P.surface_type != "Unknown") & (P.road_quality != "Unknown")].copy()
print("clean windows:", len(P))
P["route"] = ((P.trip_num - 1) % 3)  # trips {1,4,7}, {2,5,8}, {3,6,9} share a route
print("windows per route:", P.route.value_counts().sort_index().to_dict())

scores = {"model IRI (calibrated)": P.iri_calibrated, "model IRI (raw)": P.iri_raw,
          "-speed only": -P.avg_speed_ms, "RMS az dashboard (no model)": P.rms_az,
          "RMS az / speed^0.5": P.rms_az / np.sqrt(P.avg_speed_ms)}
tasks = {
    "asphalt vs cobble+dirt": (P.surface_type != "Asphalt").astype(int),
    "Good vs Regular+Bad (all)": (P.road_quality != "Good").astype(int),
}
print("\nAUC (higher = better separation):")
print(f"{'score':32s}" + "".join(f"{k:>28s}" for k in tasks) + f"{'Spearman w/ quality 0/1/2':>28s}")
qual = P.road_quality.map({"Good": 0, "Regular": 1, "Bad": 2})
for name, s in scores.items():
    row = f"{name:32s}"
    for k, y in tasks.items():
        row += f"{roc_auc_score(y, s):28.3f}"
    row += f"{spearmanr(s, qual)[0]:28.3f}"
    print(row)

print("\nWithin non-asphalt only (Regular vs Bad; the paper's claimed 'minor inversion'):")
na = P[P.surface_type != "Asphalt"]
yb = (na.road_quality == "Bad").astype(int)
for name, s in scores.items():
    print(f"  {name:32s} AUC Bad-vs-Regular = {roc_auc_score(yb, s.loc[na.index]):.3f}  (n_bad={yb.sum()}, n_reg={len(yb)-yb.sum()})")

print("\nAsphalt Regular windows (the only within-asphalt quality evidence):")
print(P[(P.surface_type == "Asphalt") & (P.road_quality == "Regular")][["trip_num", "route", "latitude", "longitude", "avg_speed_kmh", "iri_calibrated", "rms_az"]].round(4).to_string())

# Incremental value of the model over speed + raw vibration, route-grouped CV (leave-one-route-out)
y = tasks["asphalt vs cobble+dirt"].values
g = P.route.values
def cv_auc(X):
    p = cross_val_predict(LogisticRegression(max_iter=1000), X, y, groups=g, cv=GroupKFold(3), method="predict_proba")[:, 1]
    return roc_auc_score(y, p)
Xs = np.column_stack([np.log(P.avg_speed_ms)])
Xv = np.column_stack([np.log(P.avg_speed_ms), np.log(P.rms_az)])
Xm = np.column_stack([np.log(P.avg_speed_ms), np.log(P.rms_az), np.log(P.iri_raw)])
print("\nLeave-one-route-out logistic AUC, asphalt vs non-asphalt:")
print(f"  speed only: {cv_auc(Xs):.3f} | speed + RMS az: {cv_auc(Xv):.3f} | speed + RMS az + model IRI: {cv_auc(Xm):.3f}")
print("\nSpearman(model IRI calibrated, speed) =", round(spearmanr(P.iri_calibrated, P.avg_speed_ms)[0], 3),
      "| Spearman(model IRI, RMS az) =", round(spearmanr(P.iri_calibrated, P.rms_az)[0], 3))
print("Mean speed by surface (km/h):", P.groupby("surface_type").avg_speed_kmh.mean().round(1).to_dict())

# Repeatability across the 3 trips on each route (the paper's 'spatial repeatability' claim) vs. RMS az
from scipy.spatial import cKDTree
print("\nCross-trip repeatability at matched locations (<25 m), same route:")
for r in range(3):
    trips = sorted(P[P.route == r].trip_num.unique())
    for a, b in [(trips[0], trips[1]), (trips[0], trips[2]), (trips[1], trips[2])]:
        A, B = P[P.trip_num == a], P[P.trip_num == b]
        # convert lat/lon to meters (local)
        to_xy = lambda D: np.column_stack([D.latitude * 111_000, D.longitude * 111_000 * np.cos(np.deg2rad(-27.7))])
        d, idx = cKDTree(to_xy(B)).query(to_xy(A))
        ok = d < 25
        ia, ib = A.index[ok], B.index[idx[ok]]
        print(f"  route {r} trips {a}-{b}: n={ok.sum():3d}  Spearman model={spearmanr(P.loc[ia,'iri_raw'], P.loc[ib,'iri_raw'])[0]:.3f}  "
              f"RMS az={spearmanr(P.loc[ia,'rms_az'], P.loc[ib,'rms_az'])[0]:.3f}  speed={spearmanr(P.loc[ia,'avg_speed_ms'], P.loc[ib,'avg_speed_ms'])[0]:.3f}")
