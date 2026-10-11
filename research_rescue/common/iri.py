"""Canonical International Roughness Index (IRI) implementation.

Follows the quarter-car ("Golden Car") algorithm of Sayers (1995, TRR 1501) as standardised in
ASTM E1926:
  * the profile slope is computed over a 250 mm base, which equals the slope of a 250 mm
    moving-average-smoothed profile (k = max(1, nint(0.25/dx)) samples);
  * the Golden-Car state equations are discretised exactly (matrix exponential, zero-order hold)
    for the time step dt = dx / (80 km/h);
  * the state is initialised with the average slope over the first 11 m (x1 = x3 = s0, x2 = x4 = 0);
  * the rectified slope RS = |x1 - x3| (m/m) is accumulated; IRI = 1000 * mean(RS) [m/km].

Two equivalent solvers are provided: a reference Python loop (`_rs_loop`) and a fast linear-filter
version (`_rs_fast`, zero-state response by scipy.signal.lfilter + zero-input response by explicit
state propagation). `self_test()` checks they agree to numerical precision.

`continuous_rectified_slope` runs the model once over a whole profile; the IRI of any window is the
mean RS inside that window (how continuous profilers report per-interval roughness). This avoids
per-window re-initialisation artefacts and lets overlapping windows receive exact labels.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import expm
from scipy.signal import lfilter, ss2tf

GOLDEN_CAR = dict(k1=653.0, k2=63.3, mu=0.15, c=6.0)   # Sayers et al. (1986) TP45/46
V_IRI = 80.0 / 3.6                                       # 22.222 m/s reference speed


def golden_car_matrices(params: dict = GOLDEN_CAR):
    k1, k2, mu, c = params["k1"], params["k2"], params["mu"], params["c"]
    A = np.array([[0.0, 1.0, 0.0, 0.0],
                  [-k2, -c, k2, c],
                  [0.0, 0.0, 0.0, 1.0],
                  [k2 / mu, c / mu, -(k1 + k2) / mu, -c / mu]])
    B = np.array([0.0, 0.0, 0.0, k1 / mu])
    return A, B


def _nint(x: float) -> int:
    """Round half away from zero (FORTRAN NINT used in the ASTM reference code)."""
    return int(np.floor(x + 0.5)) if x >= 0 else -int(np.floor(-x + 0.5))


def _discrete(dx: float):
    A, B = golden_car_matrices()
    dt = dx / V_IRI
    Ad = expm(A * dt)
    Bd = np.linalg.solve(A, (Ad - np.eye(4)) @ B)
    return Ad, Bd


def smoothed_slope(profile_m: np.ndarray, dx: float, base: float = 0.25) -> tuple[np.ndarray, int]:
    k = max(1, _nint(base / dx))
    y = np.asarray(profile_m, dtype=float)
    return (y[k:] - y[:-k]) / (k * dx), k


def initial_slope(profile_m: np.ndarray, dx: float, init_len: float = 11.0) -> float:
    y = np.asarray(profile_m, dtype=float)
    i = min(_nint(init_len / dx), len(y) - 1)
    return (y[i] - y[0]) / (i * dx) if i > 0 else 0.0


def _rs_loop(slope: np.ndarray, Ad: np.ndarray, Bd: np.ndarray, s0: float) -> np.ndarray:
    a = Ad.tolist(); b = Bd.tolist()
    x1, x2, x3, x4 = s0, 0.0, s0, 0.0
    out = np.empty(len(slope))
    for i, u in enumerate(slope.tolist()):
        n1 = a[0][0] * x1 + a[0][1] * x2 + a[0][2] * x3 + a[0][3] * x4 + b[0] * u
        n2 = a[1][0] * x1 + a[1][1] * x2 + a[1][2] * x3 + a[1][3] * x4 + b[1] * u
        n3 = a[2][0] * x1 + a[2][1] * x2 + a[2][2] * x3 + a[2][3] * x4 + b[2] * u
        n4 = a[3][0] * x1 + a[3][1] * x2 + a[3][2] * x3 + a[3][3] * x4 + b[3] * u
        x1, x2, x3, x4 = n1, n2, n3, n4
        out[i] = abs(x1 - x3)
    return out


def _rs_fast(slope: np.ndarray, Ad: np.ndarray, Bd: np.ndarray, s0: float, zi_steps: int = 20000) -> np.ndarray:
    # Output after each update: y[k] = C x[k+1] = (C Ad) x[k] + (C Bd) u[k]
    C = np.array([[1.0, 0.0, -1.0, 0.0]])
    num, den = ss2tf(Ad, Bd.reshape(4, 1), C @ Ad, C @ Bd.reshape(4, 1))
    y = lfilter(num[0], den, slope)
    # zero-input response from x0 = [s0, 0, s0, 0]
    x = np.array([s0, 0.0, s0, 0.0])
    n = min(len(slope), zi_steps)
    yzi = np.empty(n)
    CA = (C @ Ad)[0]
    for i in range(n):
        yzi[i] = CA @ x
        x = Ad @ x
    y[:n] += yzi
    return np.abs(y)


def continuous_rectified_slope(profile_m: np.ndarray, dx: float, fast: bool = True,
                               base: float = 0.25, init_len: float = 11.0) -> tuple[np.ndarray, np.ndarray]:
    """Returns (rs, pos): rectified slope per slope interval (m/m) and the interval centre position
    (m, relative to the first profile sample)."""
    slope, k = smoothed_slope(profile_m, dx, base)
    Ad, Bd = _discrete(dx)
    s0 = initial_slope(profile_m, dx, init_len)
    rs = (_rs_fast if fast else _rs_loop)(slope, Ad, Bd, s0)
    pos = (np.arange(len(slope)) + 0.5 * k) * dx
    return rs, pos


def iri(profile_m: np.ndarray, dx: float, **kw) -> float:
    """IRI (m/km) of a whole profile (ASTM-style single section)."""
    rs, _ = continuous_rectified_slope(profile_m, dx, **kw)
    return 1000.0 * float(np.mean(rs)) if len(rs) else float("nan")


def window_iri(rs: np.ndarray, pos: np.ndarray, starts: np.ndarray, length: float) -> np.ndarray:
    """Mean-RS IRI (m/km) for windows [start, start+length) using a continuous RS series."""
    cs = np.concatenate([[0.0], np.cumsum(rs)])
    i0 = np.searchsorted(pos, starts, side="left")
    i1 = np.searchsorted(pos, np.asarray(starts) + length, side="left")
    n = i1 - i0
    out = np.full(len(i0), np.nan)
    ok = n > 0
    out[ok] = 1000.0 * (cs[i1[ok]] - cs[i0[ok]]) / n[ok]
    return out


def self_test(seed: int = 0) -> dict:
    """Checks (1) fast == loop, (2) a sinusoidal profile gives the analytic Golden-Car gain,
    (3) a straight ramp gives IRI ~ 0."""
    rng = np.random.default_rng(seed)
    dx = 0.1
    prof = np.cumsum(rng.normal(0, 1e-3, 20000)) * 0.05
    rs_f, _ = continuous_rectified_slope(prof, dx, fast=True)
    rs_l, _ = continuous_rectified_slope(prof, dx, fast=False)
    max_abs = float(np.max(np.abs(rs_f - rs_l)))
    # Analytic check: steady-state RS for a sinusoidal slope input of amplitude S at wavelength L
    # is |H(j w)| * S * (2/pi) on average, with w = 2*pi*V/L (rectified sine mean = 2/pi * amplitude).
    A, B = golden_car_matrices()
    C = np.array([1.0, 0.0, -1.0, 0.0])
    L = 5.0
    w = 2 * np.pi * V_IRI / L
    H = C @ np.linalg.solve(1j * w * np.eye(4) - A, B)
    x = np.arange(0, 2000, 0.05)
    amp = 0.002
    prof_sin = amp * np.sin(2 * np.pi * x / L)
    slope_amp = amp * 2 * np.pi / L
    # 250-mm moving average attenuates the slope amplitude by sinc(pi*0.25/L)
    att = np.sinc(0.25 / L)
    rs_sin, pos = continuous_rectified_slope(prof_sin, 0.05)
    iri_num = 1000 * np.mean(rs_sin[pos > 200])
    iri_ana = 1000 * abs(H) * slope_amp * att * 2 / np.pi
    ramp = 0.03 * np.arange(0, 500, 0.1)
    return dict(fast_vs_loop_max_abs_diff=max_abs,
                sine_numeric_iri=float(iri_num), sine_analytic_iri=float(iri_ana),
                sine_rel_err=float(abs(iri_num - iri_ana) / iri_ana),
                ramp_iri=iri(ramp, 0.1))


if __name__ == "__main__":
    print(self_test())
