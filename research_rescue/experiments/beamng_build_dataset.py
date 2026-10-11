"""Build the clean BeamNG window dataset.

Changes w.r.t. the rejected paper's pipeline (all deliberate, see FINAL_EVALUATION_PROTOCOL.md):
  * distance axis = 2-D position (identical to the label pipeline) for BOTH labels and inputs;
  * IMU rows that are exact sample-and-hold duplicates are dropped (fresh samples only);
  * labels are computed EXACTLY for each window from a continuous quarter-car run (no time-weighted
    mixing of neighbouring segments); two label definitions are produced:
        iri_raw     canonical IRI of the raw LiDAR profile (no mesh correction)
        iri_corr    canonical IRI of the profile after the legacy curvature-adaptive correction
        iri_legacy  (evaluation segments only) the legacy fixed-segment label, recomputed with the
                    legacy code exactly as readings_2.csv was produced;
  * evaluation units are NON-overlapping 100 m segments on the legacy segment grid; training windows
    use a 25 m stride (labels exact, so overlap only affects training, never evaluation);
  * no random resampling augmentation (deterministic tensors).
Outputs: data/processed/beamng/{meta.csv, arrays.npz}
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import iri, features as F, legacy_recipe as LR  # noqa: E402
from common.paths import BEAMNG_RAW, PROCESSED, LEGACY_LABEL_CODE  # noqa: E402

sys.path.insert(0, LEGACY_LABEL_CODE)
import iri_calculation as legacy  # noqa: E402

DX = 0.25
WIN = 100.0
STRIDE = 25.0
FS = 50.0
CHANNELS = ["ax", "ay", "az", "wx", "wy", "wz"]


def load_trip(car, route, trip):
    tp = os.path.join(BEAMNG_RAW, car, route, trip)
    df = pd.read_csv(os.path.join(tp, "imu_speed_data.csv")).merge(
        pd.read_csv(os.path.join(tp, "iri_sensor_data.csv")), on=["sample_number", "sim_time"])
    df = df[(df.pos_x != 0.0) & (df.road_elevation_left != 0.0)].reset_index(drop=True)
    cd = np.cumsum(np.hypot(np.diff(df.pos_x, prepend=df.pos_x[0]), np.diff(df.pos_y, prepend=df.pos_y[0])))
    df["cd"] = cd
    return df


def profiles(df):
    cd = df.cd.to_numpy()
    m = np.concatenate([[True], np.diff(cd) > 0])
    grid = np.arange(0, cd.max(), DX)
    out = {}
    for side in ["left", "right"]:
        out[side] = np.interp(grid, cd[m], df[f"road_elevation_{side}"].to_numpy()[m])
    return grid, out


def legacy_fixed_segments(z):
    """Legacy readings_2 labels: 100 m segments from 0 with 20 m lead-in, corrected profile."""
    seg, lead = int(WIN / DX), int(20.0 / DX)
    zc = {s: legacy.apply_250mm_moving_average(legacy.correct_mesh_tessellation(z[s], DX), DX) for s in z}
    n = len(z["left"])
    labels = []
    for s0 in range(0, n - seg + 1, seg):
        a = max(0, s0 - lead)
        vals = [legacy.compute_iri(zc[s][a:s0 + seg], DX, lead_in_samples=(s0 - a))[0] for s in ("left", "right")]
        labels.append(np.mean(vals))
    return np.array(labels)


def main():
    t0 = time.time()
    rows, X6, XZ, FEAT, CTX = [], [], [], [], []
    for car in ["hopper", "sunburst2", "vivace"]:
        for route in ["automation_test_track", "east_coast_usa", "west_coast_usa"]:
            for trip in sorted(os.listdir(os.path.join(BEAMNG_RAW, car, route))):
                if not trip.startswith("trip_"):
                    continue
                df = load_trip(car, route, trip)
                grid, z = profiles(df)
                rs_raw, rs_cor = [], []
                for side in ["left", "right"]:
                    r1, pos = iri.continuous_rectified_slope(z[side], DX)
                    r2, _ = iri.continuous_rectified_slope(legacy.correct_mesh_tessellation(z[side], DX), DX)
                    rs_raw.append(r1); rs_cor.append(r2)
                rs_raw = 0.5 * (rs_raw[0] + rs_raw[1]); rs_cor = 0.5 * (rs_cor[0] + rs_cor[1])
                leg = legacy_fixed_segments(z)
                # fresh IMU samples only (drop exact sample-and-hold duplicates)
                ch = df[CHANNELS].to_numpy()
                fresh = np.concatenate([[True], np.any(np.diff(ch, axis=0) != 0, axis=1)])
                d = df[fresh].reset_index(drop=True)
                t = d.sim_time.to_numpy(); cd = d.cd.to_numpy(); v = d.speed_ms.to_numpy()
                # elevation staleness flag (LiDAR value held while moving)
                el_hold = np.concatenate([[False], np.diff(df.road_elevation_left.to_numpy()) == 0]) & (df.speed_ms.to_numpy() > 1)
                # uniform 50 Hz time grid for physics features; gravity removed by 0.3 Hz high-pass
                tg = np.arange(t[0], t[-1], 1.0 / FS)
                az_g = np.interp(tg, t, d.az.to_numpy())
                adyn = F.remove_gravity(az_g, FS)
                cdg = np.interp(tg, t, cd); vg = np.interp(tg, t, v)
                starts = np.arange(0.0, cd.max() - WIN, STRIDE)
                for st in starts:
                    sel = (cd >= st) & (cd < st + WIN)
                    selg = (cdg >= st) & (cdg < st + WIN)
                    if sel.sum() < 30 or selg.sum() < 50:
                        continue
                    vw = v[sel]
                    if vw.mean() < 1.0:
                        continue
                    # exact labels from continuous RS
                    lab_raw = iri.window_iri(rs_raw, pos, np.array([st]), WIN)[0]
                    lab_cor = iri.window_iri(rs_cor, pos, np.array([st]), WIN)[0]
                    is_eval = (st % WIN) == 0
                    lab_leg = leg[int(st // WIN)] if is_eval and int(st // WIN) < len(leg) else np.nan
                    # spatial tensors (400 x 0.25 m)
                    raw6 = np.stack([F.spatial_resample(cd[sel], d[c].to_numpy()[sel], st) for c in CHANNELS], axis=1)
                    vs = F.spatial_resample(cd[sel], vw, st)
                    leg6 = raw6.copy(); leg6[:, 2] = LR.kinetic_normalise(leg6[:, 2], vs)
                    ctx = LR.extract_context_features(leg6, vs)
                    zsp = F.spatial_resample(cdg[selg], adyn[selg], st)
                    feat = F.window_features(adyn[selg], vg[selg], FS)
                    cx = np.interp(st + WIN / 2, df.cd, df.pos_x); cy = np.interp(st + WIN / 2, df.cd, df.pos_y)
                    selall = (df.cd.to_numpy() >= st) & (df.cd.to_numpy() < st + WIN)
                    rows.append(dict(car=car, map=route, trip=trip, start_m=st, is_eval=bool(is_eval),
                                     iri_raw=lab_raw, iri_corr=lab_cor, iri_legacy=lab_leg,
                                     v_mean=float(vw.mean()), v_std=float(vw.std()), n_fresh=int(sel.sum()),
                                     dur_s=float(t[sel][-1] - t[sel][0]), cx=cx, cy=cy,
                                     elev_hold_frac=float(el_hold[selall].mean()) if selall.any() else np.nan,
                                     max_hold_run_s=float(_max_run(el_hold[selall]) * 0.01) if selall.any() else np.nan))
                    X6.append(leg6.astype(np.float32)); XZ.append(np.stack([zsp, vs], axis=1))
                    FEAT.append(feat); CTX.append(ctx)
                print(f"{car:9s} {route:22s} {trip}: windows so far {len(rows)}  ({time.time()-t0:.0f}s)", flush=True)
    meta = pd.DataFrame(rows)
    meta["cluster"] = (meta["map"] + "_" + (meta.cx // 100).astype(int).astype(str) + "_" + (meta.cy // 100).astype(int).astype(str))
    out = os.path.join(PROCESSED, "beamng"); os.makedirs(out, exist_ok=True)
    meta.to_csv(os.path.join(out, "meta.csv"), index=False)
    np.savez_compressed(os.path.join(out, "arrays.npz"), X_legacy6=np.array(X6), X_zv=np.array(XZ),
                        feat=np.array(FEAT), ctx_legacy=np.array(CTX), feature_names=np.array(F.FEATURE_NAMES))
    print("saved", len(meta), "windows;", int(meta.is_eval.sum()), "evaluation segments")


def _max_run(b):
    best = cur = 0
    for x in b:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


if __name__ == "__main__":
    main()
