"""Readers for the LiRA-CD dataset (Skar et al., Data in Brief 2023; CC BY 4.0).

Reference subset: P79 profilometer longitudinal elevation per laser at 0.1 m ('*_zp_*.csv', mm),
P79 IRI per 10 m for the left (laser 5) and right (laser 21) wheel paths ('*_iri_mpd_rut_*.csv'),
ARAN9000 condition data ('*_aran_*.csv'). Files are ';'-separated, Latin-1 encoded.
Car subset: AutoPi + CAN data in HDF5 (route / device / task / pass / signal).
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

from .paths import LIRA_REF, LIRA_CAR


def _read(path: str, usecols=None) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="latin-1", usecols=usecols, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df


def load_zp(route: str, direction: str) -> pd.DataFrame:
    p = os.path.join(LIRA_REF, f"{route.lower()}_zp_{direction.lower()}.csv")
    df = _read(p)
    out = pd.DataFrame({
        "dist": pd.to_numeric(df["Distance [m]"], errors="coerce"),
        "z_left": pd.to_numeric(df["Laser 5 [mm]"], errors="coerce") / 1000.0,
        "z_right": pd.to_numeric(df["Laser 21 [mm]"], errors="coerce") / 1000.0,
        "lat": pd.to_numeric(df["Lat"], errors="coerce"),
        "lon": pd.to_numeric(df["Lon"], errors="coerce"),
    })
    return out.dropna(subset=["dist"]).sort_values("dist").reset_index(drop=True)


def load_p79_iri(route: str, direction: str) -> pd.DataFrame:
    p = os.path.join(LIRA_REF, f"{route.lower()}_iri_mpd_rut_{direction.lower()}.csv")
    df = _read(p)
    cols = list(df.columns)
    return pd.DataFrame({
        "dist": pd.to_numeric(df[cols[0]], errors="coerce"),
        "iri_left": pd.to_numeric(df[cols[1]], errors="coerce"),
        "iri_right": pd.to_numeric(df[cols[2]], errors="coerce"),
    }).dropna().sort_values("dist").reset_index(drop=True)


def load_aran(route: str, direction: str) -> pd.DataFrame:
    p = os.path.join(LIRA_REF, f"{route.lower()}_aran_{direction.lower()}.csv")
    df = _read(p)
    iri_cols = [c for c in df.columns if "IRI" in c]          # [left (Venstre), right (Højre)]
    return pd.DataFrame({
        "begin": pd.to_numeric(df["BeginChainage"], errors="coerce"),
        "end": pd.to_numeric(df["EndChainage"], errors="coerce"),
        "iri_left": pd.to_numeric(df[iri_cols[0]], errors="coerce"),
        "iri_right": pd.to_numeric(df[iri_cols[1]], errors="coerce"),
        "lat": pd.to_numeric(df["Lat"], errors="coerce"),
        "lon": pd.to_numeric(df["Lon"], errors="coerce"),
    }).dropna()


def zp_runs(zp: pd.DataFrame, max_gap: float = 0.5, min_len: float = 200.0):
    """Split a zp profile into gap-free runs; returns list of (start_idx, end_idx_exclusive)."""
    d = zp["dist"].to_numpy()
    brk = np.where(np.diff(d) > max_gap)[0]
    starts = np.concatenate([[0], brk + 1]); ends = np.concatenate([brk + 1, [len(d)]])
    return [(s, e) for s, e in zip(starts, ends) if d[e - 1] - d[s] >= min_len]


def car_file(route: str, direction: str) -> str:
    return os.path.join(LIRA_CAR, f"{route}_{direction}.hdf5")
