"""Raw-data integrity audit for the BeamNG IRI corpus (read-only)."""
import os
import numpy as np
import pandas as pd

BASE = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model_work\data\simulation\data\IRI_new_experiments"
rows = []
for car in ["hopper", "sunburst2", "vivace"]:
    for route in sorted(os.listdir(os.path.join(BASE, car))):
        rp = os.path.join(BASE, car, route)
        if not os.path.isdir(rp):
            continue
        for trip in sorted(os.listdir(rp)):
            tp = os.path.join(rp, trip)
            if not os.path.isdir(tp):
                continue
            imu = pd.read_csv(os.path.join(tp, "imu_speed_data.csv"))
            geo = pd.read_csv(os.path.join(tp, "iri_sensor_data.csv"))
            r2 = pd.read_csv(os.path.join(tp, "readings_2.csv"))
            df = imu.merge(geo, on=["sample_number", "sim_time"])
            df = df[(df.pos_x != 0) & (df.road_elevation_left != 0)].reset_index(drop=True)

            ch = ["ax", "ay", "az", "wx", "wy", "wz"]
            imu_dup = (df[ch].diff().abs().sum(axis=1) == 0).iloc[1:].mean()
            pos_dup = ((df.pos_x.diff() == 0) & (df.pos_y.diff() == 0)).iloc[1:].mean()
            moving = df.speed_ms > 1.0
            el_dup_moving = ((df.road_elevation_left.diff() == 0) & moving).iloc[1:].sum() / max(moving.sum(), 1)

            # run lengths of held elevation while moving
            el = df.road_elevation_left.values
            runs, cur = [], 1
            for i in range(1, len(el)):
                if el[i] == el[i - 1] and moving.iloc[i]:
                    cur += 1
                else:
                    runs.append(cur)
                    cur = 1
            runs = np.array(runs)

            # distance axes
            d2d = np.sum(np.hypot(np.diff(df.pos_x), np.diff(df.pos_y)))
            d3d = np.sum(np.sqrt(np.diff(df.pos_x) ** 2 + np.diff(df.pos_y) ** 2 + np.diff(df.pos_z) ** 2))
            dm = df[df.speed_ms >= 1.0]
            dspeed = np.sum(dm.speed_ms.values * 0.01)

            # Speed from position vs reported speed (checks wall-clock vs sim-time)
            pos_speed = np.hypot(np.diff(df.pos_x), np.diff(df.pos_y)) / 0.01
            ratio_series = pd.Series(pos_speed).rolling(100).mean() / df.speed_ms.iloc[1:].reset_index(drop=True).rolling(100).mean()

            seg_iri = r2.groupby("IRI").size()
            rows.append(dict(
                car=car, route=route, trip=trip, n=len(df), minutes=len(df) / 100 / 60,
                km_2d=d2d / 1000, km_speed_int=dspeed / 1000, drift_pct=100 * (dspeed - d2d) / d2d,
                imu_dup_pct=100 * imu_dup, pos_dup_pct=100 * pos_dup, elev_hold_moving_pct=100 * el_dup_moving,
                elev_run_mean=runs[runs > 1].mean() if (runs > 1).any() else 1,
                elev_run_max=runs.max(),
                posspeed_over_speed_med=np.nanmedian(ratio_series[df.speed_ms.iloc[1:].reset_index(drop=True) > 5]),
                speed_kmh_mean=3.6 * df.speed_ms[df.speed_ms > 1].mean(),
                speed_kmh_p95=3.6 * df.speed_ms.quantile(0.95),
                n_segments=len(seg_iri), iri_seg_mean=np.mean(seg_iri.index.values),
                iri_seg_max=np.max(seg_iri.index.values),
                az_mean=df.az.mean(),
            ))

out = pd.DataFrame(rows)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
print(out.round(3).to_string())
out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "audit_raw.csv"), index=False)
print("\nTotals by route:")
print(out.groupby("route")[["minutes", "km_2d", "n_segments"]].sum().round(2))
print("\nTotal km:", out.km_2d.sum().round(2), " total 100m segments:", out.n_segments.sum())
