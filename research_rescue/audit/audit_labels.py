"""Label validity: correction coverage, hyperparameter sensitivity, cross-run repeatability."""
import os
import sys
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.path.insert(0, r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model\iri_compliant")
import iri_calculation as ic

BASE = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model_work\data\simulation\data\IRI_new_experiments"
DX = 0.25


def load(car, route, trip):
    tp = os.path.join(BASE, car, route, trip)
    df = pd.read_csv(os.path.join(tp, "imu_speed_data.csv")).merge(
        pd.read_csv(os.path.join(tp, "iri_sensor_data.csv")), on=["sample_number", "sim_time"])
    return df[(df.pos_x != 0) & (df.road_elevation_left != 0)].reset_index(drop=True)


def profile(df, side="left"):
    cd = np.cumsum(np.hypot(np.diff(df.pos_x, prepend=df.pos_x[0]), np.diff(df.pos_y, prepend=df.pos_y[0])))
    m = np.concatenate([[True], np.diff(cd) > 0])
    grid = np.arange(0, cd.max(), DX)
    z = np.interp(grid, cd[m], df[f"road_elevation_{side}"].values[m])
    x = np.interp(grid, cd[m], df.pos_x.values[m])
    y = np.interp(grid, cd[m], df.pos_y.values[m])
    v = np.interp(grid, cd[m], df.speed_ms.values[m])
    return grid, z, x, y, v


def alpha_of(z, win=10.0, thr=1.5e-4):
    k = int(round(win / DX)) | 1
    zd = np.convolve(np.pad(z, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
    c = np.zeros_like(z)
    c[1:-1] = np.abs(zd[2:] - 2 * zd[1:-1] + zd[:-2]) / DX ** 2
    c = np.convolve(np.pad(c, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
    return np.clip((c - thr) / (5 * thr), 0, 1)


def correct(z, win_s, thr):
    ic.ANTI_TESS_WINDOW_M, ic.CURVATURE_THRESHOLD = win_s, thr
    out = ic.correct_mesh_tessellation(z, DX)
    ic.ANTI_TESS_WINDOW_M, ic.CURVATURE_THRESHOLD = 5.0, 1.5e-4
    return out


# ---- (a) coverage + (b) hyperparameter sensitivity ----
alphas, sens = [], []
trips = [(c, r, t) for c in ["hopper", "sunburst2", "vivace"]
         for r in ["automation_test_track", "east_coast_usa", "west_coast_usa"]
         for t in sorted(os.listdir(os.path.join(BASE, c, r))) if t.startswith("trip_")]
cache = {}
for c, r, t in trips:
    df = load(c, r, t)
    g, z, x, y, v = profile(df)
    cache[(c, r, t)] = (g, z, x, y, v)
    a = alpha_of(z)
    alphas.append(a)
    z_a = correct(z, 5.0, 1.5e-4)   # readings_2 (paper)
    z_b = correct(z, 6.0, 1.0e-4)   # readings_3 variant
    z_c = correct(z, 5.0, 3.0e-4)   # 2x threshold
    for s in range(80, len(g) - 400, 400):
        seg = slice(s - 80, s + 400)
        sens.append(dict(raw=ic.compute_iri(z[seg], DX, 80)[0], paper=ic.compute_iri(z_a[seg], DX, 80)[0],
                         r3=ic.compute_iri(z_b[seg], DX, 80)[0], thr2x=ic.compute_iri(z_c[seg], DX, 80)[0]))
A = np.concatenate(alphas)
print("=== (a) Correction coverage over the whole corpus (0.25 m grid points) ===")
print(f"alpha == 0 (untouched): {100*np.mean(A==0):.1f}%   alpha >= 0.5: {100*np.mean(A>=0.5):.1f}%   alpha == 1 (fully smoothed): {100*np.mean(A==1):.1f}%")

S = pd.DataFrame(sens)
print("\n=== (b) Label sensitivity to correction hyperparameters (per 100 m segment) ===")
print(S.describe().loc[["mean", "50%", "max"]].round(2).to_string())
for col in ["r3", "thr2x", "raw"]:
    d = S[col] - S.paper
    print(f"paper vs {col:6s}: mean |diff| = {d.abs().mean():.2f} m/km, Spearman = {S[[col,'paper']].corr('spearman').iloc[0,1]:.3f}, "
          f"class change (bins 0-4/4-8/8-14/14+): {100*np.mean(np.digitize(S[col],[4,8,14]) != np.digitize(S.paper,[4,8,14])):.1f}%")

# ---- (c) cross-run repeatability of labels on identical road stretches ----
print("\n=== (c) Label repeatability: same 100 m stretch, different runs (automation_test_track) ===")
pairs = [(("hopper", "trip_2"), ("hopper", "trip_1")), (("vivace", "trip_2"), ("vivace", "trip_1")),
         (("sunburst2", "trip_2"), ("sunburst2", "trip_1")), (("hopper", "trip_2"), ("vivace", "trip_1")),
         (("vivace", "trip_2"), ("sunburst2", "trip_1")), (("hopper", "trip_1"), ("vivace", "trip_1"))]
out = []
for (ca, ta), (cb, tb) in pairs:
    ga, za, xa, ya, va = cache[(ca, "automation_test_track", ta)]
    gb, zb, xb, yb, vb = cache[(cb, "automation_test_track", tb)]
    za_c, zb_c = correct(za, 5.0, 1.5e-4), correct(zb, 5.0, 1.5e-4)
    tree = cKDTree(np.column_stack([xb, yb]))
    d, idx = tree.query(np.column_stack([xa, ya]))
    for s in range(80, len(ga) - 400, 400):
        seg = slice(s - 80, s + 400)
        ii = idx[seg]
        if np.max(d[seg]) > 1.5 or np.any(np.diff(ii) < 0) or (ii[-1] - ii[0]) < 0.9 * 480 or (ii[-1] - ii[0]) > 1.1 * 480:
            continue
        zb_on_a = zb[ii]; zbc_on_a = zb_c[ii]
        out.append(dict(pair=f"{ca}{ta[-1]}-{cb}{tb[-1]}",
                        iri_a_raw=ic.compute_iri(za[seg], DX, 80)[0], iri_b_raw=ic.compute_iri(zb_on_a, DX, 80)[0],
                        iri_a_cor=ic.compute_iri(za_c[seg], DX, 80)[0], iri_b_cor=ic.compute_iri(zbc_on_a, DX, 80)[0],
                        speed_a=va[seg].mean(), speed_b=vb[ii].mean(),
                        prof_rms_diff_mm=1000 * np.std((za[seg] - za[seg].mean()) - (zb_on_a - zb_on_a.mean()))))
R = pd.DataFrame(out)
print(f"matched 100 m stretches: {len(R)}")
for kind in ["raw", "cor"]:
    a, b = R[f"iri_a_{kind}"], R[f"iri_b_{kind}"]
    r = np.corrcoef(a, b)[0, 1]
    icc_like = 1 - np.mean((a - b) ** 2) / (np.var(np.concatenate([a, b])) * 2)
    print(f"{kind:3s}: Pearson r = {r:.3f}, mean |diff| = {np.mean(np.abs(a-b)):.2f} m/km, median |diff| = {np.median(np.abs(a-b)):.2f}, "
          f"rel |diff| median = {100*np.median(np.abs(a-b)/((a+b)/2)):.0f}%, agreement-R2 = {icc_like:.3f}")
R["dv"] = (R.speed_a - R.speed_b).abs()
R["dcor"] = (R.iri_a_cor - R.iri_b_cor).abs()
R["draw"] = (R.iri_a_raw - R.iri_b_raw).abs()
print("Spearman(|label diff| corrected, |speed diff|) =", round(R[["dcor", "dv"]].corr("spearman").iloc[0, 1], 3))
print("Spearman(|label diff| raw, |speed diff|)       =", round(R[["draw", "dv"]].corr("spearman").iloc[0, 1], 3))
print("per-pair Pearson r (corrected):")
print(R.groupby("pair").apply(lambda q: pd.Series(dict(n=len(q), r_cor=np.corrcoef(q.iri_a_cor, q.iri_b_cor)[0, 1],
                                                          mad_cor=np.mean(np.abs(q.iri_a_cor - q.iri_b_cor)),
                                                          r_raw=np.corrcoef(q.iri_a_raw, q.iri_b_raw)[0, 1]))).round(3).to_string())
R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "label_repeatability.csv"), index=False)
