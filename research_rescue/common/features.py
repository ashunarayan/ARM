"""Domain-independent window features shared by BeamNG, LiRA-CD and the parametric simulator.

Input per window: dynamic vertical acceleration a(t) [m/s^2] (gravity removed) on a uniform time grid
at fs Hz, and speed v(t) [m/s]. Features are physically interpretable and contain no position/route
identifiers.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

BANDS_HZ = [(0.5, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 15.0)]
FEATURE_NAMES = (["log_v_mean", "v_cv", "log_rms", "log_p95_abs", "log_max_abs", "crest", "kurtosis"]
                 + [f"log_band_{lo:g}_{hi:g}" for lo, hi in BANDS_HZ]
                 + ["log_rms_hp1", "log_rms_spatial_lt5m"])
SPEED_FREE = [n for n in FEATURE_NAMES if not n.startswith(("log_v_mean", "v_cv"))]


def remove_gravity(a: np.ndarray, fs: float, cutoff_hz: float = 0.3) -> np.ndarray:
    """High-pass (zero-phase Butterworth) to remove gravity, grade and slow attitude changes."""
    if len(a) < 3 * int(fs):
        return a - np.mean(a)
    sos = butter(2, cutoff_hz, btype="highpass", fs=fs, output="sos")
    return sosfiltfilt(sos, a)


def band_rms(a: np.ndarray, fs: float, lo: float, hi: float) -> float:
    if hi >= fs / 2:
        hi = 0.98 * fs / 2
    if lo >= hi or len(a) < 16:
        return np.nan
    f, p = welch(a, fs=fs, nperseg=min(len(a), 256))
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(np.trapezoid(p[m], f[m]))) if m.sum() > 1 else np.nan


def window_features(a: np.ndarray, v: np.ndarray, fs: float, eps: float = 1e-4) -> np.ndarray:
    a = np.asarray(a, float); v = np.asarray(v, float)
    vm = max(float(np.mean(v)), 0.5)
    rms = float(np.sqrt(np.mean(a ** 2)))
    absa = np.abs(a)
    p95 = float(np.percentile(absa, 95)); mx = float(absa.max())
    kurt = float(np.mean((a - a.mean()) ** 4) / (np.var(a) ** 2 + 1e-12))
    bands = [band_rms(a, fs, lo, hi) for lo, hi in BANDS_HZ]
    # 1 Hz high-pass RMS (suppresses body-pitch / driver-induced content)
    if len(a) > 3 * fs:
        hp1 = sosfiltfilt(butter(2, 1.0, btype="highpass", fs=fs, output="sos"), a)
        rms_hp1 = float(np.sqrt(np.mean(hp1 ** 2)))
    else:
        rms_hp1 = rms
    # content with spatial wavelength < 5 m: temporal frequency > v/5
    fc = vm / 5.0
    rms_sp = band_rms(a, fs, fc, min(25.0, 0.98 * fs / 2))
    f = [np.log(vm), float(np.std(v) / vm), np.log(rms + eps), np.log(p95 + eps), np.log(mx + eps),
         mx / (rms + eps), kurt] + [np.log((b if np.isfinite(b) else 0.0) + eps) for b in bands] + \
        [np.log(rms_hp1 + eps), np.log((rms_sp if np.isfinite(rms_sp) else 0.0) + eps)]
    return np.array(f, dtype=np.float32)


def resample_uniform(t: np.ndarray, y: np.ndarray, fs: float):
    t = np.asarray(t, float)
    grid = np.arange(t[0], t[-1], 1.0 / fs)
    return grid, np.interp(grid, t, y)


def spatial_resample(dist: np.ndarray, y: np.ndarray, start: float, length: float = 100.0, n: int = 400) -> np.ndarray:
    grid = start + (np.arange(n) + 0.5) * (length / n)
    return np.interp(grid, dist, y).astype(np.float32)
