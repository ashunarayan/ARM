"""Checks of the corrections made after the final verification audit (review/final_audit/audit.md).

1. rank_scope.csv re-derived from the saved predictions (segment means of pass predictions; not from the summary files)
2. the new ranking macros match rank_scope.csv; no macro of numbers.tex / numbers_v2.tex / numbers_v3.tex changed its
   value relative to the audited checkpoint (checkpoints/v3_2026-10-11), only new macros were added
3. the corrected statements: superseded wording absent, corrected wording present (main paper, supplement, tables)
4. build: both PDFs newer than every input, no undefined reference / overfull box in the logs, no '??' in the PDFs
5. integrity: frozen PROTOCOL_V3.md hash, checkpoint manifests, audit report identical to its checkpoint copy
Output: results/v3/verification_final.json (exit code 1 if any check fails).
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

RR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CP = os.path.join(RR, "checkpoints", "v3_2026-10-11")
ROUTES = ["CPH1", "CPH6", "M3", "M13"]
OUT = []


def check(name, ok, **info):
    OUT.append(dict(check=name, ok=bool(ok), **{k: (v if isinstance(v, (str, int, float, bool, list)) else str(v)) for k, v in info.items()}))
    print(("PASS " if ok else "FAIL ") + name, info if info else "")


def macros(path):
    txt = open(path, encoding="utf-8").read()
    return {m.group(1): m.group(2) for m in re.finditer(r"\\newcommand\{\\([A-Za-z]+)\}\{((?:[^{}]|\{[^{}]*\})*)\}", txt)}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# ---------------------------------------------------------------- 1. ranking scope from saved predictions
U = pd.read_csv(os.path.join(RR, "data", "processed", "lira", "units.csv"))
seg = U.groupby("segment").agg(route=("route", "first"), y=("mri", "first"))
U["stat"] = U.a_rms / np.sqrt(U.v_mean)
P = {"untrained": U.groupby("segment").stat.mean()}
L = pd.read_csv(os.path.join(RR, "results", "predictions", "lira_ladder.csv.gz"))
lad = {"real-trained LightGBM": "M3 LightGBM (all features)", "MLP": "M4 MLP", "1D-CNN": "M5 1D-CNN",
       "M2c vibration index": "M2c RMS/v^alpha (alpha fitted on training data)",
       "LightGBM without speed inputs": "M3 LightGBM (no speed features)",
       "M1 speed only": "M1 speed-only (LightGBM on speed features)"}
for lab, m in lad.items():
    P[lab] = L[L.model == m].groupby("segment").pred.mean()                 # neural nets: mean over the 5 seeds
PI = pd.read_csv(os.path.join(RR, "results", "v2", "physics_inversion_segments.csv"))
P["M7 quarter-car inversion"] = PI[PI.model.str.contains("uncalibrated")].set_index("segment").p
VP = pd.read_csv(os.path.join(RR, "results", "v2", "variants_pass_predictions.csv.gz"))
VP = VP[VP.model == "GBM"]
VP["segment"] = U.segment.to_numpy()[VP.unit.to_numpy()]
for v in [f"V{i}" for i in range(9)]:
    P[f"{v} LightGBM (zero-shot)"] = VP[VP.vid == v].groupby("segment").pred.mean()


def rho(p, r):
    d = seg[seg.route == r].assign(p=p.reindex(seg[seg.route == r].index))
    assert d.p.notna().all()
    return float(np.corrcoef(rankdata(d.p), rankdata(d.y))[0, 1])


RS = pd.read_csv(os.path.join(RR, "results", "v3", "rank_scope.csv")).set_index("estimator")
worst = 0.0
for lab in RS.index:
    for r in ROUTES:
        worst = max(worst, abs((rho(P[lab], r) - rho(P["untrained"], r)) - RS.loc[lab, f"d_{r}"]))
check("rank_scope.csv re-derived from saved predictions", worst < 1e-6, max_abs_diff=float(worst), n_estimators=len(RS))
scope_max = float(RS[RS.scope == 1].max_abs.max())
out_min = float(RS[RS.scope == 0].max_abs.min())
check("every in-scope estimator within 0.05, every out-of-scope estimator beyond it", scope_max <= 0.05 < out_min,
      in_scope_max=round(scope_max, 4), out_of_scope_min=round(out_min, 4))

# ---------------------------------------------------------------- 2. macros
M3new = macros(os.path.join(RR, "paper", "numbers_v3.tex"))
exp = {"rkScopeAbsMax": f"{scope_max:.3f}",
       "rkScopeVarAbsMax": f"{RS.loc[[f'V{i} LightGBM (zero-shot)' for i in range(9)]].max_abs.max():.3f}",
       "rkIdxGapMax": f"{RS.loc['M2c vibration index', 'max_abs']:.2f}",
       "rkNoSpeedGapMax": f"{RS.loc['LightGBM without speed inputs', 'max_abs']:.2f}",
       "rkSpeedOnlyGapMax": f"{RS.loc['M1 speed only', 'max_abs']:.2f}"}
check("new ranking macros match rank_scope.csv", all(M3new.get(k) == v for k, v in exp.items()),
      printed={k: M3new.get(k) for k in exp}, expected=exp)
check("printed bound rpAbsMax covers the in-scope estimators", scope_max <= float(M3new["rpAbsMax"]), rpAbsMax=M3new["rpAbsMax"])
changed, added = [], []
for f in ("numbers.tex", "numbers_v2.tex", "numbers_v3.tex"):
    old, new = macros(os.path.join(CP, "paper", f)), macros(os.path.join(RR, "paper", f))
    changed += [k for k in old if new.get(k) != old[k]]
    added += [k for k in new if k not in old]
check("no existing macro changed its value since the audited checkpoint", not changed, changed=changed, added=added)

# ---------------------------------------------------------------- 3. corrected statements
SRC = [os.path.join(RR, "paper", "main.tex"), os.path.join(RR, "paper", "supplementary.tex")]
SRC += sorted(glob.glob(os.path.join(RR, "paper", "sections", "*.tex"))) + sorted(glob.glob(os.path.join(RR, "tables", "v*.tex")))
TXT = {os.path.relpath(p, RR): " ".join(open(p, encoding="utf-8").read().split()) for p in SRC}
gone = ["every trained estimator", "provided with the paper", "when real training routes are available",
        "over the segments of a road class", "Simulation thus removes", "removes part of the over-correction",
        "over-correct less on urban roads", "all differences are within", "validated them on a probe vehicle against an inertial profilometer"]
hits = {g: [f for f, t in TXT.items() if g in t] for g in gone}
check("superseded wording absent", not any(hits.values()), hits={k: v for k, v in hits.items() if v})
need = {"paper/sections/discussion.tex": ["though not of every estimator", "could not be separated from within-pass speed variability"],
        "paper/sections/method.tex": ["uses the first configuration", "mean of the levels of its two routes", "which use 1\\,km blocks",
                                      "not registered publicly"],
        "paper/sections/intro.tex": ["We will release the code"],
        "paper/sections/results.tex": ["intervals of single elasticities from 1\\,km blocks", "so this advantage is not established"],
        "paper/sections/related.tex": ["according to Bajic et al."],
        "paper/supplementary.tex": ["not yet public", "not registered publicly"],
        "tables/v3_variants.tex": ["averaged over the two routes of a road class"]}
miss = {f: [s for s in ss if s not in TXT[os.path.normpath(f)]] for f, ss in need.items()}
check("corrected wording present", not any(miss.values()), missing={k: v for k, v in miss.items() if v})

# ---------------------------------------------------------------- 4. build
inputs = SRC + glob.glob(os.path.join(RR, "paper", "numbers*.tex")) + [os.path.join(RR, "paper", "references_cited.tex"),
                                                                       os.path.join(RR, "paper", "fig_pipeline.tex")]
inputs += glob.glob(os.path.join(RR, "figures", "*.pdf"))
pdfs = {d: os.path.join(RR, "paper", d + ".pdf") for d in ("main", "supplementary")}
newest = max(os.path.getmtime(p) for p in inputs)
check("PDFs newer than every source, table, macro and figure file", all(os.path.getmtime(p) >= newest for p in pdfs.values()))
from pypdf import PdfReader  # noqa: E402
for d, p in pdfs.items():
    log = open(os.path.join(RR, "paper", d + ".log"), encoding="latin-1").read()
    bad = [w for w in ("undefined", "Overfull", "Missing character", "multiply defined") if w in log]
    R = PdfReader(p)
    text = "".join(pg.extract_text() or "" for pg in R.pages)
    check(f"{d}.pdf: clean log and no '??'", not bad and "??" not in text, pages=len(R.pages), log_problems=bad)

# ---------------------------------------------------------------- 5. integrity
check("PROTOCOL_V3.md unchanged (frozen hash)",
      sha(os.path.join(RR, "evaluation", "PROTOCOL_V3.md")) == "994cd02729a8bf3b4ec3040bedc2b83bc7647227772b56f87eca7831a415ccc6")
check("audit report unchanged", sha(os.path.join(RR, "review", "final_audit", "audit.md")) == sha(os.path.join(CP, "review", "final_audit", "audit.md")))
for cp in ("v2_2026-10-03", "v3_2026-10-11"):
    base = os.path.join(RR, "checkpoints", cp)
    bad = []
    for line in open(os.path.join(base, "MANIFEST.sha256"), encoding="utf-8"):
        h, f = line.split(maxsplit=1)
        if sha(os.path.join(base, f.strip().lstrip("*"))) != h:
            bad.append(f.strip())
    check(f"checkpoint {cp} matches its manifest", not bad, mismatches=bad[:5])

json.dump(OUT, open(os.path.join(RR, "results", "v3", "verification_final.json"), "w"), indent=1)
n_fail = sum(not c["ok"] for c in OUT)
print(f"{len(OUT)} checks, {n_fail} failed")
sys.exit(1 if n_fail else 0)
