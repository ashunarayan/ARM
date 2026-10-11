"""Revision v3: independent verification of the v3 artifacts (results/v3/verification_v3.json).

Re-derives the headline numbers from the raw result files with code independent of make_numbers_v3.py, cross-checks
two different computations of the same quantity, checks the paper sources and PDFs, and checks the integrity of the
frozen protocol and of the v2 checkpoint. Every check is reported, passed or not; the script exits non-zero if any fails.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R2, R3, PAPER = (os.path.join(HERE, "results", "v2"), os.path.join(HERE, "results", "v3"), os.path.join(HERE, "paper"))
MEAS = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
SENS = [v for v in MEAS if v != "V4"]
CHECKS = []


def check(name, passed, **details):
    CHECKS.append(dict(check=name, passed=bool(passed), **{k: (v if isinstance(v, (str, int, float, bool, list, dict))
                                                               or v is None else str(v)) for k, v in details.items()}))
    print(("PASS " if passed else "FAIL ") + name + ("  " + json.dumps(details, default=str)[:300] if details else ""))


def macros():
    pat = re.compile(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}")
    out = {}
    for f in ("numbers.tex", "numbers_v2.tex", "numbers_v3.tex"):
        for k, v in pat.findall(open(os.path.join(PAPER, f), encoding="utf-8").read()):
            out.setdefault(k, []).append((f, v.replace("\\ensuremath{-}", "-").replace("\\ensuremath{+}", "+")))
    return out


def num(s):
    return float(s.replace("\\ensuremath{-}", "-").replace("\\ensuremath{+}", "+").replace(",", ""))


def pooled_mae(D, keys):
    D = D.assign(w=D.seg_mae * D.n_seg)
    a = D.groupby(keys + ["draw"]).agg(w=("w", "sum"), n=("n_seg", "sum")).reset_index()
    a["mae"] = a.w / a.n
    return a


def main():
    MAC = macros()
    M = {k: v[0][1] for k, v in MAC.items()}

    # ---- 1. macro files: unique names, no unresolved values
    dup = [k for k, v in MAC.items() if len(v) > 1]
    check("macro names unique across numbers.tex, numbers_v2.tex, numbers_v3.tex", not dup, duplicates=dup[:10])
    unresolved = [k for k, v in M.items() if "??" in v]
    check("no unresolved ('??') macro values", not unresolved, unresolved=unresolved[:10])

    # ---- 2. every macro used in the paper sources is defined
    srcs = [os.path.join(PAPER, f) for f in ("main.tex", "supplementary.tex", "fig_pipeline.tex")]
    srcs += [os.path.join(PAPER, "sections", f) for f in os.listdir(os.path.join(PAPER, "sections")) if f.endswith(".tex")]
    tex = "\n".join(open(p, encoding="utf-8").read() for p in srcs)
    for t in re.findall(r"\\input\{\.\./tables/([A-Za-z0-9_]+)\.tex\}", tex):
        tex += "\n" + open(os.path.join(HERE, "tables", t + ".tex"), encoding="utf-8").read()
    used = set(re.findall(r"\\([A-Za-z]+)", tex))
    prefixes = ("po", "cu", "bl", "ba", "ld", "rp", "sr", "ns", "pd", "re", "mt", "kd", "vp", "vr", "vv", "pc", "vb",
                "el", "ep", "ss", "sp", "bg", "inv", "ud", "bj", "rk", "lira", "acf", "inf", "ar", "vs", "rbv")
    cand = {u for u in used if u.startswith(prefixes) and any(c.isupper() for c in u[1:])}
    undefined = sorted(u for u in cand if u not in M)
    check("every number macro used in the paper and tables is defined", not undefined, undefined=undefined[:20])

    # ---- 3. compiled PDFs: page counts, no '??', no undefined references in the logs
    try:
        from pypdf import PdfReader
        for f in ("main", "supplementary"):
            r = PdfReader(os.path.join(PAPER, f + ".pdf"))
            text = "".join(p.extract_text() for p in r.pages)
            log = open(os.path.join(PAPER, f + ".log"), encoding="latin-1").read()
            check(f"{f}.pdf has no '??' and its log no undefined references or overfull boxes",
                  "??" not in text and "undefined" not in log and "Overfull" not in log, pages=len(r.pages))
            # ranges are typeset with an en dash; hyphens (dates such as 2026-10-10) are not ranges
            check(f"{f}.pdf has no equal-ended ranges such as '20-20' (en dash)",
                  re.search(r"\b(\d+)–\1\b(?!\.\d)", text) is None)
    except ImportError:
        check("pypdf available for the PDF checks", False)

    # ---- 4. joint-training arm re-derived from the raw rows (V3-1)
    P = pd.read_csv(os.path.join(R3, "pooled_vs_real.csv"))
    check("pooled_vs_real.csv has 10 variants x 4 folds x 5 k x 20 draws", len(P) == 4000
          and P.groupby(["vid", "fold", "k_km", "draw"]).size().max() == 1, rows=len(P))
    R4 = pd.read_csv(os.path.join(R2, "value_of_simulation.csv")); R4 = R4[R4.arm == "real_only"]
    pm = pooled_mae(P, ["vid", "k_km"]); rm = pooled_mae(R4, ["k_km"]).rename(columns={"mae": "real"})
    J = pm.merge(rm[["k_km", "draw", "real"]], on=["k_km", "draw"])
    J["d"] = J.mae - J.real
    S = J.groupby(["vid", "k_km"]).agg(mae=("mae", "mean"), d=("d", "mean"), w=("d", lambda x: int((x < 0).sum())))
    g5 = S.loc[MEAS].xs(5, level="k_km")
    check("joint 5 km pooled MAE range over V0-V8 equals the printed macros",
          f"{g5.mae.min():.2f}" == M["poMaeFiveMin"] and f"{g5.mae.max():.2f}" == M["poMaeFiveMax"],
          recomputed=[round(g5.mae.min(), 4), round(g5.mae.max(), 4)], printed=[M["poMaeFiveMin"], M["poMaeFiveMax"]])
    g20 = S.loc[MEAS].xs(20, level="k_km")
    check("joint 20 km difference to real-only equals the printed macros",
          f"{g20.d.min():+.2f}" == M["poDiffTwentyMin"] and f"{g20.d.max():+.2f}" == M["poDiffTwentyMax"],
          recomputed=[round(g20.d.min(), 4), round(g20.d.max(), 4)])
    h1 = all((S.loc[(v, k), "d"] < 0) for v in MEAS + ["V10"] for k in (1, 2, 5, 10)) and \
        all(S.loc[(v, 20), "d"] <= 0.02 for v in MEAS + ["V10"])
    check("pre-registered H1 (joint better on average for every variant at k<=10, within 0.02 at 20 km) re-derived",
          h1 == (M["poHoneAll"] == "holds"), h1=h1, printed=M["poHoneAll"])
    c4 = {("V0", 5): 0.452, ("V0", 10): 0.453, ("V0", 20): 0.435, ("V1", 5): 0.467, ("V1", 10): 0.467,
          ("V1", 20): 0.443, ("V3", 5): 0.473, ("V3", 10): 0.476, ("V3", 20): 0.447, ("V5", 5): 0.466,
          ("V5", 10): 0.469, ("V5", 20): 0.442}
    worst = max(abs(S.loc[key, "mae"] - v) for key, v in c4.items())
    check("joint arm reproduces review check c4 within the protocol tolerance (0.002 m/km + rounding)", worst <= 0.0025,
          max_abs_diff=round(worst, 5))
    rv = os.path.join(HERE, "review", "v3_checks", "outputs")
    rows_c4 = [f for f in os.listdir(rv) if f.startswith("c4") and f.endswith(".csv")] if os.path.isdir(rv) else []
    if rows_c4:
        C4 = pd.concat([pd.read_csv(os.path.join(rv, f)) for f in rows_c4], ignore_index=True)
        cols = [c for c in ("vid", "fold", "k_km", "draw", "seg_mae") if c in C4.columns]
        if set(cols) == {"vid", "fold", "k_km", "draw", "seg_mae"}:
            m = C4[cols].merge(P[cols], on=["vid", "fold", "k_km", "draw"], suffixes=("_rev", "_v3"))
            check("joint arm identical to the reviewer's per-fold-draw values", len(m) > 0 and
                  float((m.seg_mae_rev - m.seg_mae_v3).abs().max()) < 1e-9, rows=len(m))

    # ---- 5. two computations of the same difference agree (V3-2 vs per-draw pooled MAE)
    U = pd.read_csv(os.path.join(R3, "calib_uncertainty.csv"))
    PS = pd.read_csv(os.path.join(R3, "pooled_summary.csv")).set_index(["vid", "k_km"])
    dev = []
    for _, r in U.iterrows():
        ref = PS.loc[(r.vid, r.k_km), "d_real" if r.arm == "sim_real_pooled" else "d_real_cal"]
        dev.append(abs(r["diff"] - ref))
    check("test-route interval centres equal the mean per-draw pooled differences (segment-level vs pooled computation)",
          max(dev) < 1e-9, max_abs_dev=float(max(dev)))
    check("every 5 km interval excludes zero, joint 20 km intervals all below zero, level offset 20 km above zero for V1, V3, V5",
          bool((U[U.k_km == 5].hi < 0).all() and (U[(U.k_km == 20) & (U.arm == "sim_real_pooled")].hi < 0).all()
               and set(U[(U.k_km == 20) & (U.arm == "sim_all_cal") & (U.lo > 0)].vid) == {"V1", "V3", "V5"}))

    # ---- 6. band-limited retraining (V3-3): spreads, H3, H3b, reproduction of the zero-shot MAEs
    BL = pd.read_csv(os.path.join(R3, "band_limited.csv"))

    def spread(s, c):
        g = BL[(BL.features == s) & BL.vid.isin(SENS)][c]
        return g.max() - g.min()
    ratios = {c: spread("lt10", c) / spread("full", c) for c in ("lvl_mean", "lvl_urban", "lvl_motorway")}
    nochg = max(abs(spread("no1015", c) / spread("full", c) - 1) for c in ("lvl_mean", "lvl_urban", "lvl_motorway", "bias"))
    v4 = BL[(BL.features == "lt10") & (BL.vid == "V4")].lvl_mean.iloc[0]
    g8 = BL[(BL.features == "lt10") & BL.vid.isin(SENS)].lvl_mean
    check("H3: below-10 Hz spread <= 50 % of full for mean, urban and motorway level; dropping 10-15 Hz changes < 20 %",
          all(v <= 0.5 for v in ratios.values()) and nochg < 0.2,
          ratios={k: round(v, 3) for k, v in ratios.items()}, no1015_max_change=round(nochg, 4))
    check("H3b: V4 outside the range of the eight sensor variants under lt10", not (g8.min() <= v4 <= g8.max()),
          v4=round(v4, 3), range=[round(g8.min(), 3), round(g8.max(), 3)])
    check("printed band-limited ratio of the mean level matches", f"{100 * ratios['lvl_mean']:.0f}" == M["blRatioLvl"],
          recomputed=round(100 * ratios["lvl_mean"], 2), printed=M["blRatioLvl"])
    SV = pd.read_csv(os.path.join(R2, "summary_variants.csv")); SV = SV[SV.model == "GBM"].set_index("vid")
    full = BL[BL.features == "full"].set_index("vid")
    check("full-feature retraining reproduces the v2 zero-shot MAEs to three decimals",
          float((full.loc[MEAS, "mae"] - SV.loc[MEAS, "mae"]).abs().max()) < 5e-4)

    # ---- 7. pass density (V3-10)
    PD = pd.read_csv(os.path.join(R3, "pass_density.csv"))
    check("pass_density.csv complete (real-only 3x4x20 rows; 2 arms x 9 variants x 3 x 4 x 20)",
          len(PD) == 240 + 2 * 9 * 240, rows=len(PD))
    a = pooled_mae(PD.assign(vid=PD.vid.fillna("-")), ["arm", "vid", "m"])
    real1 = a[(a.arm == "real_only") & (a.m == 1)][["draw", "mae"]].rename(columns={"mae": "real"})
    b = a[(a.m == 1) & (a.arm != "real_only")].merge(real1, on="draw")
    check("with one pass per segment both simulation arms beat real-only LightGBM in every draw for every variant",
          bool((b.mae < b.real).all()), worst_margin=round(float((b.mae - b.real).max()), 4))

    # ---- 8. ranking claim: every per-route difference within the printed bound
    RP = pd.read_csv(os.path.join(R3, "rank_paired.csv"))
    rr = RP[(RP.metric == "rho") & RP["diff"].notna() & (RP.route != "mean")]
    check("every per-route rho difference to RMS/v^0.5 within the printed bound", float(rr["diff"].abs().max()) <= num(M["rpAbsMax"]),
          max_abs=round(float(rr["diff"].abs().max()), 4), bound=M["rpAbsMax"])

    # ---- 9. M7 fix (V3-8)
    PI = pd.read_csv(os.path.join(R2, "physics_inversion.csv"))
    m7 = PI[(PI.fold == "M13") & PI.model.str.startswith("M7 quarter")].iloc[0]
    check("M7 now evaluated on all 228 M13 segments", int(m7.n_seg) == 228, n_seg=int(m7.n_seg))

    # ---- 10. frozen protocol and checkpoint integrity
    h = hashlib.sha256(open(os.path.join(HERE, "evaluation", "PROTOCOL_V3.md"), "rb").read()).hexdigest()
    check("PROTOCOL_V3.md unchanged since freezing", h == "994cd02729a8bf3b4ec3040bedc2b83bc7647227772b56f87eca7831a415ccc6",
          sha256=h)
    ck = os.path.join(HERE, "checkpoints", "v2_2026-10-03")
    bad, n = [], 0
    for line in open(os.path.join(ck, "MANIFEST.sha256"), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        digest, rel = line.split(None, 1)
        rel = rel.lstrip("*")
        n += 1
        p = os.path.join(ck, rel)
        if not os.path.exists(p) or hashlib.sha256(open(p, "rb").read()).hexdigest() != digest:
            bad.append(rel)
    check("v2 checkpoint matches its manifest", not bad, files=n, mismatched=bad[:10])

    out = dict(n_checks=len(CHECKS), n_failed=sum(not c["passed"] for c in CHECKS), checks=CHECKS)
    json.dump(out, open(os.path.join(R3, "verification_v3.json"), "w", encoding="utf-8"), indent=1, default=str)
    print(f"{out['n_checks']} checks, {out['n_failed']} failed -> results/v3/verification_v3.json")
    sys.exit(1 if out["n_failed"] else 0)


if __name__ == "__main__":
    main()
