"""Small geodesy helpers (local tangent-plane projection, polyline chainage)."""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

R_EARTH = 6371008.8


def to_local_xy(lat: np.ndarray, lon: np.ndarray, lat0: float, lon0: float) -> np.ndarray:
    """Equirectangular projection around (lat0, lon0); metric error < 0.1 % over ~50 km."""
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    x = np.deg2rad(lon - lon0) * R_EARTH * np.cos(np.deg2rad(lat0))
    y = np.deg2rad(lat - lat0) * R_EARTH
    return np.column_stack([x, y])


class Polyline:
    """Reference track with chainage; nearest-vertex matching on a densely sampled polyline."""

    def __init__(self, xy: np.ndarray, chainage: np.ndarray, step: float = 1.0):
        order = np.argsort(chainage)
        xy, chainage = xy[order], chainage[order]
        keep = np.concatenate([[True], np.diff(chainage) >= step])
        # resample to roughly `step` metre vertex spacing
        idx = np.searchsorted(chainage, np.arange(chainage[0], chainage[-1], step))
        idx = np.unique(np.clip(idx, 0, len(chainage) - 1))
        self.xy = xy[idx]
        self.ch = chainage[idx]
        seg = np.diff(self.xy, axis=0)
        self.heading = np.arctan2(seg[:, 1], seg[:, 0])
        self.heading = np.concatenate([self.heading, self.heading[-1:]])
        self.tree = cKDTree(self.xy)

    def match(self, xy: np.ndarray, k: int = 8, heading: np.ndarray | None = None, max_dh: float = np.pi / 3):
        """Return (chainage, lateral_distance) of the nearest vertex; if `heading` is given, candidates
        whose direction differs by more than `max_dh` are rejected (separates opposite carriageways
        and self-crossings)."""
        d, i = self.tree.query(xy, k=k)
        if heading is None:
            return self.ch[i[:, 0]], d[:, 0]
        dh = np.abs(np.angle(np.exp(1j * (self.heading[i] - heading[:, None]))))
        d_pen = np.where(dh <= max_dh, d, np.inf)
        j = np.argmin(d_pen, axis=1)
        rows = np.arange(len(xy))
        dist = d_pen[rows, j]
        return self.ch[i[rows, j]], dist
