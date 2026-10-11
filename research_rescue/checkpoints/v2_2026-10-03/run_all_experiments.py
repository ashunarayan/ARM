"""One-command reproduction of every number, figure and table of the rescued paper.

    python research_rescue/run_all_experiments.py            # run all steps whose outputs are missing
    python research_rescue/run_all_experiments.py --force    # re-run everything
    python research_rescue/run_all_experiments.py --only lira_ladder lira_zeroshot

Environments: steps marked 'legacy' need the TensorFlow 2.10 environment that can load the rejected paper's Keras
models (PY_LEGACY, default C:/Users/nishk/anaconda3/envs/tf/python.exe); all other steps run in the PyTorch/CUDA
environment (PY, default: the interpreter running this script). Logs: research_rescue/logs/<step>.log

The second analysis round (revision v2, evaluation/PROTOCOL_V2.md) follows the first-round steps; its outputs are in
results/v2/ and its paper macros in paper/numbers_v2.tex. Pinned packages: environment_lock.txt.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.environ.get("PY", sys.executable)
PY_LEGACY = os.environ.get("PY_LEGACY", r"C:/Users/nishk/anaconda3/envs/tf/python.exe")
R = lambda *p: os.path.join(HERE, *p)

# (name, interpreter, script + args, output that marks completion)
STEPS = [
    ("download_lira", PY, ["data/raw/download_lira.py", "all", "8"], R("data", "raw", "lira_cd", "car", "M13_VH.hdf5")),
    ("audit_legacy", "bash", ["audit/run_audits.sh"], R("audit", "outputs", "audit_misc.txt")),
    ("iri_unit_test", PY, ["evaluation/iri_unit_test.py"], R("results", "iri_validation.json")),
    ("iri_alignment", PY, ["evaluation/cph6hh_alignment.py"], R("results", "iri_alignment_search.json")),
    ("lira_sensor_stats", PY, ["evaluation/lira_sensor_stats.py"], R("results", "lira_sensor_stats.json")),
    ("sim_unit_test", PY, ["evaluation/sim_unit_test.py"], R("results", "sim_unit_test.json")),
    ("legacy_fidelity", PY, ["experiments/legacy_fidelity_check.py"], R("results", "legacy_fidelity_check.json")),
    ("beamng_dataset", PY, ["experiments/beamng_build_dataset.py"], R("data", "processed", "beamng", "meta.csv")),
    ("beamng_experiments", PY, ["experiments/exp_beamng.py", "S1_raw", "S1_corr", "S3", "S2"], R("results", "beamng", "S2_iri_raw_metrics.csv")),
    ("beamng_vehicle", PY, ["experiments/exp_beamng_vehicle.py"], R("results", "beamng", "seen_vs_unseen_vehicle.csv")),
    ("sim_generate", PY, ["experiments/sim_generate.py", "p79", "iso", "sweep", "region", "seenveh", "ablation"],
     R("data", "processed", "sim", "p79_train_idealsensor_meta.csv")),
    ("lira_dataset", PY, ["experiments/lira_build_dataset.py"], R("data", "processed", "lira", "units.csv")),
    ("route_overlap", PY, ["evaluation/route_overlap.py"], R("results", "route_overlap.json")),
    ("lira_ladder", PY, ["experiments/exp_lira.py", "ladder", "gap"], R("results", "lira", "ladder_segment_metrics.csv")),
    ("lira_zeroshot", PY, ["experiments/exp_lira.py", "zeroshot"], R("results", "lira", "zeroshot_segment_metrics.csv")),
    ("lira_fewshot", PY, ["experiments/exp_lira.py", "fewshot"], R("results", "lira", "fewshot_raw.csv")),
    ("lira_analysis", PY, ["experiments/exp_lira_analysis.py"], R("results", "lira", "analysis_within_route_ranking.csv")),
    ("lira_compare", PY, ["experiments/exp_lira_compare.py"], R("results", "lira", "compare_zeroshot_vs_real.csv")),
    # post-hoc sensitivity analysis (added after the primary results; reported separately)
    ("posthoc_sensor_sim", PY, ["experiments/sim_generate.py", "measuredsensor", "measuredmix"],
     R("data", "processed", "sim", "p79_train_measuredmix_meta.csv")),
    ("posthoc_sensor_zeroshot", PY, ["experiments/exp_lira.py", "zeroshot_sensor"], R("results", "lira", "zeroshot_sensor_segment_metrics.csv")),
    ("sim_controlled", PY, ["experiments/exp_sim_controlled.py", "general", "region", "speed", "robust"], R("results", "sim", "robustness.csv")),
    ("sim_speed_p79", PY, ["experiments/exp_sim_controlled.py", "speed_p79"], R("results", "sim", "speed_invariance_p79trained.csv")),
    ("pvs", PY, ["experiments/exp_pvs.py"], R("results", "pvs", "pvs_auc.csv")),
    ("references", PY, ["references/build_bib.py"], R("references", "references.tex")),
    ("figures", PY, ["make_figures.py"], None),
    ("tables", PY, ["make_tables.py"], None),
    ("numbers", PY, ["make_numbers.py"], None),
    ("key_metrics", PY, ["make_key_metrics.py"], None),
    # ---- revision v2 (evaluation/PROTOCOL_V2.md); outputs in results/v2
    ("v2_verify_review", PY, ["experiments/v2/verify_review_claims.py"], R("results", "v2", "verify_review_claims.json")),
    ("v2_sim_factorial", PY, ["experiments/sim_generate.py", "telecompliant", "phonerigid"],
     R("data", "processed", "sim", "p79_train_phonerigid_meta.csv")),
    ("v2_variants", PY, ["experiments/v2/simreal_variants.py"], R("results", "v2", "variants_calibration.csv")),
    ("v2_value", PY, ["experiments/v2/value_of_simulation.py"], R("results", "v2", "value_of_simulation.csv")),
    ("v2_value_variants", PY, ["experiments/v2/value_of_simulation_variants.py"], R("results", "v2", "value_of_simulation_variants.csv")),
    ("v2_value_real_index", PY, ["experiments/v2/value_real_index.py"], R("results", "v2", "value_real_index.csv")),
    ("v2_inference", PY, ["experiments/v2/inference_blocks.py"], R("results", "v2", "inference_blocks.csv")),
    ("v2_speed_real", PY, ["experiments/v2/speed_real.py"], R("results", "v2", "speed_real.csv")),
    ("v2_speed_paired", PY, ["experiments/v2/speed_paired.py"], R("results", "v2", "speed_paired.csv")),
    ("v2_real_baselines", PY, ["experiments/v2/real_baselines_v2.py"], R("results", "v2", "unit_disjoint.csv")),
    ("v2_aran", PY, ["experiments/v2/aran_rematch.py"], R("results", "v2", "aran_rematch.csv")),
    ("v2_physics_inversion", PY, ["experiments/v2/physics_inversion.py"], R("results", "v2", "physics_inversion.csv")),
    ("v2_spectra", PY, ["experiments/v2/spectra.py"], R("results", "v2", "spectra_log10_diff.csv")),
    ("v2_band_gain", PY, ["experiments/v2/band_gain.py"], R("results", "v2", "band_gain.csv")),
    ("v2_band_gain_class", PY, ["experiments/v2/band_gain.py", "by_class"], R("results", "v2", "band_gain_by_class.csv")),
    ("v2_speed_scaling", PY, ["experiments/v2/speed_scaling_sim.py"], R("results", "v2", "speed_scaling_sim.csv")),
    ("v2_ranking_untrained", PY, ["experiments/v2/ranking_untrained.py"], R("results", "v2", "ranking_untrained.csv")),
    ("v2_vehicle_sweep", PY, ["experiments/v2/vehicle_sweep.py"], R("results", "v2", "vehicle_sweep.csv")),
    ("v2_summarise", PY, ["experiments/v2/summarise_v2.py"], None),
    ("v2_paired", PY, ["experiments/v2/paired_vs_real.py"], None),
    ("v2_figures", PY, ["make_figures_v2.py"], None),
    ("v2_tables", PY, ["make_tables_v2.py"], None),
    ("v2_numbers", PY, ["make_numbers_v2.py"], None),
    ("v2_final_results", PY, ["make_final_results_v2.py"], None),
    ("bib_cited", PY, ["paper/make_bib_cited.py"], None),
    # the supplement and the main paper cross-reference each other (xr-hyper): compile in turn
    ("paper", "latex", ["supplementary.tex", "main.tex"], None),
    ("compress_predictions", PY, ["results/compress_predictions.py"], None),
]


def run(name, interp, args, log):
    if interp == "bash":
        cmd = ["bash"] + [R(a) for a in args]
        env = dict(os.environ, PY_LEGACY=PY_LEGACY)
    elif interp == "latex":
        d, rc = R("paper"), 0
        for _ in range(2):            # two rounds over all documents for cross-references between them
            for tex in args:
                rc = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex], cwd=d, stdout=log,
                                    stderr=subprocess.STDOUT).returncode or rc
        return rc
    else:
        cmd = [interp, R(args[0])] + args[1:]
        env = os.environ.copy()
    return subprocess.run(cmd, cwd=HERE, stdout=log, stderr=subprocess.STDOUT, env=env).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    os.makedirs(R("logs"), exist_ok=True)
    for name, interp, args, done in STEPS:
        if a.only and name not in a.only:
            continue
        if not a.force and done is not None and os.path.exists(done):
            print(f"[skip] {name} (output exists)"); continue
        t0 = time.time()
        with open(R("logs", f"{name}.log"), "w") as log:
            rc = run(name, interp, args, log)
        print(f"[{'ok' if rc == 0 else 'FAILED'}] {name} ({time.time() - t0:.0f}s)")
        if rc != 0:
            print(f"   see logs/{name}.log"); sys.exit(rc)


if __name__ == "__main__":
    main()
