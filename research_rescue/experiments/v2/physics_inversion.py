"""Revision v2, R10: calibrated quarter-car spectral inversion baseline M7 (PROTOCOL_V2.md, Section 4).

In the spirit of response-type calibration and of Skar & Levenberg (2024), whose calibrated vehicle parameters are not
published (exact reproduction impossible):
 1. road input spectrum of every unit: spatial Welch PSD G(n) of the P79 profile (mean of both wheel paths, 0.1 m grid)
    of its 100 m segment, mapped to time with the unit's mean speed v: S_r(f) = G(f / v) / v
 2. empirical transmissibility of the real car + sensor on the TRAINING routes of a fold:
    T(f) = exp(median over training units of log(S_a(f) / S_r(f))), 0.5-20 Hz (S_a: unit acceleration PSD after the
    shared preprocessing, from experiments/v2/spectra.py)
 3. calibration: normalised quarter car (K1 = kt/ms, K2 = ks/ms, C = cs/ms, U = mu/ms) times a sensor gain g fitted to
    log T(f) by least squares
 4. inversion of a test unit: road spectrum S_r(f) = S_a(f) / |H(f)|^2 -> spatial G(n) = S_r(n v) v on the observable
    band n in [0.5/v, 20/v]; IRI from the Golden-Car relative-velocity response at 80 km/h with the 250 mm moving
    average, assuming a Gaussian response: IRI = 1000 sqrt(2/pi) sigma_rv / V80
 5. M7 = this IRI (uncalibrated); M7cal = exp(a + b log IRI_M7) with (a, b) fitted on training-route segments
The spectral IRI formula is first checked against the validated IRI on the true P79 profile spectra.
Outputs: results/v2/physics_inversion.csv (per fold), physics_inversion_check.json, physics_transmissibility.csv
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.signal import welch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_v2 import OUT, EPS, LIRA_ROUTES, load_lira, seg_table  # noqa: E402
from common import lira  # noqa: E402
from common.paths import PROCESSED, LIRA_DIRS  # noqa: E402

F50 = np.fft.rfftfreq(128, 1 / 50.0)
BAND = (F50 >= 0.5) & (F50 <= 20.0)
NPER = 512
NGRID = np.fft.rfftfreq(NPER, 0.1)                     # spatial frequencies (cycles/m)
V80 = 80 / 3.6
GC = dict(K1=653.0, K2=63.3, C=6.0, U=0.15)


def qc_tf(w, K1, K2, C, U):
    """Quarter car (per unit sprung mass): returns (sprung acceleration / road, relative velocity / road)."""
    s = 1j * w
    A = (C * s + K2) / (s ** 2 + C * s + K2)
    D = U * s ** 2 + C * s + K2 + K1 - (C * s + K2) * A
    Xu = K1 / D
    return s ** 2 * A * Xu, s * (A - 1) * Xu


def gc_weight(n):
    """|H_rv,GoldenCar(n)|^2 * |250 mm moving average|^2 for spatial frequency n (cycles/m) at 80 km/h."""
    _, hrv = qc_tf(2 * np.pi * n * V80, **GC)
    return np.abs(hrv) ** 2 * np.sinc(0.25 * n) ** 2


def iri_from_spectrum(n, G):
    """IRI (m/km) from a one-sided displacement PSD G(n) on increasing frequencies n (trapezoid)."""
    return 1000.0 * np.sqrt(2 / np.pi) * np.sqrt(np.trapezoid(gc_weight(n) * G, n)) / V80


def segment_spectra(starts):
    """Spatial PSD of the P79 profile of every 100 m segment of the real units.
    starts: (route, direction) -> segment start distances (m) of the real units. v3 fix (PROTOCOL_V3 V3-8): the v2 code
    used windows at multiples of 100 m, which missed every M13-VH segment (starts at ...60 m)."""
    out = {}
    for route in LIRA_ROUTES:
        for d in LIRA_DIRS:
            zp = lira.load_zp(route, d)
            st_rd = np.sort(np.asarray(starts.get((route, d), []), float))
            for s, e in lira.zp_runs(zp):
                run = zp.iloc[s:e]
                grid = np.arange(run.dist.iloc[0], run.dist.iloc[-1], 0.1)
                z = 0.5 * (np.interp(grid, run.dist, run.z_left.interpolate().bfill().ffill())
                           + np.interp(grid, run.dist, run.z_right.interpolate().bfill().ffill()))
                for st in st_rd[(st_rd >= grid[0]) & (st_rd <= grid[-1] - 100)]:
                    w = (grid >= st) & (grid < st + 100)
                    if w.sum() < 900:
                        continue
                    out[f"{route}_{d}_{int(st)}"] = welch(z[w], fs=10.0, nperseg=NPER, noverlap=NPER // 2, window="hann",
                                                          detrend="linear")[1]
    return out


def main():
    U, _ = load_lira()
    psd = np.load(os.path.join(PROCESSED, "v2", "spectra_real.npz"))["psd50"].astype(float)
    Gs = segment_spectra({k: g.start_m.unique() for k, g in U.groupby(["route", "direction"])})
    have = U.segment.isin(Gs.keys()).to_numpy() & np.isfinite(psd).all(1)
    print("units with road spectrum and acceleration PSD:", have.sum(), "of", len(U), flush=True)

    # (check) spectral IRI formula on the TRUE profile spectra vs the validated IRI
    segs = U.drop_duplicates("segment").set_index("segment")
    chk = pd.DataFrame([dict(segment=k, y=segs.mri.get(k, np.nan), cls=segs.cls.get(k, None),
                             iri_spec=iri_from_spectrum(NGRID[1:], G[1:])) for k, G in Gs.items()]).dropna()
    r = float(np.corrcoef(np.log(chk.iri_spec), np.log(chk.y))[0, 1])
    ratio = chk.iri_spec / chk.y
    check = dict(n_segments=len(chk), log_pearson=r, median_ratio=float(ratio.median()),
                 median_ratio_urban=float(ratio[chk.cls == "urban"].median()), median_ratio_motorway=float(ratio[chk.cls == "motorway"].median()))

    v = U.v_mean.to_numpy()
    # road temporal spectrum S_r(f) for every unit (log-log interpolation of G at n = f / v)
    Sr = np.full((len(U), BAND.sum()), np.nan)
    lg = {k: np.log(np.maximum(G[1:], 1e-16)) for k, G in Gs.items()}
    ln = np.log(NGRID[1:])
    fb = F50[BAND]
    for i in np.where(have)[0]:
        n = fb / v[i]
        Sr[i] = np.exp(np.interp(np.log(n), ln, lg[U.segment.iat[i]])) / v[i]
    Sa = psd[:, BAND]
    logT_unit = np.log(Sa + 1e-16) - np.log(Sr)

    rows, trans = [], []
    w = 2 * np.pi * fb
    for R in LIRA_ROUTES:
        tr = have & (U.route != R).to_numpy(); te = np.where(have & (U.route == R).to_numpy())[0]
        logT = np.median(logT_unit[tr], 0)

        def resid(th):
            K1, K2, C, Uu, lg_ = th
            ha, _ = qc_tf(w, K1, K2, C, Uu)
            return np.log(np.abs(ha) ** 2) + 2 * lg_ - logT
        best = None
        for x0 in ([653, 63.3, 6, 0.15, 0.0], [400, 40, 4, 0.1, 0.5], [1200, 120, 12, 0.25, -0.5], [800, 60, 10, 0.12, 0.0]):
            sol = least_squares(resid, x0, bounds=([100, 20, 1, 0.05, -3], [3000, 300, 40, 0.4, 3]))
            if best is None or sol.cost < best.cost:
                best = sol
        K1, K2, C, Uu, lg_ = best.x
        ha, _ = qc_tf(w, K1, K2, C, Uu)
        H2 = np.abs(ha) ** 2 * np.exp(2 * lg_)
        for f_, t_, m_ in zip(fb, logT, np.log(H2)):
            trans.append(dict(fold=R, freq_hz=f_, log_T_empirical=t_, log_T_quartercar=m_))

        def iri_units(idx):
            out = np.full(len(idx), np.nan)
            for j, i in enumerate(idx):
                n = fb / v[i]
                Ghat = (Sa[i] / H2) * v[i]
                o = np.argsort(n)
                out[j] = iri_from_spectrum(n[o], Ghat[o])
            return out
        p_te = iri_units(te)
        tr_idx = np.where(tr)[0]
        p_tr = iri_units(tr_idx)
        St = seg_table(U, tr_idx, p_tr)                      # calibration on training-route segments
        X = np.column_stack([np.ones(len(St)), St.lp])
        a, b = np.linalg.lstsq(X, np.log(St.y + EPS), rcond=None)[0]
        for name, p in (("M7 quarter-car inversion (uncalibrated)", p_te),
                        ("M7cal quarter-car inversion + log-linear calibration", np.exp(a + b * np.log(p_te + EPS)) - EPS)):
            S = seg_table(U, te, p)
            rows.append(dict(fold=R, model=name, mae=float(np.mean(np.abs(S.p - S.y))), bias=float(np.mean(S.p - S.y)),
                             rho=float(pd.Series(S.p).corr(pd.Series(S.y), method="spearman")), n_seg=len(S),
                             K1=K1, K2=K2, C=C, U=Uu, gain=float(np.exp(lg_)), cal_a=float(a), cal_b=float(b),
                             fit_rmse_log=float(np.sqrt(np.mean(resid(best.x) ** 2)))))
            pd.DataFrame(dict(segment=S.segment, y=S.y, p=S.p, model=name, fold=R)).to_csv(
                os.path.join(OUT, "physics_inversion_segments.csv"), mode="a", index=False,
                header=not os.path.exists(os.path.join(OUT, "physics_inversion_segments.csv")))
        print(rows[-2]); print(rows[-1], flush=True)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "physics_inversion.csv"), index=False)
    pd.DataFrame(trans).to_csv(os.path.join(OUT, "physics_transmissibility.csv"), index=False)
    seg = pd.read_csv(os.path.join(OUT, "physics_inversion_segments.csv"))
    pooled = {m: dict(mae=float(np.mean(np.abs(g.p - g.y))), bias=float(np.mean(g.p - g.y))) for m, g in seg.groupby("model")}
    check["pooled"] = pooled
    json.dump(check, open(os.path.join(OUT, "physics_inversion_check.json"), "w"), indent=1)
    print(json.dumps(check, indent=1))


if __name__ == "__main__":
    p = os.path.join(OUT, "physics_inversion_segments.csv")
    if os.path.exists(p):
        os.remove(p)
    main()
