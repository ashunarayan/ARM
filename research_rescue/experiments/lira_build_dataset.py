"""Build the LiRA-CD real-car evaluation dataset (100 m segment x pass units).

For every route/direction and every GreenMobility (Renault Zoe) pass:
  1. AutoPi acceleration (irregular 56-260 Hz, 0.01 g resolution) -> common/preprocess.vertical_dynamic:
     200 Hz interpolation, zero-phase 20 Hz low-pass, 50 Hz, gravity alignment on the pass-mean direction
     (removes the static mounting tilt), m/s^2, 0.3 Hz high-pass;
  2. speed from the CAN bus (obd.spd_veh, km/h -> m/s);
  3. GPS (1-4 Hz) map-matched to the P79 profile track of the same route/direction (nearest vertex with a
     heading constraint; fixes > 20 m from the track rejected; monotone progression enforced); chainage
     interpolated in time;
  4. 100 m units on the P79 chainage grid via common/preprocess.extract_units (identical to the simulator).
Labels: P79 IRI (mean of both wheel paths) recomputed from the published P79 profile with the validated
implementation; the P79-reported value is carried along where the profile/IRI files are consistent.
Outputs: data/processed/lira/{units.csv, arrays.npz, build_status.json}
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import lira, geo, features as F, preprocess as PP  # noqa: E402
from common.paths import PROCESSED, LIRA_CAR, LIRA_ROUTES, LIRA_DIRS  # noqa: E402


def task_units(readme_path: str) -> dict:
    """TaskId -> telematics unit (vehicle) from the LiRA-CD car readme table."""
    out = {}
    for line in open(readme_path, encoding="latin-1"):
        m = re.match(r"^(\d{4,5})\s+(TMU#\d+|-)\s", line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def complete(name: str) -> bool:
    man = {f["name"]: f["size"] for f in json.load(open(os.path.join(LIRA_CAR, "_manifest.json")))}
    p = os.path.join(LIRA_CAR, name)
    return os.path.exists(p) and os.path.getsize(p) == man.get(name, -1)


def chainage_from_gps(gps, poly, lat0, lon0, t50, max_lat=20.0):
    gps = gps[np.isfinite(gps).all(1)]
    if len(gps) < 10:
        return []
    xy = geo.to_local_xy(gps[:, 1], gps[:, 2], lat0, lon0)
    d = np.diff(xy, axis=0)
    hd = np.arctan2(d[:, 1], d[:, 0]); hd = np.concatenate([hd, hd[-1:]])
    step = np.concatenate([np.hypot(d[:, 0], d[:, 1]), [1.0]])
    for i in range(1, len(hd)):            # heading undefined when (nearly) stationary: carry forward
        if step[i] < 0.5:
            hd[i] = hd[i - 1]
    ch, lat_d = poly.match(xy, heading=hd)
    ok = np.isfinite(lat_d) & (lat_d < max_lat)
    if ok.sum() < 10:
        return []
    tg, cg, lg = gps[ok, 0], ch[ok], lat_d[ok]
    # Split into runs of physically plausible progression (ring roads/loops: the chainage wraps around; GPS
    # outliers: isolated jumps). Each run yields its own chainage track; units are extracted per run.
    cuts = [0]
    for i in range(1, len(cg)):
        dc, dt = cg[i] - cg[i - 1], max(tg[i] - tg[i - 1], 1e-3)
        if dc < -5.0 or dc > 50.0 + 45.0 * dt:
            cuts.append(i)
    cuts.append(len(cg))
    runs = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < 10:
            continue
        ta, ca, la = tg[a:b], np.maximum.accumulate(cg[a:b]), lg[a:b]
        c50 = np.full(len(t50), np.nan); lat50 = np.full(len(t50), np.nan)
        inside = (t50 >= ta[0]) & (t50 <= ta[-1])
        c50[inside] = np.interp(t50[inside], ta, ca); lat50[inside] = np.interp(t50[inside], ta, la)
        runs.append((c50, lat50))
    return runs


def process_pass(g, poly, lat0, lon0, seg_ref):
    if not all(k in g for k in ("acc.xyz", "obd.spd_veh", "gps")):   # some passes contain GPS only
        return None, None, None
    if g["acc.xyz"].shape[0] < 500 or g["obd.spd_veh"].shape[0] < 10 or g["gps"].shape[0] < 10:   # empty/short signals
        return None, None, None
    acc = g["acc.xyz"][:]
    if len(acc) < 500:
        return [], [], []
    t50, a_dyn = PP.vertical_dynamic(acc[:, 0], acc[:, 1:4])
    spd = g["obd.spd_veh"][:]
    v50 = np.interp(t50, spd[:, 0], spd[:, 1] / 3.6)
    units, feats, seqs = [], [], []
    for k, (c50, lat50) in enumerate(chainage_from_gps(g["gps"][:], poly, lat0, lon0, t50)):
        u_, f_, s_ = PP.extract_units(a_dyn, v50, c50, seg_ref.start_m.to_numpy())
        for u in u_:
            sel = (c50 >= u["start_m"]) & (c50 < u["start_m"] + PP.SEG)
            u["lateral_m"] = float(np.nanmedian(lat50[sel])); u["run"] = k
        units += u_; feats += f_; seqs += s_
    return units, feats, seqs


def main():
    t0 = time.time()
    seg_all = pd.read_csv(os.path.join(PROCESSED, "lira", "p79_segments_100m.csv"))
    units_map = task_units(os.path.join(LIRA_CAR, "readme.txt"))
    rows, FEAT, XZ = [], [], []
    status = {}
    for route in LIRA_ROUTES:
        for direction in LIRA_DIRS:
            fname = f"{route}_{direction}.hdf5"
            if not complete(fname):
                status[fname] = "incomplete download - skipped"; print(fname, "incomplete, skipped"); continue
            zp = lira.load_zp(route, direction).dropna(subset=["lat", "lon"])
            lat0, lon0 = zp.lat.median(), zp.lon.median()
            poly = geo.Polyline(geo.to_local_xy(zp.lat.to_numpy(), zp.lon.to_numpy(), lat0, lon0), zp.dist.to_numpy(), step=1.0)
            seg_ref = seg_all[(seg_all.route == route) & (seg_all.direction == direction) & seg_all.mri_profile.notna()]
            seg_by_start = seg_ref.set_index("start_m")
            n_pass = n_nosignal = n_nounits = 0
            with h5py.File(os.path.join(LIRA_CAR, fname), "r") as f:
                for task in f["GM"].keys():
                    for p in f["GM"][task].keys():
                        units, feats, seqs = process_pass(f["GM"][task][p], poly, lat0, lon0, seg_ref)
                        if units is None:
                            n_nosignal += 1; continue
                        if not units:
                            n_nounits += 1; continue
                        n_pass += 1
                        for u, ft, sq in zip(units, feats, seqs):
                            s = seg_by_start.loc[u["start_m"]]
                            rows.append(dict(route=route, direction=direction, task=task, pass_id=p,
                                             unit=units_map.get(task, "?"), segment=f"{route}_{direction}_{int(u['start_m'])}",
                                             mri=s.mri_profile, mri_reported=s.mri_reported if s.consistent_reported else np.nan,
                                             mri_aran=s.mri_aran, lat=s.lat, lon=s.lon, **u))
                            FEAT.append(ft); XZ.append(sq)
            status[fname] = dict(passes_used=n_pass, passes_without_acc_or_speed=n_nosignal, passes_without_valid_units=n_nounits)
            print(f"{fname}: {n_pass} passes, units so far {len(rows)} ({time.time()-t0:.0f}s)", flush=True)
    U = pd.DataFrame(rows)
    out = os.path.join(PROCESSED, "lira"); os.makedirs(out, exist_ok=True)
    U.to_csv(os.path.join(out, "units.csv"), index=False)
    np.savez_compressed(os.path.join(out, "arrays.npz"), feat=np.array(FEAT), X_zv=np.array(XZ),
                        feature_names=np.array(F.FEATURE_NAMES))
    json.dump(status, open(os.path.join(out, "build_status.json"), "w"), indent=1)
    print("saved", len(U), "segment-pass units;", U.segment.nunique() if len(U) else 0, "distinct segments")


if __name__ == "__main__":
    main()
