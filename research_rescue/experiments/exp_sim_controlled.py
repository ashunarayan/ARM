"""Controlled experiments in the parametric simulator (protocol section 3). Parts (argv):

  general    train on iso_train (train vehicles) -> held-out routes: unseen vehicles (iso_test) vs seen vehicles
             (iso_test_seenveh); same models as the real-data ladder
  region     extrapolation in vehicle space: train on LOW body-frequency vehicles (region_train), test on held-out
             routes driven by HIGH-f_s vs new LOW-f_s vehicles (region_test)
  speed      constant-speed sweeps (20-110 km/h) on held-out synthetic routes and on real P79 profiles;
             invariance criterion fixed in advance: mean relative change 40 -> 100 km/h within +-10 % (95 % CI inside)
  robust     sensor perturbations applied at test time only (models trained on iso_train)
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import models as M, report, vehsim, sensor, simpipe  # noqa: E402
from common.paths import PROCESSED, RESULTS  # noqa: E402
from common.stats import metrics  # noqa: E402

OUT = os.path.join(RESULTS, "sim"); os.makedirs(OUT, exist_ok=True)
R = vehsim.RANGES


def load_sim(name):
    m = pd.read_csv(os.path.join(PROCESSED, "sim", f"{name}_meta.csv"))
    A = np.load(os.path.join(PROCESSED, "sim", f"{name}_arrays.npz"))
    return m, dict(feat=A["feat"], seq=A["X_zv"][:, :, :1], y=m.mri.to_numpy(), group=m.segment.to_numpy())


def models_for_controlled():
    return [M.PhysicsIndex(0.0, label="M2a RMS only (alpha=0)"), M.PhysicsIndex(0.5, label="M2b RMS/v^0.5"),
            M.PhysicsIndex(None, label="M2c RMS/v^alpha (alpha fitted)"), M.PhysicsIndex(2.0, label="M2d legacy exponent 2"),
            M.GBM(label="M3 LightGBM"), M.GBM(features=[f for f in M.FEATURE_NAMES if f not in M.SPEED_FEATS], label="M3 LightGBM (no speed)"),
            M.TorchModel("cnn", label="M5 1D-CNN"), M.TorchModel("cnn", use_speed=False, label="M5 1D-CNN (no speed)")]


_CACHE = {}


def fit_all(Dtr, key=None):
    """Fit the controlled-experiment model set once per training set (cached within the process)."""
    if key is not None and key in _CACHE:
        return _CACHE[key]
    ms = models_for_controlled()
    for m in ms:
        m.fit(Dtr)
    if key is not None:
        _CACHE[key] = ms
    return ms


def predict(m, D):
    return m.predict_seeds(D) if isinstance(m, M.TorchModel) else m.predict(D)


def part_general():
    mtr, Dtr = load_sim("iso_train")
    ms = fit_all(Dtr, "iso_train")
    rows = []
    for name in ["iso_test", "iso_test_seenveh"]:
        mte, Dte = load_sim(name)
        P = {m.name: predict(m, Dte) for m in ms}
        df = report.evaluate(Dte["y"], P, mte.segment.to_numpy(), label=f"general_{name}", B=1000)
        df["test_set"] = name
        rows.append(df)
    out = pd.concat(rows)
    out.to_csv(os.path.join(OUT, "general_seen_vs_unseen_vehicles.csv"), index=False)
    # paired seen-vs-unseen difference per model on the SAME segments (segment-mean MAE)
    pair = []
    mU, DU = load_sim("iso_test"); mS, DS = load_sim("iso_test_seenveh")
    for m in ms:
        eU = pd.Series(np.abs(np.atleast_2d(predict(m, DU)).mean(0) - DU["y"])).groupby(mU.segment.to_numpy()).mean()
        eS = pd.Series(np.abs(np.atleast_2d(predict(m, DS)).mean(0) - DS["y"])).groupby(mS.segment.to_numpy()).mean()
        j = pd.concat([eU.rename("u"), eS.rename("s")], axis=1).dropna()
        rng = np.random.default_rng(0); d = (j.u - j.s).to_numpy(); base = j.s.mean()
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        pair.append(dict(model=m.name, mae_seen=float(j.s.mean()), mae_unseen=float(j.u.mean()), diff=float(d.mean()),
                         lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), rel_diff=float(d.mean() / base),
                         rel_hi=float(np.percentile(bs, 97.5) / base),
                         generalises=bool(np.percentile(bs, 97.5) / base <= 0.10), n_segments=len(j)))
    pd.DataFrame(pair).to_csv(os.path.join(OUT, "unseen_vehicle_paired.csv"), index=False)
    print(pd.DataFrame(pair).round(3).to_string(index=False))


def part_region():
    mtr, Dtr = load_sim("region_train")
    ms = fit_all(Dtr, "region_train")
    mte, Dte = load_sim("region_test")
    hi = mte.vehicle.str.startswith("hi").to_numpy()
    rows = []
    for m in ms:
        p = np.atleast_2d(predict(m, Dte)).mean(0)
        e = pd.DataFrame(dict(seg=mte.segment, hi=hi, ae=np.abs(p - Dte["y"]), err=p - Dte["y"]))
        g = e.groupby(["seg", "hi"]).ae.mean().unstack().dropna()
        d = (g[True] - g[False]).to_numpy(); rng = np.random.default_rng(0)
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
        rows.append(dict(model=m.name, mae_low_fs_unseen=float(g[False].mean()), mae_high_fs_unseen=float(g[True].mean()),
                         diff=float(d.mean()), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                         bias_high_fs=float(e[e.hi].err.mean()), bias_low_fs=float(e[~e.hi].err.mean()), n_segments=len(g)))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "vehicle_region_extrapolation.csv"), index=False)
    print(pd.DataFrame(rows).round(3).to_string(index=False))


def part_speed():
    mtr, Dtr = load_sim("iso_train")
    ms = fit_all(Dtr, "iso_train")
    res, curves = [], []
    for name in ["sweep_iso", "sweep_p79"]:
        mte, Dte = load_sim(name)
        P = {m.name: np.atleast_2d(predict(m, Dte)).mean(0) for m in ms}
        # raw measurement (no model): RMS of dynamic vertical acceleration
        P["raw RMS of a_z (no model, not an IRI)"] = np.exp(Dte["feat"][:, M.FI["log_rms"]])
        for k, p in P.items():
            df = pd.DataFrame(dict(seg=mte.segment, veh=mte.vehicle, sp=mte.speed_set, p=p, y=mte.mri))
            pv = df.pivot_table(index=["seg", "veh"], columns="sp", values="p").dropna()
            rel = (pv[100] / pv[40] - 1.0).to_numpy()
            segs = pv.index.get_level_values(0).to_numpy()
            # bootstrap over profiles (route) clusters
            route = np.array([s.rsplit("_", 2)[0] for s in segs])
            ur = np.unique(route); mem = [np.where(route == r)[0] for r in ur]
            rng = np.random.default_rng(0)
            bs = [np.mean(rel[np.concatenate([mem[i] for i in rng.integers(0, len(ur), len(ur))])]) for _ in range(2000)]
            lsp = np.log(np.array(pv.columns, float))
            slopes = np.array([np.polyfit(lsp, np.log(np.maximum(r, 1e-6)), 1)[0] for r in pv.to_numpy()])
            cv = (pv.std(axis=1) / pv.mean(axis=1)).to_numpy()
            mae_by_speed = {int(s): float(np.mean(np.abs(df[df.sp == s].p - df[df.sp == s].y))) for s in sorted(df.sp.unique())}
            lo, hi_ = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
            ratio = pv.div(pv[60], axis=0)
            for spd in pv.columns:
                rr = ratio[spd].to_numpy()
                bsr = [np.mean(rr[np.concatenate([mem[i] for i in rng.integers(0, len(ur), len(ur))])]) for _ in range(1000)]
                curves.append(dict(sweep=name, model=k, speed_kmh=int(spd), mean_ratio_to_60=float(rr.mean()),
                                   lo=float(np.percentile(bsr, 2.5)), hi=float(np.percentile(bsr, 97.5)),
                                   mae=float(np.mean(np.abs(df[df.sp == spd].p - df[df.sp == spd].y)))))
            res.append(dict(sweep=name, model=k, n_seg_veh=len(pv), rel_change_40_100=float(rel.mean()), ci_lo=lo, ci_hi=hi_,
                            invariant_40_100=bool(-0.10 <= lo and hi_ <= 0.10), slope_dlogpred_dlogv=float(slopes.mean()),
                            cv_across_speeds=float(cv.mean()), **{f"mae_{s}kmh": v for s, v in mae_by_speed.items()}))
    out = pd.DataFrame(res)
    out.to_csv(os.path.join(OUT, "speed_invariance.csv"), index=False)
    pd.DataFrame(curves).to_csv(os.path.join(OUT, "speed_invariance_curves.csv"), index=False)
    print(out[["sweep", "model", "rel_change_40_100", "ci_lo", "ci_hi", "invariant_40_100", "slope_dlogpred_dlogv", "cv_across_speeds"]].round(3).to_string(index=False))


def part_speed_p79():
    """Secondary (added after the ISO-trained sweep result; reported regardless of outcome): train on simulated drives
    over the measured P79 profiles of three LiRA routes and test the constant-speed sweep on the held-out route's
    profiles (leave-one-route-out). Same criterion (fixed in advance) as part_speed."""
    mtr, Dtr = load_sim("p79_train")
    mte, Dte = load_sim("sweep_p79")
    route_tr = mtr.route.to_numpy(); route_te = mte.route.to_numpy()
    preds = {}
    for R_ in np.unique(route_te):
        tr = np.where(route_tr != R_)[0]; te = np.where(route_te == R_)[0]
        Dt = {k: v[tr] for k, v in Dtr.items()}; De = {k: v[te] for k, v in Dte.items()}
        for m in [M.PhysicsIndex(None, label="M2c RMS/v^alpha (alpha fitted)"), M.GBM(label="M3 LightGBM"),
                  M.GBM(features=[f for f in M.FEATURE_NAMES if f not in M.SPEED_FEATS], label="M3 LightGBM (no speed)")]:
            m.fit(Dt)
            preds.setdefault(m.name, np.full(len(mte), np.nan))[te] = m.predict(De)
    res, curves = [], []
    for k, p in preds.items():
        df = pd.DataFrame(dict(seg=mte.segment, veh=mte.vehicle, sp=mte.speed_set, p=p, y=mte.mri))
        pv = df.pivot_table(index=["seg", "veh"], columns="sp", values="p").dropna()
        rel = (pv[100] / pv[40] - 1.0).to_numpy()
        route = np.array([s_.rsplit("_", 2)[0] for s_ in pv.index.get_level_values(0)])
        ur = np.unique(route); mem = [np.where(route == r)[0] for r in ur]
        rng = np.random.default_rng(0)
        bs = [np.mean(rel[np.concatenate([mem[i] for i in rng.integers(0, len(ur), len(ur))])]) for _ in range(2000)]
        lo, hi_ = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
        ratio = pv.div(pv[60], axis=0)
        for spd in pv.columns:
            rr = ratio[spd].to_numpy()
            bsr = [np.mean(rr[np.concatenate([mem[i] for i in rng.integers(0, len(ur), len(ur))])]) for _ in range(1000)]
            curves.append(dict(sweep="sweep_p79_trained_on_p79", model=k, speed_kmh=int(spd), mean_ratio_to_60=float(rr.mean()),
                               lo=float(np.percentile(bsr, 2.5)), hi=float(np.percentile(bsr, 97.5)),
                               mae=float(np.mean(np.abs(df[df.sp == spd].p - df[df.sp == spd].y)))))
        res.append(dict(sweep="sweep_p79_trained_on_p79 (LORO)", model=k, n_seg_veh=len(pv), rel_change_40_100=float(rel.mean()),
                        ci_lo=lo, ci_hi=hi_, invariant_40_100=bool(-0.10 <= lo and hi_ <= 0.10)))
    pd.DataFrame(res).to_csv(os.path.join(OUT, "speed_invariance_p79trained.csv"), index=False)
    pd.DataFrame(curves).to_csv(os.path.join(OUT, "speed_invariance_curves_p79trained.csv"), index=False)
    print(pd.DataFrame(res).round(3).to_string(index=False))


PERTURB = {
    "sampling_rate_hz": [("25 Hz", dict(rate=25)), ("50 Hz", dict(rate=50)), ("100 Hz", dict(rate=100)), ("200 Hz", dict(rate=200))],
    "noise_x": [(f"x{k}", dict(noise_mult=k)) for k in (0, 1, 2, 4, 8)],
    "quantisation_g": [(f"{q} g", dict(lsb=q)) for q in (0.0, 0.001, 0.01, 0.02, 0.05)],
    "tilt_sd_deg": [(f"{d} deg", dict(tilt=d)) for d in (0, 5, 10, 15, 20)],
    "speed_bias": [(f"{b:+d}%", dict(speed_bias=b / 100)) for b in (-20, -10, 0, 10, 20)] + [("GPS 1 Hz", dict(gps=True))],
    "missing_samples": [(f"{p}%", dict(missing=p / 100)) for p in (0, 5, 10, 20, 40)],
    "mount_resonance": [("rigid", dict()), ("40 Hz", dict(mount_f=40)), ("25 Hz", dict(mount_f=25)), ("15 Hz", dict(mount_f=15))],
}


def perturbed_units(routes, vehicles, spec, seed=12345):
    """Common random numbers: every perturbation level re-uses the same per-pass random streams (speed profile,
    sensor configuration, noise), so level-to-level differences reflect the perturbation, not resampling."""
    rows, feats, seqs = [], [], []
    k = 0
    for P in routes:
        for vid, veh in vehicles:
            k += 1
            rng_s = np.random.default_rng(seed + 7919 * k)          # sensor configuration stream
            rng = np.random.default_rng(seed + 104729 * k)          # driving + measurement stream
            sens = sensor.sample_sensor(rng_s, R["sensor_autopi"])
            sens["tilt"] = np.zeros(3)
            tilt_draw = rng_s.normal(0, 1, 3)                       # unit draws, scaled below
            if "rate" in spec: sens["rate_hz"] = float(spec["rate"])
            if "noise_mult" in spec: sens["noise_ug"] = 250.0 * spec["noise_mult"]
            if "lsb" in spec: sens["lsb_g"] = float(spec["lsb"])
            if "tilt" in spec: sens["tilt"] = np.deg2rad(spec["tilt"] * tilt_draw)
            if "missing" in spec: sens["missing"] = spec["missing"]
            if "mount_f" in spec: sens.update(mount=True, mount_f=float(spec["mount_f"]), mount_zeta=0.1)
            units, ft, sq = simpipe.run_pass(rng, P["z"], P["dx"], P["s0"], P["starts"], veh, sens,
                                             speed_mode="gps" if spec.get("gps") else "can", speed_rel_err=spec.get("speed_bias", 0.0))
            lab = dict(zip(P["starts"], P["labels"]))
            for u, f_, s_ in zip(units, ft, sq):
                rows.append(dict(segment=f"{P['route']}_{int(u['start_m'])}", mri=lab[u["start_m"]])); feats.append(f_); seqs.append(s_)
    m = pd.DataFrame(rows)
    return m, dict(feat=np.array(feats), seq=np.array(seqs)[:, :, :1], y=m.mri.to_numpy(), group=m.segment.to_numpy())


def part_robust():
    from experiments.sim_generate import iso_routes
    mtr, Dtr = load_sim("iso_train")
    ms = [m for m in fit_all(Dtr, "iso_train") if m.name in ("M2c RMS/v^alpha (alpha fitted)", "M3 LightGBM", "M5 1D-CNN", "M3 LightGBM (no speed)")]
    vehicles = json.load(open(os.path.join(PROCESSED, "sim", "vehicles.json")))["test"]
    vehicles = list(vehicles.items())[:6]
    routes = iso_routes(np.random.default_rng(2), 15, tag="isote")[:12]
    rows = []
    for fam, levels in PERTURB.items():
        for lname, spec in levels:
            t0 = time.time()
            mte, Dte = perturbed_units(routes, vehicles, spec)
            for m in ms:
                p = np.atleast_2d(predict(m, Dte)).mean(0)
                mm = metrics(Dte["y"], p)
                rows.append(dict(family=fam, level=lname, model=m.name, n=len(p), mae=mm["mae"], bias=mm["bias"], spearman=mm["spearman"]))
            print(f"  [robust] {fam}={lname}: " + " ".join(f"{r['model'][:14]}={r['mae']:.3f}" for r in rows[-len(ms):]) + f" ({time.time()-t0:.0f}s)", flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "robustness.csv"), index=False)


def main():
    parts = sys.argv[1:] or ["general", "region", "speed", "robust"]
    for p in parts:
        print(f"=== {p}", flush=True)
        {"general": part_general, "region": part_region, "speed": part_speed, "robust": part_robust,
         "speed_p79": part_speed_p79}[p]()


if __name__ == "__main__":
    main()
