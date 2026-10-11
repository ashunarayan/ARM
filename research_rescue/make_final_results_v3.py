"""Revision v3: headline results with provenance (results/v3/final_results_v3.json and .csv).

Every new or changed headline number of the v3 paper is listed with the LaTeX macros that print it, the result file
it comes from, the script that wrote that file, the protocol item (evaluation/PROTOCOL_V3.md) and the evidence class.
Values are read from results/v3/paper_numbers_v3.json (and results/v2/paper_numbers_v2.json for re-used v2 macros),
which make_numbers_v3.py / make_numbers_v2.py generate from the result files, so this table cannot drift from the
paper. Run after make_numbers_v3.py.
"""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
V2, V3 = os.path.join(HERE, "results", "v2"), os.path.join(HERE, "results", "v3")

# (id, quantity, macros, source file(s), script, protocol item, evidence class, paper location)
HEADLINES = [
    ("T1", "k km of paired drives: passes per segment, segment-passes at 5 km (mean, range), km driven",
     ["kdPassesFive", "kdUnitsFive", "kdUnitsFiveMin", "kdUnitsFiveMax", "kdKmFive", "kdDriveKmFive"],
     "results/v2/value_of_simulation.csv", "experiments/v2/value_of_simulation.py", "metric definition", "-",
     "Sec. IV, Sec. V-D"),
    ("T2", "Joint training (sim + real, equal total weight) with 5 km: pooled MAE range over V0-V8, draws better than real-only",
     ["poMaeFiveMin", "poMaeFiveMax", "poWinsFiveRange", "vbRealOnlyFive"],
     "results/v3/pooled_vs_real.csv; results/v2/value_of_simulation.csv", "experiments/v3/pooled_vs_real.py",
     "V3-1", "R", "abstract, Sec. V-D, Table II, Table III, Fig. 2c, Fig. 4b"),
    ("T3", "Joint training with 20 km: difference to real-only (range over V0-V8), draws better; pre-registered H1",
     ["poDiffTwentyMin", "poDiffTwentyMax", "poWinsTwentyRange", "poHoneMeas", "poHoneAll", "poBeatAllK"],
     "results/v3/pooled_summary.csv", "make_numbers_v3.py (from pooled_vs_real.csv)", "V3-1", "R",
     "abstract, Sec. V-D, Supplement S1"),
    ("T4", "Level offset with 5 km (v2 result, re-used): pooled MAE range over V0-V8, draws better than real-only",
     ["pcCalMaeFiveMin", "pcCalMaeFiveMax", "pcCalWinsFiveMin", "pcCalWinsFiveMax"],
     "results/v2/paired_vs_real.csv", "experiments/v2/paired_vs_real.py", "v2 R3/E6", "R/E", "abstract, Sec. V-D"),
    ("T5", "Test-route 5 km-block intervals of the difference to real-only (level offset, joint training; 5 and 20 km)",
     ["cuCalFiveDiffMin", "cuCalFiveDiffMax", "cuPoolFiveDiffMin", "cuPoolFiveDiffMax", "cuCalFiveExclNeg",
      "cuPoolFiveExclNeg", "cuCalTwentyExclPos", "cuPoolTwentyExclNeg", "cuCalVoneTwenty", "cuCalVfiveTwenty"],
     "results/v3/calib_uncertainty.csv", "experiments/v3/calib_uncertainty.py", "V3-2", "E", "Sec. V-D, Table S18"),
    ("T6", "Variant dependence: spread of pooled MAE over V0-V8, joint training vs level offset (5 and 20 km); 1 km range",
     ["poMaeSpreadFive", "poCalSpreadFive", "poMaeSpreadTwenty", "poCalSpreadTwenty", "poMaeOneMin", "poMaeOneMax"],
     "results/v3/pooled_summary.csv", "make_numbers_v3.py", "V3-1", "R", "Sec. V-D"),
    ("T7", "Per held-out route at 20 km: variant-route cells where joint training beats real-only",
     ["poRouteTwentyNeg", "poRouteTwentyCells", "poRouteTwentyPos", "poRouteTwentyMwThreePos",
      "poRouteTwentyCphSixPos", "poRouteTwentyDiffMax"],
     "results/v3/pooled_by_route.csv", "make_numbers_v3.py", "V3-1", "R", "Sec. V-D"),
    ("T8", "Which combination: joint minus level offset at 5 km by group; class-level difference and its correlation with the MAE after an offset",
     ["poHiDefDiffCalFiveMin", "poHiDefDiffCalFiveMax", "poLoDefDiffCalFiveMin", "poLoDefDiffCalFiveMax",
      "ldSpreadMin", "ldSpreadMax", "ldSpreadCalRho", "ldHiDefSpreadMin", "ldHiDefSpreadMax"],
     "results/v3/pooled_summary.csv; results/v3/level_decomposition.csv", "make_numbers_v3.py; experiments/v3/level_and_bands.py",
     "V3-1, V3-5", "R", "Sec. V-D, Discussion"),
    ("T9", "Affine map worse than the better of offset and joint training (number of variants of 9, 5 and 20 km)",
     ["poAffWorseFive", "poAffWorseTwenty"], "results/v3/pooled_summary.csv", "make_numbers_v3.py", "V3-1", "R",
     "Sec. V-D"),
    ("T10", "Pass density at 5 km, one pass per segment: segment-passes, level offset and joint ranges, real-only",
     ["pdUnitsOne", "pdCalOneMin", "pdCalOneMax", "pdPoolOneMin", "pdPoolOneMax", "pdOneAllDraws", "pdRealOne"],
     "results/v3/pass_density.csv; results/v3/pass_density_summary.csv", "experiments/v3/pass_density.py", "V3-10", "E",
     "abstract, Sec. V-D, Table S19"),
    ("T11", "No-simulator index (label-free car speed exponent, affine) at 5 and 20 km",
     ["nsCarAffineFive", "nsCarAffineTwenty", "nsAlphaCarMin", "nsAlphaCarMax"],
     "results/v3/nosim_index.csv; results/v3/nosim_index_alpha.csv", "experiments/v3/nosim_index.py", "V3-9", "E",
     "Sec. V-D, Table S17"),
    ("T12", "Band associations of the zero-shot bias over V0-V8 (Spearman per band, R2)",
     ["baSpHighBias", "baSpMidHighBias", "baSpRmsBias", "baSpLowBias", "baSpMidBias", "baRtwoRmsBias", "baRtwoHighBias"],
     "results/v3/band_associations.csv", "experiments/v3/level_and_bands.py", "V3-4", "E", "Sec. V-C, Fig. 3b, Table S23"),
    ("T13", "Band-limited retraining: spread of the mean log level and bias over the 8 sensor variants; V4; cost; H3/H3b",
     ["blFullSpreadLvl", "blLowSpreadLvl", "blRatioLvl", "blRatioLvlUrban", "blRatioLvlMotorway", "blFullSpreadBias",
      "blLowSpreadBias", "blNoHighMaxChange", "blLowVfourLvl", "blLowCalMin", "blLowCalMax", "blHthreeHolds",
      "blHthreeBHolds"],
     "results/v3/band_limited.csv", "experiments/v3/band_limited.py", "V3-3", "E", "Sec. V-C, Fig. 3c, Table S24"),
    ("T14", "Level decomposition of V0 and the vehicle-population effect (V4 minus V0)",
     ["ldVzeroUrban", "ldVzeroMotorway", "ldVzeroPctMotorwayAbs", "vpVehicleEffBias", "vpVfourRatioHigh",
      "vpVzeroRatioHigh"],
     "results/v3/level_decomposition.csv; results/v2/summary_variants.csv; results/v2/band_gain.csv",
     "experiments/v3/level_and_bands.py; make_numbers_v3.py", "V3-5", "R", "Sec. V-B, Sec. V-C, Discussion"),
    ("T15", "Paired within-route ranking against the untrained RMS/v^0.5 (per route; bound over routes and models)",
     ["rpRhoRealCphOne", "rpRhoRealCphSix", "rpRhoRealMwThree", "rpRhoRealMwThirteen", "rpRhoVzeroMwThirteen",
      "rpRhoVzeroCphOne", "rpAbsMax", "rpAbsMaxExact"],
     "results/v3/rank_paired.csv", "experiments/v3/rank_paired.py", "V3-6", "E", "abstract, Sec. V-B, Table S5"),
    ("T16", "Speed robustness: real-trained urban elasticity and paired difference with the log speed SD; CV control",
     ["srRealUrbanLsd", "srRealUrbanLsdLo", "srRealUrbanLsdHi", "srDiffUrbanLsd", "srDiffUrbanLsdLo",
      "srDiffUrbanLsdHi", "srDiffUrbanCv", "srDiffUrbanCvLo", "srDiffUrbanCvHi", "srCorrLsdUrban", "srCorrCvUrban"],
     "results/v3/speed_robustness.csv", "experiments/v3/speed_robustness.py", "V3-7", "E", "Sec. V-E, Table S26"),
    ("T17", "Relative errors of real-trained LightGBM by road class (%)", ["reGbmUrban", "reGbmMotorway"],
     "results/v3/relative_errors.csv", "make_numbers_v3.py (from results/v2/summary_real_estimators.csv)", "V3-11", "E",
     "Sec. V-A, Table S6"),
    ("T18", "M7 segment-grid fix: M13 segments and MAE before and after", ["mtMwThirteenOldSeg", "mtMwThirteenNewSeg",
                                                                           "mtMwThirteenOldMae", "mtMwThirteenNewMae"],
     "checkpoints/v2_2026-10-03/results/v2/physics_inversion.csv; results/v2/physics_inversion.csv",
     "experiments/v2/physics_inversion.py", "V3-8", "R", "Supplement S1"),
]
V2_MACROS = {"vbRealOnlyFive", "pcCalMaeFiveMin", "pcCalMaeFiveMax", "pcCalWinsFiveMin", "pcCalWinsFiveMax"}


def main():
    M3 = json.load(open(os.path.join(V3, "paper_numbers_v3.json"), encoding="utf-8"))
    M2 = json.load(open(os.path.join(V2, "paper_numbers_v2.json"), encoding="utf-8"))
    rows = []
    for hid, q, macros, src, script, item, cls, loc in HEADLINES:
        vals = {}
        for m in macros:
            src_m = M2 if m in V2_MACROS else M3
            assert m in src_m, (hid, m)
            vals[m] = src_m[m]
        rows.append(dict(id=hid, quantity=q, values=vals, source=src, script=script, protocol_item=item,
                         evidence_class=cls, paper=loc))
    with open(os.path.join(V3, "final_results_v3.json"), "w", encoding="utf-8") as f:
        json.dump(dict(note="Headline results of the v3 paper; values are the printed LaTeX macros (paper/numbers_v3.tex, "
                            "paper/numbers_v2.tex). Protocol items and evidence classes as in evaluation/PROTOCOL_V3.md.",
                       headlines=rows), f, indent=1, ensure_ascii=False)
    with open(os.path.join(V3, "final_results_v3.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "quantity", "values", "source", "script", "protocol_item", "evidence_class", "paper"])
        for r in rows:
            w.writerow([r["id"], r["quantity"], "; ".join(f"{k}={v}" for k, v in r["values"].items()), r["source"],
                        r["script"], r["protocol_item"], r["evidence_class"], r["paper"]])
    print(len(rows), "headline rows written to results/v3/final_results_v3.{json,csv}")


if __name__ == "__main__":
    main()
