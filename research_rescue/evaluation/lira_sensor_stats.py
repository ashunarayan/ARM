"""Sensor statistics of the LiRA-CD car files (no labels used): per-pass nominal accelerometer rate (1 / median
sample interval) and effective mean rate (including gaps), quantisation step, and static mounting tilt (angle between
the pass-mean acceleration and the device z axis). Written to results/lira_sensor_stats.json.

Note: the simulator's telematics sensor configuration (config/sim_ranges.json, 55-62 Hz, tilt s.d. 6 deg) was set
from a preliminary inspection before this script existed; see CHANGELOG (2026-10-02) for the discrepancy."""
from __future__ import annotations

import json
import os
import sys

import h5py
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.paths import LIRA_CAR, LIRA_ROUTES, LIRA_DIRS, RESULTS  # noqa: E402


def main():
    rows = []
    avail = {"all_signals": 0, "gps_only": 0, "no_speed": 0, "other": 0}
    for route in LIRA_ROUTES:
        for direction in LIRA_DIRS:
            fname = os.path.join(LIRA_CAR, f"{route}_{direction}.hdf5")
            if not os.path.exists(fname):
                continue
            with h5py.File(fname, "r") as f:
                for task in f["GM"].keys():
                    for p in f["GM"][task].keys():
                        g = f["GM"][task][p]
                        n = lambda k: g[k].shape[0] if k in g else 0
                        has_a, has_s, has_g = n("acc.xyz") >= 500, n("obd.spd_veh") >= 10, n("gps") >= 10
                        key = ("all_signals" if has_a and has_s and has_g else "gps_only" if has_g and not has_a and not has_s
                               else "no_speed" if has_a and has_g and not has_s else "other")
                        avail[key] += 1
                        if "acc.xyz" not in g or g["acc.xyz"].shape[0] < 500:
                            continue
                        acc = g["acc.xyz"][:]
                        dt = np.diff(acc[:, 0])
                        u = np.unique(acc[:20000, 3]); du = np.diff(u)
                        m = acc[:, 1:4].mean(0)
                        rate = lambda key: (float(1.0 / np.median(np.diff(g[key][:, 0])[np.diff(g[key][:, 0]) > 0]))
                                            if key in g and g[key].shape[0] > 10 else float("nan"))
                        rows.append(dict(route=route, direction=direction, task=task, pass_id=p, n=len(acc),
                                         gps_hz=rate("gps"), speed_hz=rate("obd.spd_veh"),
                                         nominal_hz=float(1.0 / np.median(dt[dt > 0])),
                                         mean_hz=float((len(acc) - 1) / (acc[-1, 0] - acc[0, 0])),
                                         lsb_g=float(du[du > 0].min()) if (du > 0).any() else float("nan"),
                                         tilt_deg=float(np.degrees(np.arccos(abs(m[2]) / np.linalg.norm(m))))))
    nom = np.array([r["nominal_hz"] for r in rows]); mean = np.array([r["mean_hz"] for r in rows])
    lsb = np.array([r["lsb_g"] for r in rows]); tilt = np.array([r["tilt_deg"] for r in rows])
    low = nom < 100
    out = dict(n_passes=len(rows), signal_availability=avail,
               nominal_hz_low_cluster=float(np.median(nom[low])), nominal_hz_high_cluster=float(np.median(nom[~low])),
               share_passes_low_cluster=float(low.mean()),
               mean_hz_min=float(mean.min()), mean_hz_max=float(mean.max()),
               share_passes_lsb_0p01g=float(np.mean(np.isclose(lsb, 0.01, atol=1e-4))), lsb_g_min=float(np.nanmin(lsb)),
               tilt_deg_median=float(np.median(tilt)), tilt_deg_p95=float(np.percentile(tilt, 95)), tilt_deg_max=float(tilt.max()),
               gps_hz_min=float(np.nanmin([r["gps_hz"] for r in rows])), gps_hz_max=float(np.nanmax([r["gps_hz"] for r in rows])),
               gps_hz_median=float(np.nanmedian([r["gps_hz"] for r in rows])),
               speed_hz_min=float(np.nanmin([r["speed_hz"] for r in rows])), speed_hz_max=float(np.nanmax([r["speed_hz"] for r in rows])),
               speed_hz_median=float(np.nanmedian([r["speed_hz"] for r in rows])),
               per_pass=rows)
    json.dump(out, open(os.path.join(RESULTS, "lira_sensor_stats.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "per_pass"}, indent=1))


if __name__ == "__main__":
    main()
