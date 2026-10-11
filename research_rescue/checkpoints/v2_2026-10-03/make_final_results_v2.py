"""Revision v2: headline results with provenance (results/v2/final_results_v2.json and .csv).

Every headline number of the revised paper is listed with the LaTeX macro that prints it, the result file it comes
from, the script that wrote that file and the evidence class (PROTOCOL_V2.md). Values are read from
results/v2/paper_numbers_v2.json, which make_numbers_v2.py generates from the result files, so this table cannot
drift from the paper. Run after make_numbers_v2.py.
"""
from __future__ import annotations

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, "results", "v2")

# (id, quantity, macros, source file(s), script, evidence class, paper location)
HEADLINES = [
    ("H1", "Real-trained LightGBM, within-route MAE (m/km)", ["vrGbmMaeWithin"], "summary_real_estimators.csv",
     "experiments/v2/summarise_v2.py", "C1", "Table I, abstract"),
    ("H2", "V0 simulation-trained LightGBM (zero-shot), within-route MAE (m/km)", ["vrSimVzeroMaeWithin"],
     "summary_real_estimators.csv", "experiments/v2/summarise_v2.py", "C1", "Table I, abstract"),
    ("H3", "V0 minus real-trained, pooled segment MAE difference with 5 km-block 95 % CI (m/km)",
     ["vrSimVzeroDfive", "vrSimVzeroDfiveLo", "vrSimVzeroDfiveHi"], "summary_real_estimators.csv / inference_blocks.csv",
     "experiments/v2/summarise_v2.py, experiments/v2/inference_blocks.py", "C1 estimand, R inference", "Table I, Sec. V-B"),
    ("H4", "Within-route Spearman of simulation-trained LightGBM over V0-V8 (real-trained: vrGbmRhoWithin)",
     ["vvRhoMin", "vvRhoMax", "vrGbmRhoWithin"], "summary_variants.csv", "experiments/v2/simreal_variants.py", "E",
     "Table II, Fig. 2a, abstract"),
    ("H5", "Zero-shot pooled bias over V0-V8 (m/km)", ["vvBiasMin", "vvBiasMax"], "summary_variants.csv",
     "experiments/v2/simreal_variants.py", "E", "Table II, Fig. 2b, abstract"),
    ("H6", "Holder-resonance effect on the bias, telematics-like / phone-like sensor (m/km)",
     ["vvHolderEffTele", "vvHolderEffPhone"], "summary_variants.csv", "experiments/v2/simreal_variants.py", "E",
     "Sec. V-B"),
    ("H7", "Spearman (9 variants) of zero-shot bias with the 10-15 Hz real/sim amplitude ratio", ["bgRhoHigh"],
     "band_gain.csv + summary_variants.csv", "experiments/v2/band_gain.py", "E", "Fig. 3b, Sec. V-C"),
    ("H8", "Simulation on all profiles + level offset from 5 km of paired drives, MAE range over V0-V8 (m/km)",
     ["pcCalMaeFiveMin", "pcCalMaeFiveMax"], "paired_vs_real.csv (variants_calibration.csv)",
     "experiments/v2/simreal_variants.py, experiments/v2/paired_vs_real.py", "R", "Table III, Fig. 4b, abstract"),
    ("H9", "Real-only LightGBM trained on the same 5 km, MAE (m/km)", ["vbRealOnlyFive"], "summary_value_of_sim.csv",
     "experiments/v2/value_of_simulation.py, experiments/v2/summarise_v2.py", "R", "Table III, abstract"),
    ("H10", "Draws (of 20) in which simulation + 5 km level beats real-only LightGBM on 5 km, range over V0-V8",
     ["pcCalWinsFiveMin", "pcCalWinsFiveMax"], "paired_vs_real.csv", "experiments/v2/paired_vs_real.py", "E",
     "Sec. V-D, abstract"),
    ("H11", "Draws (of 20) in which simulation + level beats real-only LightGBM for V1/V3/V5 at 10 km and 20 km",
     ["pcCalHiDefWinsTenMin", "pcCalHiDefWinsTenMax", "pcCalHiDefWinsTwentyMax"], "paired_vs_real.csv",
     "experiments/v2/paired_vs_real.py", "E", "Sec. V-D, abstract"),
    ("H12", "Equal profile budget, simulation minus real-only LightGBM at 20 km, range over V0-V8 (m/km)",
     ["pcSameDiffTwentyMin", "pcSameDiffTwentyMax"], "paired_vs_real.csv (value_of_simulation*.csv)",
     "experiments/v2/value_of_simulation.py, experiments/v2/value_of_simulation_variants.py", "R (V0) / E (V1-V8)",
     "Sec. V-D, Fig. 4a"),
    ("H13", "Fixed-road speed elasticity: real-trained LightGBM, V0 LightGBM, paired difference (5 km blocks)",
     ["elRealGbmPooled", "elSimGbmPooled", "epVzeroPooled", "epVzeroPooledLo", "epVzeroPooledHi"],
     "speed_real.csv, speed_paired.csv", "experiments/v2/speed_real.py, experiments/v2/speed_paired.py", "R / E",
     "Sec. V-E, Fig. 5"),
    ("H14", "Raw vibration RMS speed elasticity on a fixed road: real urban / motorway vs simulated ranges over V0-V8",
     ["ssRealUrban", "ssRealMotorway", "ssSimUrbanMin", "ssSimUrbanMax", "ssSimMotorwayMin", "ssSimMotorwayMax"],
     "speed_scaling_sim.csv", "experiments/v2/speed_scaling_sim.py", "E", "Sec. V-C"),
    ("H15", "Unseen-vehicle penalty at 30 / 100 training vehicles (%), route-bootstrap upper bound at 100",
     ["vsThirtyRel", "vsHundredRel", "vsHundredRelHiRoute"], "vehicle_sweep.csv", "experiments/v2/vehicle_sweep.py", "S",
     "Table IV, Fig. 6"),
    ("H16", "Residual autocorrelation of segment errors at 100 m and 1 km (real-trained LightGBM)",
     ["acfGbmHundred", "acfGbmKm"], "residual_acf.csv", "experiments/v2/inference_blocks.py", "R", "Sec. IV"),
    ("H17", "Calibrated quarter-car inversion M7: within-route MAE and paired difference to LightGBM",
     ["vrInvMaeWithin", "vrInvDfive", "vrInvDfiveLo", "vrInvDfiveHi"], "summary_real_estimators.csv (physics_inversion*.csv)",
     "experiments/v2/physics_inversion.py", "R", "Table I, Sec. V-A"),
    ("H18", "Unit-disjoint vs size-matched real training, MAE on CPH1 / CPH6 / M13",
     ["udCphOneDis", "udCphOneCtrl", "udCphSixDis", "udCphSixCtrl", "udMwThirteenDis", "udMwThirteenCtrl"],
     "unit_disjoint.csv", "experiments/v2/real_baselines_v2.py", "R", "Sec. V-A, Table S7"),
]


def main():
    M = json.load(open(os.path.join(V2, "paper_numbers_v2.json"), encoding="utf-8"))
    rows = []
    for hid, q, macros, src, script, cls, loc in HEADLINES:
        missing = [m for m in macros if m not in M]
        assert not missing, (hid, missing)
        rows.append(dict(id=hid, quantity=q, values={m: M[m] for m in macros}, source=f"results/v2/{src}", script=script,
                         evidence_class=cls, paper=loc))
    with open(os.path.join(V2, "final_results_v2.json"), "w", encoding="utf-8") as f:
        json.dump(dict(note="Headline results of the revised paper; values are the printed LaTeX macros "
                            "(paper/numbers_v2.tex). Evidence classes as in evaluation/PROTOCOL_V2.md.",
                       headlines=rows), f, indent=1, ensure_ascii=False)
    with open(os.path.join(V2, "final_results_v2.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "quantity", "values", "source", "script", "evidence_class", "paper"])
        for r in rows:
            w.writerow([r["id"], r["quantity"], "; ".join(f"{k}={v}" for k, v in r["values"].items()), r["source"],
                        r["script"], r["evidence_class"], r["paper"]])
    print(len(rows), "headline rows written to results/v2/final_results_v2.{json,csv}")


if __name__ == "__main__":
    main()
