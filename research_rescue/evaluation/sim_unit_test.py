"""Unit tests of the parametric simulator and the shared preprocessing (results/sim_unit_test.json)."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.linalg import expm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import vehsim, sensor, preprocess as PP  # noqa: E402
from common.paths import RESULTS  # noqa: E402


def main():
    rng = np.random.default_rng(1)
    res = {}
    # 1. modal solver == direct state-space recursion
    worst = 0.0
    for _ in range(20):
        veh = vehsim.sample_vehicle(rng); A, B, C, _ = vehsim.half_car(veh)
        mod = vehsim.discrete_modal(A, B, C, 500.0)
        from scipy.signal import cont2discrete
        Ad, Bd, Cd, Dd, _ = cont2discrete((A, B, C, np.zeros((1, 2))), 1 / 500.0, method="foh")
        u = np.cumsum(rng.normal(0, 1e-4, (20000, 2)), axis=0)
        x = np.zeros(8); y_ref = np.empty(len(u))
        for k in range(len(u)):
            y_ref[k] = (Cd @ x + Dd @ u[k])[0]; x = Ad @ x + Bd @ u[k]
        worst = max(worst, float(np.max(np.abs(vehsim.modal_response(mod, u) - y_ref)) / np.max(np.abs(y_ref))))
    res["modal_vs_direct_max_rel_dev"] = worst
    # 2. modal frequencies of 500 random vehicles
    lo, hi = [], []
    for _ in range(500):
        A, *_ = vehsim.half_car(vehsim.sample_vehicle(rng))
        ev = np.linalg.eigvals(A)
        f = np.sort(np.abs(ev[ev.imag > 0]) / (2 * np.pi))       # undamped natural frequencies of the 4 modes
        lo.append(f[:2]); hi.append(f[2:])
    lo, hi = np.array(lo), np.array(hi)
    res["body_modes_hz_range"] = [float(lo.min()), float(lo.max())]
    res["wheel_hop_hz_range"] = [float(hi.min()), float(hi.max())]
    # 3. constant-grade ramp -> no dynamic acceleration after the start-up transient
    veh = vehsim.sample_vehicle(rng)
    ramp = 0.03 * np.arange(0, 2000, 0.05)
    sim = vehsim.simulate_pass(ramp, 0.05, 0.0, np.full(int(60 * 500), 20.0), 500.0, veh)
    from scipy.signal import butter as _b, sosfiltfilt as _f
    a_lp = _f(_b(4, 20.0, fs=500.0, output="sos"), sim["a_s"])   # analysis band (ZOH staircase ripple is at 500 Hz)
    res["ramp_steady_accel_rms_ms2"] = float(np.sqrt(np.mean(a_lp[int(10 * 500):-int(5 * 500)] ** 2)))
    # 4. ideal sensor through the real-data preprocessing preserves the 0.3-20 Hz vibration level
    z = vehsim.synthetic_route(rng, 3000, 0.05)
    sim = vehsim.simulate_pass(z, 0.05, 0.0, np.full(int(200 * 500), 15.0), 500.0, veh)
    ideal = dict(rate_hz=500.0, jitter=0.0, lsb_g=0.0, noise_ug=0.0, bias=np.zeros(3), scale=np.zeros(3),
                 tilt=np.zeros(3), mount=False, missing=0.0)
    td, fd = sensor.measure(rng, sim["t"], sim["a_s"], sim["a_long"], 500.0, ideal)
    t50, a_dyn = PP.vertical_dynamic(td, fd)
    from scipy.signal import butter, sosfiltfilt
    ref = sosfiltfilt(butter(4, [0.3, 20.0], btype="bandpass", fs=500.0, output="sos"), sim["a_s"])
    m = (t50 > 10) & (t50 < t50[-1] - 10)
    res["preprocess_rms_ratio_ideal_sensor"] = float(np.sqrt(np.mean(a_dyn[m] ** 2)) / np.sqrt(np.mean(ref[int(10 * 500):-int(10 * 500)] ** 2)))
    # 5. modal FOH solver == continuous-time dynamics (classical RK4, 10 sub-steps per sample, input linear in each sample
    #    interval as assumed by the first-order hold), for random vehicles and random-walk wheel inputs
    worst_rk = 0.0
    fs, sub = 500.0, 10
    for _ in range(5):
        veh = vehsim.sample_vehicle(rng); A, B, C, _ = vehsim.half_car(veh)
        mod = vehsim.discrete_modal(A, B, C, fs)
        u = np.cumsum(rng.normal(0, 1e-4, (10000, 2)), axis=0)
        u -= u[0]           # same initial condition for both: system at rest, road at zero (FOH state 0 == x 0 only if u[0] == 0)
        h = 1.0 / (fs * sub)
        f = lambda x, uu: A @ x + B @ uu
        x = np.zeros(A.shape[0]); y_rk = np.empty(len(u)); y_rk[0] = (C @ x)[0]
        for k in range(len(u) - 1):
            du = (u[k + 1] - u[k]) / sub
            for j in range(sub):
                u0 = u[k] + j * du; uh = u0 + 0.5 * du; u1 = u0 + du
                k1 = f(x, u0); k2 = f(x + 0.5 * h * k1, uh); k3 = f(x + 0.5 * h * k2, uh); k4 = f(x + h * k3, u1)
                x = x + h / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
            y_rk[k + 1] = (C @ x)[0]
        worst_rk = max(worst_rk, float(np.max(np.abs(vehsim.modal_response(mod, u) - y_rk)) / np.max(np.abs(y_rk))))
    res["modal_vs_rk4_max_rel_dev"] = worst_rk
    res["passed"] = bool(res["modal_vs_direct_max_rel_dev"] < 1e-8 and 0.9 <= res["body_modes_hz_range"][0] and
                         res["body_modes_hz_range"][1] <= 3.0 and 6 <= res["wheel_hop_hz_range"][0] and res["wheel_hop_hz_range"][1] <= 18 and
                         res["ramp_steady_accel_rms_ms2"] < 1e-3 and 0.9 <= res["preprocess_rms_ratio_ideal_sensor"] <= 1.1 and
                         res["modal_vs_rk4_max_rel_dev"] < 1e-3)
    json.dump(res, open(os.path.join(RESULTS, "sim_unit_test.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
