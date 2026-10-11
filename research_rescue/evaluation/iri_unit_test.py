"""Phase 4 - validation of the IRI implementation against an independent profilometer.

Reference: LiRA-CD P79 profilometer (Danish Road Directorate). The P79 software reports IRI per 10 m
for the left (laser 5) and right (laser 21) wheel paths; LiRA-CD also publishes the underlying laser
elevation profiles at 0.1 m (with GPS). We recompute IRI from those profiles and compare.

Variants evaluated (all on the same profiles):
  canonical_dx0.10    ASTM E1926-style algorithm (common/iri.py) at the native 0.1 m spacing
                      (250 mm base -> nint(2.5) = 3 samples = 0.30 m)
  canonical_dx0.125   resampled to 0.125 m so the slope base is exactly 0.25 m (2 samples)
  canonical_dx0.25    resampled to 0.25 m (base = 1 sample), as the legacy BeamNG pipeline used
  canonical_nosmooth  0.1 m, no 250 mm smoothing (sensitivity)
  legacy_compute_iri  the rejected paper's ml_model/iri_compliant/iri_calculation.compute_iri on
                      0.25 m profiles, 100 m segments with 20 m lead-in (exactly as for BeamNG labels)
  legacy_mesh_corrected  legacy pipeline including correct_mesh_tessellation(), applied to REAL roads
                      (which contain no simulator mesh facets) -> isolates what the correction removes

A-priori consistency rule: a (profile, reported-IRI) file pair is "consistent" if the 10 m agreement
of this implementation with the reported IRI has Pearson r >= 0.95 on both wheel paths. Pairs failing
the rule cannot be aligned (no distance shift or direction reversal aligns them, see logs) and are
reported separately, never silently dropped.

Second, independent device: ARAN9000 IRI (different survey date) mapped to P79 chainage by GPS,
which gives the inter-device agreement that bounds any label's reproducibility.

Outputs: tables/iri_reference_validation{,_by_route}.{csv,md,tex}, figures/iri_reference_validation.{pdf,png},
results/iri_validation.json, data/processed/lira/p79_segments_100m.csv (used by later phases).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import iri, lira, geo, plotting  # noqa: E402
from common.paths import FIGURES, TABLES, RESULTS, PROCESSED, LEGACY_LABEL_CODE, LIRA_ROUTES, LIRA_DIRS  # noqa: E402

sys.path.insert(0, LEGACY_LABEL_CODE)
import iri_calculation as legacy  # noqa: E402

SEG = 100.0
CONSISTENCY_R = 0.95


def resample_runs(zp: pd.DataFrame, dx: float):
    """Yield (grid, z_left, z_right, lat, lon) for each gap-free run on a uniform grid."""
    for s, e in lira.zp_runs(zp):
        seg = zp.iloc[s:e]
        grid = np.arange(seg.dist.iloc[0], seg.dist.iloc[-1], dx)
        out = [grid]
        for c in ["z_left", "z_right", "lat", "lon"]:
            v = seg[c].interpolate().bfill().ffill().to_numpy()
            out.append(np.interp(grid, seg.dist.to_numpy(), v))
        yield out


def canonical_bins(zp, starts, length, dx, smooth=True):
    out = {}
    for side in ["left", "right"]:
        rs_l, pos_l = [], []
        for grid, zl, zr, _, _ in resample_runs(zp, dx):
            z = zl if side == "left" else zr
            rs, pos = iri.continuous_rectified_slope(z, dx, base=0.25 if smooth else 1e-9)
            rs_l.append(rs); pos_l.append(pos + grid[0])
        rs = np.concatenate(rs_l); pos = np.concatenate(pos_l)
        o = np.argsort(pos)
        w = iri.window_iri(rs[o], pos[o], starts, length)
        n_exp = length / dx      # exclude windows straddling a gap (< 90 % of expected samples)
        cnt = np.searchsorted(pos[o], starts + length) - np.searchsorted(pos[o], starts)
        w[cnt < 0.9 * n_exp] = np.nan
        out[side] = w
    return out


def legacy_bins(zp, starts, mesh_correction: bool):
    out = {"left": np.full(len(starts), np.nan), "right": np.full(len(starts), np.nan)}
    lead = int(20.0 / 0.25)
    for grid, zl, zr, _, _ in resample_runs(zp, 0.25):
        for side, z in [("left", zl), ("right", zr)]:
            if mesh_correction:
                z = legacy.correct_mesh_tessellation(z, 0.25)
            z = legacy.apply_250mm_moving_average(z, 0.25)
            for j, st in enumerate(starts):
                i0 = int(round((st - grid[0]) / 0.25)); i1 = i0 + int(SEG / 0.25)
                if i0 - lead < 0 or i1 > len(z):
                    continue
                out[side][j] = legacy.compute_iri(z[i0 - lead:i1], 0.25, lead_in_samples=lead)[0]
    return out


def agreement(a: np.ndarray, b: np.ndarray) -> dict:
    """a = candidate, b = reference."""
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    d = a - b
    return dict(n=int(ok.sum()), pearson=float(np.corrcoef(a, b)[0, 1]), spearman=float(spearmanr(a, b)[0]),
                bias=float(d.mean()), mae=float(np.abs(d).mean()),
                mape=float(100 * np.mean(np.abs(d) / b)), median_ape=float(100 * np.median(np.abs(d) / b)),
                loa_low=float(d.mean() - 1.96 * d.std()), loa_high=float(d.mean() + 1.96 * d.std()),
                ref_mean=float(b.mean()))


def road_class(route: str) -> str:
    return "urban" if route.startswith("CPH") else "motorway"


def main():
    rows, seg_tables, per_file = [], [], []
    for route in LIRA_ROUTES:
        for direction in LIRA_DIRS:
            try:
                zp = lira.load_zp(route, direction); ref = lira.load_p79_iri(route, direction)
            except FileNotFoundError as e:
                print("missing", e); continue
            tag = f"{route}_{direction}"
            st10 = ref.dist.to_numpy()
            c10 = canonical_bins(zp, st10, 10.0, 0.1)
            r10 = []
            for side in ["left", "right"]:
                a = agreement(c10[side], ref[f"iri_{side}"].to_numpy())
                r10.append(a["pearson"])
                rows.append(dict(route=route, direction=direction, resolution_m=10, variant="canonical_dx0.10",
                                 reference="P79_reported", side=side, **a))
            consistent = bool(min(r10) >= CONSISTENCY_R)
            # 100 m segments on the zp chainage grid (the profile carries GPS -> later car map matching)
            d0 = np.ceil(zp.dist.min() / 10) * 10
            starts = np.arange(d0, zp.dist.max() - SEG, SEG)
            ref100 = {}
            for side in ["left", "right"]:
                s_ = pd.Series(ref[f"iri_{side}"].to_numpy(), index=st10)
                vals = []
                for st in starts:
                    w = s_[(s_.index >= st) & (s_.index < st + SEG)]
                    vals.append(w.mean() if len(w) == 10 else np.nan)
                ref100[side] = np.array(vals)
            ref100["mri"] = 0.5 * (ref100["left"] + ref100["right"])
            variants = {
                "canonical_dx0.10": canonical_bins(zp, starts, SEG, 0.1),
                "canonical_dx0.125": canonical_bins(zp, starts, SEG, 0.125),
                "canonical_dx0.25": canonical_bins(zp, starts, SEG, 0.25),
                "canonical_nosmooth": canonical_bins(zp, starts, SEG, 0.1, smooth=False),
                "legacy_compute_iri": legacy_bins(zp, starts, mesh_correction=False),
                "legacy_mesh_corrected": legacy_bins(zp, starts, mesh_correction=True),
            }
            for v in variants.values():
                v["mri"] = 0.5 * (v["left"] + v["right"])
            prof_mri = variants["canonical_dx0.10"]["mri"]
            for vname, v in variants.items():
                for side in ["left", "right", "mri"]:
                    rows.append(dict(route=route, direction=direction, resolution_m=100, variant=vname,
                                     reference="P79_reported", side=side, **agreement(v[side], ref100[side])))
            rec = dict(route=route, direction=direction, consistent=consistent, ref=ref100["mri"], prof=prof_mri,
                       **{f"v_{k}": v["mri"] for k, v in variants.items()})
            ar_mri = np.full(len(starts), np.nan)
            grid_pos = zp.dist.to_numpy()
            try:
                ar = lira.load_aran(route, direction)
                lat0, lon0 = zp.lat.median(), zp.lon.median()
                pl = geo.Polyline(geo.to_local_xy(zp.lat.to_numpy(), zp.lon.to_numpy(), lat0, lon0)[::10], grid_pos[::10])
                ch, dist = pl.match(geo.to_local_xy(ar.lat.to_numpy(), ar.lon.to_numpy(), lat0, lon0))
                ar = ar.assign(ch=ch, gdist=dist)
                ar = ar[ar.gdist < 10]
                for j, st in enumerate(starts):
                    w = ar[(ar.ch >= st) & (ar.ch < st + SEG)]
                    if len(w) >= 5:
                        ar_mri[j] = 0.5 * (w.iri_left.mean() + w.iri_right.mean())
                rows.append(dict(route=route, direction=direction, resolution_m=100, variant="ARAN9000",
                                 reference="P79_profile", side="mri", **agreement(ar_mri, prof_mri)))
            except Exception as ex:  # ARAN is secondary; record and continue
                print("ARAN failed", tag, ex)
            rec["aran"] = ar_mri
            per_file.append(rec)
            seg_tables.append(pd.DataFrame(dict(
                route=route, direction=direction, start_m=starts, consistent_reported=consistent,
                mri_reported=ref100["mri"], mri_profile=prof_mri, mri_aran=ar_mri,
                lat=np.interp(starts + SEG / 2, grid_pos, zp.lat.interpolate().bfill().ffill()),
                lon=np.interp(starts + SEG / 2, grid_pos, zp.lon.interpolate().bfill().ffill()))))
            print("done", tag, "consistent" if consistent else "INCONSISTENT (profile vs reported IRI)", flush=True)

    R = pd.DataFrame(rows)
    os.makedirs(os.path.join(PROCESSED, "lira"), exist_ok=True)
    pd.concat(seg_tables).to_csv(os.path.join(PROCESSED, "lira", "p79_segments_100m.csv"), index=False)
    R.to_csv(os.path.join(TABLES, "iri_reference_validation_by_route.csv"), index=False)

    pooled = []

    def pool(name, x_key, y_key, files, scope):
        X = np.concatenate([f[x_key] for f in files]); Y = np.concatenate([f[y_key] for f in files])
        pooled.append(dict(comparison=name, scope=scope, files=len(files), **agreement(Y, X)))

    cons = [f for f in per_file if f["consistent"]]
    for vk, vname in [("v_canonical_dx0.10", "This implementation (0.1 m)"),
                      ("v_canonical_dx0.125", "This implementation (0.125 m)"),
                      ("v_canonical_dx0.25", "This implementation (0.25 m)"),
                      ("v_canonical_nosmooth", "This implementation, no 250 mm filter"),
                      ("v_legacy_compute_iri", "Legacy compute_iri (no correction)"),
                      ("v_legacy_mesh_corrected", "Legacy pipeline incl. mesh correction")]:
        pool(f"{vname} vs P79-reported", "ref", vk, cons, "consistent files")
        for rc in ["urban", "motorway"]:
            pool(f"{vname} vs P79-reported", "ref", vk, [f for f in cons if road_class(f["route"]) == rc], rc)
    pool("This implementation (0.1 m) vs P79-reported", "ref", "v_canonical_dx0.10", per_file, "all files")
    pool("Legacy mesh-corrected vs this implementation", "prof", "v_legacy_mesh_corrected", per_file, "all files")
    for rc in ["urban", "motorway"]:
        pool("Legacy mesh-corrected vs this implementation", "prof", "v_legacy_mesh_corrected",
             [f for f in per_file if road_class(f["route"]) == rc], rc)
    pool("ARAN9000 vs P79 (profile)", "prof", "aran", per_file, "all files")
    for rc in ["urban", "motorway"]:
        pool("ARAN9000 vs P79 (profile)", "prof", "aran", [f for f in per_file if road_class(f["route"]) == rc], rc)
    P = pd.DataFrame(pooled)
    P.to_csv(os.path.join(TABLES, "iri_reference_validation.csv"), index=False)
    cols = ["comparison", "scope", "files", "n", "pearson", "bias", "mae", "mape", "loa_low", "loa_high"]
    with open(os.path.join(TABLES, "iri_reference_validation.md"), "w") as f:
        f.write(plotting.md_table(P[cols].round(3)))
    plotting.latex_table(P[cols].round(3), os.path.join(TABLES, "iri_reference_validation.tex"),
                         caption="Agreement of recomputed IRI with the P79 profilometer's reported IRI "
                                 "(100 m, mean of both wheel paths; LiRA-CD).",
                         label="tab:iri_validation")
    json.dump(dict(consistency_rule=f"10 m Pearson r >= {CONSISTENCY_R} on both wheel paths",
                   files=[dict(route=f["route"], direction=f["direction"], consistent=f["consistent"]) for f in per_file],
                   pooled=P.to_dict(orient="records"), self_test=iri.self_test()),
              open(os.path.join(RESULTS, "iri_validation.json"), "w"), indent=1)
    scatter = {"canonical_dx0.10": [np.column_stack([f["ref"], f["v_canonical_dx0.10"]]) for f in cons],
               "legacy_mesh_corrected": [np.column_stack([f["ref"], f["v_legacy_mesh_corrected"]]) for f in cons],
               "ARAN_vs_P79": [np.column_stack([f["prof"], f["aran"]]) for f in per_file]}
    plotting.iri_validation_figure(scatter, os.path.join(FIGURES, "iri_reference_validation"))
    print(P[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
