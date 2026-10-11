"""Accelerometer / speed-sensor measurement model for simulated passes (config/sim_ranges.json).

True vehicle-frame specific force f = [a_long, a_lat, g + a_s] -> (optional cradle compliance, 2nd-order
resonant low-pass) -> device anti-alias low-pass (0.4 fs) -> small-angle mounting rotation -> irregular
sampling with timing jitter -> scale/bias error -> white noise -> quantisation -> random sample loss.
Every perturbation can be overridden for robustness sweeps.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt, bilinear, tf2sos

G0 = 9.80665


def _rot(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = np.cos(roll), np.sin(roll), np.cos(pitch), np.sin(pitch), np.cos(yaw), np.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def sample_sensor(rng, cfg: dict) -> dict:
    u = lambda k: float(rng.uniform(*cfg[k]))
    s = dict(rate_hz=u("rate_hz"), jitter=cfg["rate_jitter_rel"], lsb_g=cfg["lsb_g"], noise_ug=u("noise_ug_rthz"),
             bias=rng.uniform(*cfg["bias_g"], 3), scale=rng.uniform(*cfg["scale_err"], 3),
             tilt=np.deg2rad(rng.normal(0, cfg["tilt_deg_sd"], 3)), mount=bool(cfg.get("mount_compliance", False)),
             missing=0.0)
    if s["mount"]:
        s["mount_f"] = u("mount_f_hz"); s["mount_zeta"] = u("mount_zeta")
    return s


def measure(rng, t: np.ndarray, a_s: np.ndarray, a_long: np.ndarray, fs_sim: float, sens: dict):
    n = len(t)
    f = np.column_stack([a_long / G0, rng.normal(0, 0.01, n), 1.0 + a_s / G0])
    if sens.get("mount"):
        w = 2 * np.pi * sens["mount_f"]; z = sens["mount_zeta"]
        b, a = bilinear([w * w], [1, 2 * z * w, w * w], fs=fs_sim)
        sos = tf2sos(b, a)
        f = np.column_stack([sosfilt(sos, f[:, i] - f[0, i]) + f[0, i] for i in range(3)])
    fc = min(0.4 * sens["rate_hz"], 0.45 * fs_sim)
    sos = butter(2, fc, fs=fs_sim, output="sos")
    f = np.column_stack([sosfilt(sos, f[:, i] - f[0, i]) + f[0, i] for i in range(3)])
    f = f @ _rot(*sens["tilt"]).T
    dt = (1.0 / sens["rate_hz"]) * (1 + rng.uniform(-sens["jitter"], sens["jitter"], int(t[-1] * sens["rate_hz"] * 1.2) + 10))
    td = np.cumsum(dt); td = td[td < t[-1]]
    fd = np.column_stack([np.interp(td, t, f[:, i]) for i in range(3)])
    fd = fd * (1 + sens["scale"]) + sens["bias"]
    sigma = sens["noise_ug"] * 1e-6 * np.sqrt(sens["rate_hz"] / 2.0)
    fd = fd + rng.normal(0, sigma, fd.shape)
    if sens["lsb_g"] > 0:
        fd = np.round(fd / sens["lsb_g"]) * sens["lsb_g"]
    if sens.get("missing", 0) > 0:
        keep = rng.random(len(td)) >= sens["missing"]
        keep[0] = keep[-1] = True
        td, fd = td[keep], fd[keep]
    return td, fd


def measure_speed(rng, t: np.ndarray, v: np.ndarray, mode: str = "can", rel_err: float = 0.0, cfg: dict | None = None):
    """Returns speed on the simulation time grid as a vehicle would report it."""
    cfg = cfg or {"can_rel_noise": 0.005, "gps_rate_hz": 1.0, "gps_sd_ms": 0.3}
    if mode == "gps":
        tg = np.arange(t[0], t[-1], 1.0 / cfg["gps_rate_hz"])
        vg = np.interp(tg, t, v) + rng.normal(0, cfg["gps_sd_ms"], len(tg))
        vm = np.interp(t, tg, vg)
    else:
        vm = v * (1 + rng.normal(0, cfg["can_rel_noise"], len(v)))
    return np.clip(vm * (1 + rel_err), 0.0, None)
