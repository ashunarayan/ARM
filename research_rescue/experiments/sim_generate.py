"""Generate simulated datasets with the parametric half-car + sensor model (config/sim_ranges.json).

Datasets (data/processed/sim/<name>_{meta.csv,arrays.npz}):
  p79_train     every LiRA-CD P79 profile (mean of both wheel paths) driven once by each of 30 TRAIN vehicles
  p79_test      the same profiles driven by 15 TEST vehicles (disjoint random draws)
  iso_train     40 synthetic ISO-8608-type routes (4 km) x 6 TRAIN vehicles
  iso_test      15 held-out synthetic routes x 6 TEST vehicles
  sweep_iso     10 held-out synthetic routes x 6 TEST vehicles x constant speeds {20,40,60,80,100,110} km/h
  sweep_p79     all P79 profiles x 2 TEST vehicles x the same constant speeds
  region_train  the 40 training routes driven by 6 LOW-f_s vehicles (f_s <= 1.25 Hz)
  region_test   the 15 held-out routes driven by 4 HIGH-f_s and 4 new LOW-f_s vehicles
  iso_test_seenveh  the 15 held-out routes driven by 6 TRAIN vehicles (seen-vehicle reference)
  p79_train_fixedvehicle / p79_train_idealsensor  ablations: no vehicle randomisation / no sensor model
Speeds are drawn independently of roughness (base 20-110 km/h); sensors are a 50/50 mixture of the
'autopi' and 'phone' configurations unless stated. Labels: canonical IRI (MRI) of the driven profile.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import vehsim, sensor, simpipe, lira, features as F  # noqa: E402
from common.paths import PROCESSED, LIRA_ROUTES, LIRA_DIRS, RESULTS  # noqa: E402

OUT = os.path.join(PROCESSED, "sim"); os.makedirs(OUT, exist_ok=True)
R = vehsim.RANGES
SPEEDS = [20, 40, 60, 80, 100, 110]


def save(name, rows, feats, seqs):
    pd.DataFrame(rows).to_csv(os.path.join(OUT, f"{name}_meta.csv"), index=False)
    np.savez_compressed(os.path.join(OUT, f"{name}_arrays.npz"), feat=np.array(feats, dtype=np.float32),
                        X_zv=np.array(seqs, dtype=np.float32), feature_names=np.array(F.FEATURE_NAMES))
    print(f"saved {name}: {len(rows)} units", flush=True)


def p79_profiles():
    seg = pd.read_csv(os.path.join(PROCESSED, "lira", "p79_segments_100m.csv"))
    out = []
    for route in LIRA_ROUTES:
        for d in LIRA_DIRS:
            zp = lira.load_zp(route, d)
            ref = seg[(seg.route == route) & (seg.direction == d) & seg.mri_profile.notna()]
            for s, e in lira.zp_runs(zp):
                run = zp.iloc[s:e]
                grid = np.arange(run.dist.iloc[0], run.dist.iloc[-1], 0.1)
                z = 0.5 * (np.interp(grid, run.dist, run.z_left.interpolate().bfill().ffill()) +
                           np.interp(grid, run.dist, run.z_right.interpolate().bfill().ffill()))
                r = ref[(ref.start_m >= grid[0]) & (ref.start_m + 100 <= grid[-1])]
                if len(r) == 0:
                    continue
                out.append(dict(route=route, direction=d, z=z, s0=float(grid[0]), dx=0.1,
                                starts=r.start_m.to_numpy(), labels=r.mri_profile.to_numpy()))
    return out


def iso_routes(rng, n, length=4000.0, dx=0.05, tag="iso"):
    out = []
    for i in range(n):
        z = vehsim.synthetic_route(rng, length, dx)
        starts = np.arange(100.0, length - 200.0, 100.0)
        out.append(dict(route=f"{tag}{i:03d}", direction="-", z=z, s0=0.0, dx=dx, starts=starts,
                        labels=simpipe.synthetic_labels(z, dx, 0.0, starts)))
    return out


def sensor_for(rng, kind):
    if kind == "mix":
        kind = "autopi" if rng.random() < 0.5 else "phone"
    return kind, sensor.sample_sensor(rng, R[f"sensor_{kind}"])


def factorial_sensor_sampler(family: str, holder: bool):
    """Revision v2, class-E diagnostic (PROTOCOL_V2.md, Section 3): one cell of the 2 x 2 factorial sensor family
    (telematics-like 'autopi' / phone-like 'phone') x holder resonance (on / off). The holder-resonance ranges are the
    phone-like ones from config/sim_ranges.json; everything else is the family's own configuration."""
    cfg = dict(R[f"sensor_{family}"], mount_compliance=holder)
    if holder:
        cfg.update(mount_f_hz=R["sensor_phone"]["mount_f_hz"], mount_zeta=R["sensor_phone"]["mount_zeta"])
    label = f"{family}_{'holder' if holder else 'rigid'}"

    def f(rng, kind=None):
        return label, sensor.sample_sensor(rng, cfg)
    return f


def measured_sensor_sampler(mix=False):
    """POST-HOC SENSITIVITY ONLY (added 2026-10-02 after the zero-shot results): telematics sensor matched to the
    unlabelled LiRA-CD sensor statistics (results/lira_sensor_stats.json): nominal rate 52.6 Hz or 333 Hz in the
    measured proportion, 0.01 g or the finer quantisation in the measured proportion, tilt of the measured size.
    No LiRA-CD label is used. The primary simulator configuration is unchanged."""
    Q = json.load(open(os.path.join(RESULTS, "lira_sensor_stats.json")))
    base = R["sensor_autopi"]

    def f(rng, kind=None):
        if mix and rng.random() < 0.5:          # keep the primary smartphone-like half of the mixture unchanged
            return sensor_for(rng, "phone")
        rate = Q["nominal_hz_low_cluster"] if rng.random() < Q["share_passes_low_cluster"] else Q["nominal_hz_high_cluster"]
        lsb = 0.01 if rng.random() < Q["share_passes_lsb_0p01g"] else Q["lsb_g_min"]
        cfg = dict(base, rate_hz=[rate, rate], lsb_g=lsb, tilt_deg_sd=Q["tilt_deg_median"] / np.sqrt(2.0))
        return "autopi_measured", sensor.sample_sensor(rng, cfg)
    return f


def drive(rng, profiles, vehicles, name, passes_per=None, speeds=None, sensor_kind="mix", fixed_sensor=None, sensor_fn=None):
    rows, feats, seqs = [], [], []
    t0 = time.time()
    for pi, P in enumerate(profiles):
        vs = vehicles if passes_per is None else [vehicles[j] for j in rng.choice(len(vehicles), passes_per, replace=False)]
        for (vid, veh) in vs:
            sp_list = speeds if speeds is not None else [None]
            pick = sensor_fn or sensor_for
            sk, sens = fixed_sensor[vid] if fixed_sensor is not None else pick(rng, sensor_kind)
            for sp in sp_list:
                if fixed_sensor is None and speeds is None:
                    sk, sens = pick(rng, sensor_kind)
                units, ft, sq = simpipe.run_pass(rng, P["z"], P["dx"], P["s0"], P["starts"], veh, sens,
                                                 v0_kmh=sp, constant_speed=sp is not None)
                lab = dict(zip(P["starts"], P["labels"]))
                for u, f_, s_ in zip(units, ft, sq):
                    y = lab.get(u["start_m"], np.nan)
                    if not np.isfinite(y):
                        continue
                    rows.append(dict(route=P["route"], direction=P["direction"], vehicle=vid, sensor=sk,
                                     speed_set=sp if sp is not None else -1, segment=f"{P['route']}_{P['direction']}_{int(u['start_m'])}",
                                     mri=y, f_s=veh["f_s"], zeta=veh["zeta"], m_s=veh["m_s"], **u))
                    feats.append(f_); seqs.append(s_)
        if pi % 10 == 0:
            print(f"  {name}: profile {pi+1}/{len(profiles)} units {len(rows)} ({time.time()-t0:.0f}s)", flush=True)
    save(name, rows, feats, seqs)


def main():
    rng = np.random.default_rng(20261002)
    V_train = [(f"tr{i:02d}", vehsim.sample_vehicle(rng)) for i in range(30)]
    V_test = [(f"te{i:02d}", vehsim.sample_vehicle(rng)) for i in range(15)]
    V_low = [(f"lo{i:02d}", vehsim.sample_vehicle(rng, region="low_fs")) for i in range(10)]
    V_high = [(f"hi{i:02d}", vehsim.sample_vehicle(rng, region="high_fs")) for i in range(4)]
    json.dump(dict(train=dict(V_train), test=dict(V_test), low=dict(V_low), high=dict(V_high)),
              open(os.path.join(OUT, "vehicles.json"), "w"), indent=1)
    which = sys.argv[1:] or ["p79", "iso", "sweep", "region", "seenveh"]
    if "p79" in which:
        P79 = p79_profiles()
        drive(rng, P79, V_train, "p79_train")
        drive(rng, P79, V_test, "p79_test")
    iso_tr = iso_routes(np.random.default_rng(1), 40, tag="isotr")
    iso_te = iso_routes(np.random.default_rng(2), 15, tag="isote")
    if "iso" in which:
        drive(rng, iso_tr, V_train, "iso_train", passes_per=6)
        drive(rng, iso_te, V_test, "iso_test", passes_per=6)
    if "sweep" in which:
        fixed = {vid: ("autopi", sensor.sample_sensor(rng, R["sensor_autopi"])) for vid, _ in V_test}
        drive(rng, iso_te[:10], V_test[:6], "sweep_iso", speeds=SPEEDS, fixed_sensor=fixed)
        drive(rng, p79_profiles(), V_test[:2], "sweep_p79", speeds=SPEEDS, fixed_sensor=fixed)
    if "seenveh" in which:   # held-out routes driven by TRAIN vehicles (seen-vehicle reference for the unseen-vehicle test)
        drive(np.random.default_rng(77), iso_te, V_train, "iso_test_seenveh", passes_per=6)
    if "ablation" in which:   # one-at-a-time ablations of the simulator for sim->real transfer
        P79 = p79_profiles()
        rngA = np.random.default_rng(99)
        mid = {k: float(np.mean(v["range"])) for k, v in R["vehicle"].items()}
        fixed_veh = dict(m_s=mid["m_s"], r_y=mid["r_y"], L=mid["L"], a_frac=mid["a_frac"], f_s=mid["f_s"],
                         rear_freq_ratio=mid["rear_freq_ratio"], zeta=mid["zeta"], m_u=mid["m_u_per_wheel"],
                         k_t=mid["k_t_per_tire"], x_s=mid["x_s"])
        drive(rngA, P79, [(f"fx{i:02d}", fixed_veh) for i in range(30)], "p79_train_fixedvehicle")
        ideal = dict(rate_hz=100.0, jitter=0.0, lsb_g=0.0, noise_ug=0.0, bias=np.zeros(3), scale=np.zeros(3),
                     tilt=np.zeros(3), mount=False, missing=0.0)
        drive(rngA, P79, V_train, "p79_train_idealsensor", fixed_sensor={vid: ("ideal", ideal) for vid, _ in V_train})
    if "region" in which:
        drive(rng, iso_tr, V_low[:6], "region_train")
        drive(rng, iso_te, V_high + V_low[6:10], "region_test")
    if "measuredsensor" in which:   # POST-HOC sensitivity analysis (see measured_sensor_sampler); own RNG, primary data untouched
        drive(np.random.default_rng(31337), p79_profiles(), V_train, "p79_train_measuredsensor", sensor_fn=measured_sensor_sampler())
    if "measuredmix" in which:      # POST-HOC: matched telematics half + the primary smartphone-like half (separates the two changes)
        drive(np.random.default_rng(31338), p79_profiles(), V_train, "p79_train_measuredmix", sensor_fn=measured_sensor_sampler(mix=True))
    # revision v2 (PROTOCOL_V2.md, Section 3): the two missing cells of the sensor-family x holder-resonance factorial
    if "telecompliant" in which:    # V7: telematics-like sensor WITH the phone-like holder resonance
        drive(np.random.default_rng(41001), p79_profiles(), V_train, "p79_train_telecompliant",
              sensor_fn=factorial_sensor_sampler("autopi", True))
    if "phonerigid" in which:       # V8: phone-like sensor WITHOUT holder resonance
        drive(np.random.default_rng(41002), p79_profiles(), V_train, "p79_train_phonerigid",
              sensor_fn=factorial_sensor_sampler("phone", False))


if __name__ == "__main__":
    main()
