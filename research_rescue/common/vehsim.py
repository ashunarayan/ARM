"""Parametric vehicle simulator: linear 4-DOF half-car (bounce, pitch, front/rear unsprung masses).

The vehicle is linear time-invariant in time; speed only changes how the road is sampled in time, so the
sensor acceleration is a_s(t) = H_f * r_f(t) + H_r * r_r(t), with r_r(t) = r(s(t) - L). Each path is
discretised exactly (zero-order hold) and run as second-order sections (numerically robust).

Parameter ranges are SENSITIVITY RANGES bracketing typical passenger cars; see config/sim_ranges.json for
the documented sources and rationale. Nothing here is fitted to LiRA-CD data.
"""
from __future__ import annotations

import json
import os

import numpy as np
from scipy.linalg import expm
from scipy.signal import lfilter, cont2discrete

RANGES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "sim_ranges.json")
RANGES = json.load(open(RANGES_PATH)) if os.path.exists(RANGES_PATH) else None


def sample_vehicle(rng: np.random.Generator, ranges: dict | None = None, region: str | None = None) -> dict:
    R = (ranges or RANGES)["vehicle"]
    u = lambda k: float(rng.uniform(*R[k]["range"]))
    v = dict(m_s=u("m_s"), r_y=u("r_y"), L=u("L"), a_frac=u("a_frac"), f_s=u("f_s"),
             rear_freq_ratio=u("rear_freq_ratio"), zeta=u("zeta"), m_u=u("m_u_per_wheel"), k_t=u("k_t_per_tire"),
             x_s=u("x_s"))
    if region == "low_fs":
        v["f_s"] = float(rng.uniform(R["f_s"]["range"][0], R["f_s"]["split"]))
    elif region == "high_fs":
        v["f_s"] = float(rng.uniform(R["f_s"]["split"], R["f_s"]["range"][1]))
    return v


def half_car(v: dict):
    L = v["L"]; a = v["a_frac"] * L; b = L - a
    ms = v["m_s"]; Iy = ms * v["r_y"] ** 2
    msf, msr = ms * b / L, ms * a / L                          # static sprung load per axle
    ksf = (2 * np.pi * v["f_s"]) ** 2 * msf
    ksr = (2 * np.pi * v["f_s"] * v["rear_freq_ratio"]) ** 2 * msr
    csf = 2 * v["zeta"] * np.sqrt(ksf * msf); csr = 2 * v["zeta"] * np.sqrt(ksr * msr)
    muf = mur = 2 * v["m_u"]; ktf = ktr = 2 * v["k_t"]
    # state: [zb, th, zuf, zur, dzb, dth, dzuf, dzur]
    A = np.zeros((8, 8)); A[:4, 4:] = np.eye(4)
    B = np.zeros((8, 2))
    # suspension forces on body: Ff = ksf(zuf - zb - a th) + csf(...), Fr = ksr(zur - zb + b th) + csr(...)
    Kf = np.array([-ksf, -ksf * a, ksf, 0.0]); Cf = np.array([-csf, -csf * a, csf, 0.0])
    Kr = np.array([-ksr, ksr * b, 0.0, ksr]); Cr = np.array([-csr, csr * b, 0.0, csr])
    Ff = np.concatenate([Kf, Cf]); Fr = np.concatenate([Kr, Cr])
    A[4] = (Ff + Fr) / ms
    A[5] = (a * Ff - b * Fr) / Iy
    A[6] = -Ff / muf; A[6, 2] -= ktf / muf; B[6, 0] = ktf / muf
    A[7] = -Fr / mur; A[7, 3] -= ktr / mur; B[7, 1] = ktr / mur
    C = A[4] + v["x_s"] * A[5]                                  # sensor vertical acceleration (no feedthrough)
    return A, B, C.reshape(1, 8), dict(a=a, b=b)


def discrete_modal(A, B, C, fs: float):
    """Exact first-order-hold (piecewise-linear input) discretisation, run in modal coordinates:
    x[k+1] = Ad x[k] + Bd u[k], y[k] = Cd x[k] + Dd u[k] (scipy cont2discrete 'foh' realisation);
    xi = V^-1 x gives 8 first-order complex recursions -> numerically stable. FOH avoids the ZOH artefact
    (aliased intra-sample sawtooth) that biases the output for sloping inputs."""
    Ad, Bd, Cd, Dd, _ = cont2discrete((A, B, C, np.zeros((C.shape[0], B.shape[1]))), 1.0 / fs, method="foh")
    lam, V = np.linalg.eig(Ad)
    W = np.linalg.inv(V)
    return dict(lam=lam, CV=(Cd @ V).ravel(), WB=W @ Bd, D=np.asarray(Dd).ravel())


def modal_response(mod: dict, U: np.ndarray) -> np.ndarray:
    """y[k] = Cd x[k] + Dd u[k] for inputs U (n, n_in), zero initial state."""
    n = U.shape[0]
    y = np.zeros(n, dtype=complex)
    for i, lam in enumerate(mod["lam"]):
        drive = U @ mod["WB"][i]
        xi_next = lfilter([1.0], [1.0, -lam], drive)
        y[1:] += mod["CV"][i] * xi_next[:-1]
    return y.real + U @ mod["D"]


def tyre_envelope(profile: np.ndarray, dx: float, base: float = 0.25) -> np.ndarray:
    k = max(1, int(round(base / dx)))
    if k <= 1:
        return profile
    ker = np.ones(k) / k
    return np.convolve(np.pad(profile, (k // 2, k - 1 - k // 2), mode="edge"), ker, mode="valid")


def simulate_pass(profile: np.ndarray, dx: float, s0: float, v_t: np.ndarray, fs: float, veh: dict, mod=None):
    """profile: elevation (m) on a uniform grid of spacing dx starting at chainage s0 (front-wheel track);
    v_t: speed (m/s) at fs, starting with the front axle at chainage s0 + L (so the rear wheel is on the
    profile from the start). Returns dict(t, s_front, v, a_s, a_long)."""
    if mod is None:
        A, B, C, geom = half_car(veh)
        mod = discrete_modal(A, B, C, fs)
    prof = tyre_envelope(profile, dx)
    s = s0 + veh["L"] + np.concatenate([[0.0], np.cumsum(v_t[:-1]) / fs])
    xg = s0 + np.arange(len(prof)) * dx
    end = s < xg[-1]
    s, vv = s[end], v_t[end]
    rf = np.interp(s, xg, prof); rr = np.interp(s - veh["L"], xg, prof)
    # remove initial offset to avoid a start-up transient
    rf -= rf[0]; rr -= rr[0]
    a_s = modal_response(mod, np.column_stack([rf, rr]))
    a_long = np.gradient(vv) * fs
    return dict(t=np.arange(len(s)) / fs, s_front=s, v=vv, a_s=a_s, a_long=a_long)


def speed_profile(rng, duration_s: float, fs: float, v0: float, constant: bool = False, ranges: dict | None = None):
    """Base speed v0 with an Ornstein-Uhlenbeck fluctuation and random braking/acceleration events."""
    n = int(duration_s * fs)
    if constant:
        return np.full(n, v0)
    R = (ranges or RANGES)["speed"]
    tau, sig = R["ou_tau_s"], R["ou_rel_sigma"]
    a = np.exp(-1 / (tau * fs)); w = rng.normal(0, sig * np.sqrt(1 - a * a), n)
    x = lfilter([1.0], [1.0, -a], w)
    v = v0 * (1 + x)
    # braking events: Poisson in time
    t = 0.0
    while True:
        t += rng.exponential(R["event_mean_interval_s"])
        if t * fs >= n:
            break
        dec = rng.uniform(*R["decel_ms2"]); acc = rng.uniform(*R["accel_ms2"]); frac = rng.uniform(*R["event_min_speed_frac"])
        i0 = int(t * fs); dv = v0 * (1 - frac)
        n_dec, n_acc = int(dv / dec * fs), int(dv / acc * fs)
        prof = np.concatenate([np.linspace(0, dv, max(n_dec, 1)), np.linspace(dv, 0, max(n_acc, 1))])
        j1 = min(n, i0 + len(prof))
        v[i0:j1] -= prof[:j1 - i0]
    return np.clip(v, R["v_min_ms"], R["v_max_ms"])


def iso8608_profile(rng, length_m: float, dx: float, gd_n0: float, w: float = 2.0, n0: float = 0.1,
                    n_lo: float = 0.011, n_hi: float = 10.0) -> np.ndarray:
    """Random profile with displacement PSD Gd(n) = gd_n0 (n/n0)^-w (ISO 8608), spectral synthesis."""
    N = int(length_m / dx)
    n = np.fft.rfftfreq(N, dx)
    dn = n[1] - n[0]
    G = np.zeros_like(n); m = (n >= n_lo) & (n <= n_hi)
    G[m] = gd_n0 * (n[m] / n0) ** (-w)
    amp = np.sqrt(G * dn)                               # one-sided PSD -> amplitude of each harmonic
    ph = rng.uniform(0, 2 * np.pi, len(n))
    spec = amp * np.exp(1j * ph) * N / 2
    return np.fft.irfft(spec, N)


def synthetic_route(rng, length_m: float, dx: float, ranges: dict | None = None) -> np.ndarray:
    """Concatenation of 200-1000 m sections with log-uniform roughness class, plus discrete events."""
    R = (ranges or RANGES)["synthetic"]
    out = []
    total = 0.0
    while total < length_m:
        Ls = rng.uniform(*R["section_m"])
        gd = float(np.exp(rng.uniform(np.log(R["gd_n0_range"][0]), np.log(R["gd_n0_range"][1]))))
        z = iso8608_profile(rng, Ls + 50, dx, gd)
        # discrete events (potholes as half-sine dips, joints as small steps)
        n_ev = rng.poisson(R["events_per_100m"] * Ls / 100.0) if rng.random() < R["event_section_prob"] else 0
        x = np.arange(len(z)) * dx
        for _ in range(n_ev):
            c = rng.uniform(0, Ls); wdt = rng.uniform(*R["pothole_len_m"]); d = rng.uniform(*R["pothole_depth_m"])
            m = np.abs(x - c) < wdt / 2
            z[m] -= d * np.cos(np.pi * (x[m] - c) / wdt)
        if out:   # smooth junction: match level
            z += out[-1][-1] - z[0]
        out.append(z[: int(Ls / dx)])
        total += Ls
    return np.concatenate(out)[: int(length_m / dx)]
