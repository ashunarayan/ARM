"""Verbatim re-implementations of the rejected paper's recipe (for 'legacy recipe under clean protocol').

Sources (unchanged logic):
  * extract_context_features / kinetic normalisation: ml_model/iri_v3/data_pipeline.py
  * 2-D inverse-frequency sample weights:             ml_model/iri_v3/trainer.py
  * asymmetric Huber loss (delta=2, ratio=4) on log1p targets: ml_model/iri_v3/model.py
"""
from __future__ import annotations

import numpy as np

V_REF = 22.22
V_SAFE = 5.0


def kinetic_normalise(az: np.ndarray, v: np.ndarray) -> np.ndarray:
    return az * (V_REF / np.maximum(v, V_SAFE)) ** 2


def extract_context_features(raw_data_window: np.ndarray, speed_array: np.ndarray) -> np.ndarray:
    ax, ay, az, wx, wy, wz = [raw_data_window[:, i] for i in range(6)]
    N = len(az)
    speed_mean = np.mean(speed_array); speed_std = np.std(speed_array)
    rms_az = np.sqrt(np.mean(az ** 2)); rms_ay = np.sqrt(np.mean(ay ** 2)); var_az = np.var(az)
    crest_factor_az = np.max(np.abs(az)) / (rms_az + 1e-6)
    zero_crossings_az = len(np.where(np.diff(np.sign(az)))[0])
    mcr_az = zero_crossings_az / N
    p2p_az = np.max(az) - np.min(az)
    rms_wz = np.sqrt(np.mean(wz ** 2)); rms_wy = np.sqrt(np.mean(wy ** 2)); mean_abs_ax = np.mean(np.abs(ax))
    psd = np.abs(np.fft.rfft(az)) ** 2
    freqs_spatial = np.fft.rfftfreq(N, d=0.25)
    if speed_mean > 0:
        ft = freqs_spatial * speed_mean
        b14 = np.sum(psd[(ft >= 1.0) & (ft <= 4.0)]); b415 = np.sum(psd[(ft > 4.0) & (ft <= 15.0)])
        tot = np.sum(psd) + 1e-6
        e14, e415 = b14 / tot, b415 / tot
    else:
        e14 = e415 = 0.0
    return np.array([speed_mean, speed_std, rms_az, rms_ay, var_az, crest_factor_az, mcr_az, p2p_az,
                     rms_wz, rms_wy, mean_abs_ax, e14, e415], dtype=np.float32)


def compute_2d_sample_weights(speeds, iris, num_speed_bins=10, num_iri_bins=10):
    speed_bins = np.linspace(np.min(speeds), np.max(speeds), num_speed_bins + 1)
    iri_bins = np.linspace(np.min(iris), np.max(iris), num_iri_bins + 1)
    si = np.clip(np.digitize(speeds, speed_bins) - 1, 0, num_speed_bins - 1)
    ii = np.clip(np.digitize(iris, iri_bins) - 1, 0, num_iri_bins - 1)
    H, _, _ = np.histogram2d(speeds, iris, bins=[speed_bins, iri_bins])
    w = np.array([1.0 / H[a, b] if H[a, b] > 0 else 0.0 for a, b in zip(si, ii)], dtype=np.float32)
    w = w / np.mean(w)
    w = np.clip(w, 0, np.percentile(w, 99))
    return w / np.mean(w)
