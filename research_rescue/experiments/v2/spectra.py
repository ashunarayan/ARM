"""Revision v2, E3/E4 (class E, exploratory): spectral diagnosis of the simulation-to-real gap.

Part 1 (real): replay the v1 LiRA builder (same pass order, same chainage runs, same unit cuts) and compute per unit
  * psd50: Welch PSD of the dynamic vertical acceleration after the SHARED preprocessing (50 Hz, 2.56 s Hann windows)
  * psd200: Welch PSD of the 200 Hz-interpolated vertical acceleration WITHOUT the 20 Hz low-pass (0-100 Hz), to see
    content above the analysis band (meaningful only for passes logged at 333 Hz)
  Alignment with data/processed/lira/units.csv is checked unit by unit.
Part 2 (sim): re-simulate passes of the 10 first v1 training vehicles over all P79 profiles for the sensor variants
  V1 (telematics-like, rigid), V2 (phone-like, holder), V7 (telematics-like, holder), V8 (phone-like, rigid),
  V3 (ideal), V5 (telematics matched to LiRA-CD statistics); psd50 per unit through the same preprocessing.
Part 3 (comparisons): mean log10-PSD difference real - sim per frequency on cells (segment x 10 km/h speed band)
  present in both domains, 1 km-block bootstrap CI; aliasing check within TMU#10 (52.6 Hz vs 333 Hz logging);
  share of 0.3-100 Hz variance above 20 Hz and above 26 Hz in 333 Hz passes.

Outputs: data/processed/v2/spectra_real.npz, spectra_sim_<variant>.npz; results/v2/spectra_*.csv
"""
from __future__ import annotations

import json
import os
import sys
import time

import h5py
import numpy as np
import pandas as pd
from scipy.signal import welch, butter, sosfiltfilt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, RESCUE, LIRA_ROUTES, load_lira  # noqa: E402
sys.path.insert(0, os.path.join(RESCUE, "experiments"))
from common import lira, geo, preprocess as PP, vehsim, sensor, features as Fe  # noqa: E402
from common.paths import PROCESSED, LIRA_CAR, LIRA_DIRS  # noqa: E402
from lira_build_dataset import chainage_from_gps  # noqa: E402
from sim_generate import p79_profiles, factorial_sensor_sampler, measured_sensor_sampler, sensor_for  # noqa: E402

PROC = os.path.join(PROCESSED, "v2"); os.makedirs(PROC, exist_ok=True)
NPER50, NPER200 = 128, 512
F50 = np.fft.rfftfreq(NPER50, 1 / 50.0)
F200 = np.fft.rfftfreq(NPER200, 1 / 200.0)


def psd(a, fs, nper):
    if len(a) < nper:
        return np.full(nper // 2 + 1, np.nan)
    return welch(a, fs=fs, nperseg=nper, noverlap=nper // 2, window="hann", detrend="constant")[1]


def unit_windows(a_dyn, v50, c50, seg_starts, min_cov=0.9, min_speed=2.0):
    """Mirror of preprocess.extract_units: returns [(start_m, idx)] for valid units, in the same order."""
    out = []
    for st in seg_starts:
        sel = (c50 >= st) & (c50 < st + PP.SEG)
        if sel.sum() < 20:
            continue
        idx = np.where(sel)[0]
        if idx[-1] - idx[0] + 1 != len(idx):
            continue
        if c50[idx[-1]] - c50[idx[0]] < min_cov * PP.SEG or v50[idx].mean() < min_speed:
            continue
        out.append((float(st), idx))
    return out


def raw200(t, xyz):
    """200 Hz interpolated vertical acceleration without the 20 Hz low-pass (m/s^2, gravity-aligned, 0.3 Hz HP)."""
    o = np.argsort(t); t = np.asarray(t)[o]; xyz = np.asarray(xyz)[o]
    keep = np.concatenate([[True], np.diff(t) > 0]); t = t[keep]; xyz = xyz[keep]
    g200 = np.arange(t[0], t[-1], 1 / 200.0)
    m = np.column_stack([np.interp(g200, t, xyz[:, i]) for i in range(3)])
    ghat = m.mean(0); ghat /= np.linalg.norm(ghat)
    a = (m @ ghat) * PP.G0
    return g200, sosfiltfilt(butter(2, 0.3, btype="highpass", fs=200.0, output="sos"), a)


def real_part(U):
    seg_all = pd.read_csv(os.path.join(PROCESSED, "lira", "p79_segments_100m.csv"))
    P50, P200, meta = [], [], []
    for route in LIRA_ROUTES:
        for direction in LIRA_DIRS:
            zp = lira.load_zp(route, direction).dropna(subset=["lat", "lon"])
            lat0, lon0 = zp.lat.median(), zp.lon.median()
            poly = geo.Polyline(geo.to_local_xy(zp.lat.to_numpy(), zp.lon.to_numpy(), lat0, lon0), zp.dist.to_numpy(), step=1.0)
            seg_ref = seg_all[(seg_all.route == route) & (seg_all.direction == direction) & seg_all.mri_profile.notna()]
            with h5py.File(os.path.join(LIRA_CAR, f"{route}_{direction}.hdf5"), "r") as f:
                for task in f["GM"].keys():
                    for p in f["GM"][task].keys():
                        g = f["GM"][task][p]
                        if not all(k in g for k in ("acc.xyz", "obd.spd_veh", "gps")):
                            continue
                        if g["acc.xyz"].shape[0] < 500 or g["obd.spd_veh"].shape[0] < 10 or g["gps"].shape[0] < 10:
                            continue
                        acc = g["acc.xyz"][:]
                        t50, a_dyn = PP.vertical_dynamic(acc[:, 0], acc[:, 1:4])
                        spd = g["obd.spd_veh"][:]
                        v50 = np.interp(t50, spd[:, 0], spd[:, 1] / 3.6)
                        t200, a200 = raw200(acc[:, 0], acc[:, 1:4])
                        dt = np.diff(acc[:, 0]); nominal = float(1.0 / np.median(dt[dt > 0]))
                        for k, (c50, _) in enumerate(chainage_from_gps(g["gps"][:], poly, lat0, lon0, t50)):
                            for st, idx in unit_windows(a_dyn, v50, c50, seg_ref.start_m.to_numpy()):
                                P50.append(psd(a_dyn[idx], 50.0, NPER50))
                                w = (t200 >= t50[idx[0]]) & (t200 <= t50[idx[-1]])
                                P200.append(psd(a200[w], 200.0, NPER200))
                                meta.append(dict(route=route, direction=direction, task=str(task), pass_id=p, start_m=st,
                                                 v_mean=float(v50[idx].mean()), rms=float(np.sqrt(np.mean(a_dyn[idx] ** 2))),
                                                 nominal_hz=nominal))
            print(f"real {route} {direction}: {len(meta)} units", flush=True)
    M = pd.DataFrame(meta)
    assert len(M) == len(U), (len(M), len(U))
    for c in ("route", "direction", "task", "pass_id"):
        assert (M[c].astype(str).to_numpy() == U[c].astype(str).to_numpy()).all(), c
    assert np.allclose(M.start_m, U.start_m) and np.allclose(M.v_mean, U.v_mean, rtol=1e-6) and np.allclose(M.rms, U.a_rms, rtol=1e-5)
    np.savez_compressed(os.path.join(PROC, "spectra_real.npz"), psd50=np.array(P50, np.float32), psd200=np.array(P200, np.float32),
                        nominal_hz=M.nominal_hz.to_numpy())
    return np.array(P50), np.array(P200), M.nominal_hz.to_numpy()


SIM_VARIANTS = {"V1": lambda: (lambda rng, k=None: sensor_for(rng, "autopi")),
                "V2": lambda: (lambda rng, k=None: sensor_for(rng, "phone")),
                "V7": lambda: factorial_sensor_sampler("autopi", True),
                "V8": lambda: factorial_sensor_sampler("phone", False),
                "V5": lambda: measured_sensor_sampler(),
                "V3": None}


def sim_part(vid, vehicles, profiles, seed):
    from common import simpipe
    rng = np.random.default_rng(seed)
    ideal = dict(rate_hz=100.0, jitter=0.0, lsb_g=0.0, noise_ug=0.0, bias=np.zeros(3), scale=np.zeros(3),
                 tilt=np.zeros(3), mount=False, missing=0.0)
    sampler = SIM_VARIANTS[vid]() if SIM_VARIANTS[vid] is not None else None
    R = vehsim.RANGES
    P50, meta = [], []
    for P in profiles:
        for vname, veh in vehicles:
            sens = ideal if sampler is None else sampler(rng)[1]
            length = len(P["z"]) * P["dx"]
            v0 = rng.uniform(*R["speed"]["base_kmh"]) / 3.6
            dur = (length - veh["L"]) / max(v0 * 0.6, 1.0) + 30.0
            v_t = vehsim.speed_profile(rng, dur, simpipe.FS_SIM, v0, ranges=R)
            sim = vehsim.simulate_pass(P["z"], P["dx"], P["s0"], v_t, simpipe.FS_SIM, veh)
            td, fd = sensor.measure(rng, sim["t"], sim["a_s"], sim["a_long"], simpipe.FS_SIM, sens)
            t50, a_dyn = PP.vertical_dynamic(td, fd)
            v_meas = sensor.measure_speed(rng, sim["t"], sim["v"], cfg=R["speed_sensor"])
            v50 = np.interp(t50, sim["t"], v_meas)
            c50 = np.interp(t50, sim["t"], sim["s_front"]) + simpipe.ou(rng, len(t50), PP.FS, 3.0, 30.0)
            lab = dict(zip(P["starts"], P["labels"]))
            for st, idx in unit_windows(a_dyn, v50, c50, P["starts"]):
                P50.append(psd(a_dyn[idx], 50.0, NPER50))
                meta.append(dict(route=P["route"], direction=P["direction"], start_m=st, v_mean=float(v50[idx].mean()),
                                 mri=lab[st], vehicle=vname))
    M = pd.DataFrame(meta)
    np.savez_compressed(os.path.join(PROC, f"spectra_sim_{vid}.npz"), psd50=np.array(P50, np.float32))
    M.to_csv(os.path.join(PROC, f"spectra_sim_{vid}_meta.csv"), index=False)
    return np.array(P50), M


def cell_diff(Lr, mr, Ls, ms, B=1000, seed=0):
    """Mean over common (segment, speed band) cells of [mean log10 PSD real - mean log10 PSD sim]; block bootstrap."""
    def cells(L, m):
        ok = np.isfinite(L).all(1)                          # units shorter than one Welch window have no PSD
        L, m = L[ok], m[ok]
        key = m.segment + "|" + (m.v_mean * 3.6 // 10).astype(int).astype(str)
        df = pd.DataFrame(L); df["key"] = key.to_numpy()
        return df.groupby("key").mean(), m.assign(key=key).groupby("key").block.first()
    cr, br = cells(Lr, mr); cs, _ = cells(Ls, ms)
    common = cr.index.intersection(cs.index)
    D = cr.loc[common].to_numpy() - cs.loc[common].to_numpy()
    blk = pd.factorize(br.loc[common])[0]
    C = blk.max() + 1
    sums = np.stack([np.bincount(blk, weights=D[:, j], minlength=C) for j in range(D.shape[1])], 1)
    cnt = np.bincount(blk, minlength=C)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(B):
        w = np.bincount(rng.integers(0, C, C), minlength=C)
        bs.append((w @ sums) / (w @ cnt))
    bs = np.array(bs)
    return D.mean(0), np.percentile(bs, 2.5, 0), np.percentile(bs, 97.5, 0), len(common)


def main():
    t0 = time.time()
    U, _ = load_lira()
    rp = os.path.join(PROC, "spectra_real.npz")
    if os.path.exists(rp):
        Z = np.load(rp); P50, P200, nominal = Z["psd50"], Z["psd200"], Z["nominal_hz"]
    else:
        P50, P200, nominal = real_part(U)
    print(f"real spectra: {P50.shape} ({time.time() - t0:.0f}s)", flush=True)
    U = U.assign(nominal_hz=nominal)
    veh = json.load(open(os.path.join(PROCESSED, "sim", "vehicles.json")))["train"]
    vehicles = list(veh.items())[:10]
    profiles = p79_profiles()
    band = (F50 >= 0.5) & (F50 <= 20.0)
    Lr = np.log10(P50[:, band] + 1e-12)
    rows = []
    for j, vid in enumerate(["V1", "V2", "V7", "V8", "V3", "V5"]):
        sp = os.path.join(PROC, f"spectra_sim_{vid}.npz")
        if os.path.exists(sp):
            S50 = np.load(sp)["psd50"]; ms = pd.read_csv(os.path.join(PROC, f"spectra_sim_{vid}_meta.csv"))
        else:
            S50, ms = sim_part(vid, vehicles, profiles, seed=52000 + j)
        ms["segment"] = ms.route + "_" + ms.direction + "_" + ms.start_m.astype(int).astype(str)
        ms["block"] = ms.route + "_" + ms.direction + "_" + (ms.start_m // 1000).astype(int).astype(str)
        Ls = np.log10(S50[:, band] + 1e-12)
        mu, lo, hi, n = cell_diff(Lr, U, Ls, ms)
        for f, a, b, c in zip(F50[band], mu, lo, hi):
            rows.append(dict(comparison=f"real-{vid}", freq_hz=f, log10_diff=a, lo=b, hi=c, n_cells=n))
        print(f"{vid}: {len(ms)} sim units, {n} common cells ({time.time() - t0:.0f}s)", flush=True)
    # aliasing check (52.6 Hz vs 333 Hz logging on common cells). DEVIATION (CHANGELOG 2026-10-03): the pre-specified
    # within-TMU#10 design is infeasible - TMU#10 logged 52.6 Hz only on M13 and 333 Hz only on CPH1/M3 (no common
    # segment). Replaced by (a) TMU#12 on M3, the only unit with both rates on common segments, and (b) all units on
    # common cells (confounded with device/mounting differences).
    slow, fast = (U.nominal_hz < 100).to_numpy(), (U.nominal_hz >= 100).to_numpy()
    t12 = (U.unit == "TMU#12").to_numpy() & (U.route == "M3").to_numpy()
    for comp, a_, b_ in (("TMU12 on M3: 52.6Hz-333Hz", t12 & slow, t12 & fast), ("all units: 52.6Hz-333Hz", slow, fast)):
        try:
            mu, lo, hi, n = cell_diff(Lr[a_], U[a_], Lr[b_], U[b_])
        except ValueError:
            print(comp, "no common cells"); continue
        for f, a, b, c in zip(F50[band], mu, lo, hi):
            rows.append(dict(comparison=comp, freq_hz=f, log10_diff=a, lo=b, hi=c, n_cells=n))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "spectra_log10_diff.csv"), index=False)
    # high-frequency content of the 333 Hz passes (raw 200 Hz signal, no 20 Hz low-pass)
    h = (U.nominal_hz >= 100).to_numpy()
    Q = P200[h]; ok = np.isfinite(Q).all(1)
    Q = Q[ok]
    df_ = F200[1] - F200[0]
    tot = Q[:, (F200 >= 0.3)].sum(1) * df_
    hf = dict(n_units=int(ok.sum()), share_above_20hz=float(np.median(Q[:, F200 > 20].sum(1) * df_ / tot)),
              share_above_26hz=float(np.median(Q[:, F200 > 26.3].sum(1) * df_ / tot)),
              share_10_20hz=float(np.median(Q[:, (F200 >= 10) & (F200 <= 20)].sum(1) * df_ / tot)))
    json.dump(hf, open(os.path.join(OUT, "spectra_highfreq_333hz.json"), "w"), indent=1)
    mean_real = pd.DataFrame(dict(freq_hz=F200, mean_log10_psd=np.log10(Q.mean(0) + 1e-12)))
    mean_real.to_csv(os.path.join(OUT, "spectra_real_333hz_mean.csv"), index=False)
    print(json.dumps(hf, indent=1))
    R = pd.DataFrame(rows)
    for comp, g in R.groupby("comparison"):
        b = pd.cut(g.freq_hz, [0.4, 2, 5, 10, 15, 20.1])
        print(comp, g.groupby(b, observed=True).log10_diff.mean().round(2).to_dict())


if __name__ == "__main__":
    main()
