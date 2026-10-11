"""Simulation pipeline: profile -> half-car -> sensor model -> SAME preprocessing as real data -> 100 m units."""
from __future__ import annotations

import numpy as np
from scipy.signal import lfilter

from . import vehsim, sensor, preprocess as PP, iri

FS_SIM = 500.0


def ou(rng, n, fs, sd, tau):
    a = np.exp(-1 / (tau * fs)); w = rng.normal(0, sd * np.sqrt(1 - a * a), n)
    w[0] = rng.normal(0, sd)
    return lfilter([1.0], [1.0, -a], w)


def run_pass(rng, prof, dx, s0, seg_starts, veh, sens, v0_kmh=None, constant_speed=False, speed_mode="can",
             speed_rel_err=0.0, mm_sd=3.0, ranges=None):
    """Simulate one traversal of `prof` (m, grid dx starting at chainage s0) and return 100 m units."""
    R = ranges or vehsim.RANGES
    length = len(prof) * dx
    v0 = (v0_kmh if v0_kmh is not None else rng.uniform(*R["speed"]["base_kmh"])) / 3.6
    dur = (length - veh["L"]) / max(v0 * 0.6, 1.0) + 30.0
    v_t = vehsim.speed_profile(rng, dur, FS_SIM, v0, constant=constant_speed, ranges=R)
    sim = vehsim.simulate_pass(prof, dx, s0, v_t, FS_SIM, veh)
    td, fd = sensor.measure(rng, sim["t"], sim["a_s"], sim["a_long"], FS_SIM, sens)
    t50, a_dyn = PP.vertical_dynamic(td, fd)
    v_meas = sensor.measure_speed(rng, sim["t"], sim["v"], mode=speed_mode, rel_err=speed_rel_err, cfg=R["speed_sensor"])
    v50 = np.interp(t50, sim["t"], v_meas)
    c_true = np.interp(t50, sim["t"], sim["s_front"])
    c50 = c_true + (ou(rng, len(t50), PP.FS, mm_sd, 30.0) if mm_sd > 0 else 0.0)
    units, feats, seqs = PP.extract_units(a_dyn, v50, c50, seg_starts)
    for u in units:
        u["v0_kmh"] = v0 * 3.6
    return units, feats, seqs


def synthetic_labels(z, dx, s0, seg_starts):
    rs, pos = iri.continuous_rectified_slope(z, dx)
    return iri.window_iri(rs, pos + s0, np.asarray(seg_starts, float), PP.SEG)
