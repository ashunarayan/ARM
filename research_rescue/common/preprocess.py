"""Signal preprocessing and 100 m unit extraction shared by REAL (LiRA-CD) and SIMULATED data, so that both
domains go through byte-identical code."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt

from . import features as F

FS = 50.0
G0 = 9.80665
SEG = 100.0


def uniform_acc(t: np.ndarray, xyz: np.ndarray):
    """Irregular 3-axis samples -> 200 Hz linear interpolation -> zero-phase 20 Hz low-pass -> 50 Hz."""
    o = np.argsort(t); t = np.asarray(t)[o]; xyz = np.asarray(xyz)[o]
    keep = np.concatenate([[True], np.diff(t) > 0]); t = t[keep]; xyz = xyz[keep]
    g200 = np.arange(t[0], t[-1], 1 / 200.0)
    sos = butter(4, 20.0, fs=200.0, output="sos")
    m = np.column_stack([sosfiltfilt(sos, np.interp(g200, t, xyz[:, i])) for i in range(3)])
    return g200[::4], m[::4]


def vertical_dynamic(t: np.ndarray, xyz_g: np.ndarray):
    """Gravity alignment on the mean acceleration direction (removes static mounting tilt), conversion to
    m/s^2, 0.3 Hz high-pass. Returns (t50, a_dyn)."""
    t50, xyz = uniform_acc(t, xyz_g)
    ghat = xyz.mean(0); ghat = ghat / np.linalg.norm(ghat)
    a_vert = (xyz @ ghat) * G0
    return t50, F.remove_gravity(a_vert, FS)


def extract_units(a_dyn: np.ndarray, v50: np.ndarray, c50: np.ndarray, seg_starts: np.ndarray,
                  min_cov: float = 0.9, min_speed: float = 2.0):
    """Cut 100 m units [st, st+100) on the chainage axis c50 (NaN where unmatched). A unit needs one
    contiguous traversal covering >= min_cov of the segment and mean speed >= min_speed."""
    units, feats, seqs = [], [], []
    for st in seg_starts:
        sel = (c50 >= st) & (c50 < st + SEG)
        if sel.sum() < 20:
            continue
        idx = np.where(sel)[0]
        if idx[-1] - idx[0] + 1 != len(idx):
            continue
        cov = c50[idx[-1]] - c50[idx[0]]
        vw = v50[idx]
        if cov < min_cov * SEG or vw.mean() < min_speed:
            continue
        aw = a_dyn[idx]
        feats.append(F.window_features(aw, vw, FS))
        seqs.append(np.stack([F.spatial_resample(c50[idx], aw, st), F.spatial_resample(c50[idx], vw, st)], axis=1))
        units.append(dict(start_m=float(st), v_mean=float(vw.mean()), v_std=float(vw.std()), dur_s=float(len(idx) / FS),
                          coverage_m=float(cov), a_rms=float(np.sqrt(np.mean(aw ** 2)))))
    return units, feats, seqs
