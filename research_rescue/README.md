# Research rescue: vehicle-vibration IRI estimation, re-examined

This folder contains everything produced while turning the desk-rejected paper
(`nish_conf_paper/main.tex`, ICONAT 2026 #3979) into a scientifically defensible study, in three analysis rounds:
the first rescue (v1), a second revision (v2) in response to an independent adversarial review
(`review/first.md`), and a third revision (v3) in response to `INDEPENDENT_REVIEW_V3.md`. The original code, data and
paper are untouched; see `BASELINE_STATE.md` for their state. The reviewed v2 state is preserved in
`checkpoints/v2_2026-10-03/` (with `MANIFEST.sha256`).

Final corrections (2026-10-11, after the final verification audit `review/final_audit/audit.md`):

* `FINAL_SUBMISSION_REPORT.md` - each audit issue and its resolution, files changed, build and consistency checks,
  open items; audited state preserved in `checkpoints/v3_2026-10-11/`; checks in `results/v3/verification_final.json`

Start here (v3):

* `FINAL_VERIFICATION_REPORT_V3.md` - what the third round verified, ran, changed and left open
* `paper/main.pdf`, `paper/supplementary.pdf` - the revised paper (LaTeX sources in `paper/`; v1 kept in `paper/v1_archive/`, v2 in the checkpoint)
* `evaluation/PROTOCOL_V3.md` (frozen 2026-10-10, SHA-256 994cd027...a415ccc6) and `evaluation/PROTOCOL_V3_DEVIATIONS.md`
* `IMPLEMENTATION_AUDIT_V3.md` - every recommendation of the review: verification, class A-E, decision, outcome
* `CLAIM_AUDIT_V3.md` - every claim of the v3 paper checked against the result files
* `results/v3/final_results_v3.csv` (headline numbers with provenance) and `results/v3/verification_v3.json` (25 independent checks)

Second round:

* `FINAL_REPORT_V2.md` - what the second round verified, rejected, added, changed and left open (sections A-J)
* `evaluation/PROTOCOL_V2.md` - protocol of the second round, frozen before its analyses, with dated addenda E5-E10
* `REVISION_PLAN_V2.md` - every review concern: evidence, validity, severity, fix, final status
* `CLAIM_AUDIT_V2.md` - every claim of the revised paper checked against the result files
* `REVIEWER_AUDIT_V2.md` - final adversarial self-review (15 questions)
* `CHANGELOG.md` - every implementation decision and fix, in order
* First round: `FINAL_REPORT.md`, `REVIEWER_AUDIT.md`, `evaluation/FINAL_EVALUATION_PROTOCOL.md`;
  references: `references/REFERENCE_AUDIT.md` (sections A-D)

## Layout

| Path | Content |
|---|---|
| `common/` | shared code: validated IRI (`iri.py`), features, preprocessing (identical for real and simulated data), models, statistics, simulator (`vehsim.py`, `sensor.py`, `simpipe.py`), LiRA-CD readers, plotting |
| `config/` | frozen model configurations (`models.json`) and simulator ranges (`sim_ranges.json`) |
| `audit/` | re-runnable audit of the legacy pipeline (TensorFlow environment) |
| `evaluation/` | protocols, IRI validation against the P79 profilometer, simulator unit tests |
| `experiments/` | first-round dataset builders and experiments (BeamNG, LiRA-CD, parametric simulation, PVS) |
| `experiments/v2/` | second-round analyses (one script per protocol item; shared helpers in `common_v2.py`) |
| `experiments/v3/` | third-round analyses (one script per item of `PROTOCOL_V3.md`; shared helpers in `common_v3.py`) |
| `data/raw/`, `data/processed/` | downloaders (raw data not committed) and regenerated intermediate datasets (`data/processed/v3/` caches zero-shot predictions) |
| `results/` | first-round metrics and predictions; `results/v2/` second-round and `results/v3/` third-round results |
| `figures/`, `tables/` | generated: `make_figures*.py` / `make_tables*.py` for v1, v2 (`v2_*`, `v2s_*`) and v3 (`v3_*`, `v3s_*`) |
| `paper/` | `main.tex`, `supplementary.tex`, `sections/`, macros `numbers.tex` (v1), `numbers_v2.tex` (v2), `numbers_v3.tex` (v3) |
| `checkpoints/v2_2026-10-03/` | copy of the reviewed v2 state with a SHA-256 manifest |
| `review/v3_checks/` | the reviewer's read-only checks (c1-c8) and their outputs |

## Environment

All second-round analyses ran in the conda environment `torch_gpu` (Python 3.11.14, Windows 11, RTX 4050, CUDA 11.8);
the exact package versions are pinned in `environment_lock.txt` (`pip install -r environment_lock.txt`; PyTorch
2.7.1+cu118 comes from `https://download.pytorch.org/whl/cu118`, a CPU build also works for v2). Key versions: NumPy
2.4.4, SciPy 1.16.3, pandas 2.3.3, scikit-learn 1.8.0, LightGBM 4.6.0, matplotlib 3.10.7, statsmodels 0.14.6.
The audit of the legacy Keras models needs TensorFlow 2.10 (environment `tf`, first round only).
LaTeX: MiKTeX / pdfTeX with IEEEtran, `xr-hyper` and `placeins`.
External data: LiRA-CD (CC BY 4.0, doi:10.11583/DTU.c.6659909, ~6.6 GB, downloaded automatically); the BeamNG corpus
and PVS files are in this repository (`ml_model_work/`).

## Reproduce

```bash
# everything, in order (skips steps whose outputs exist; --force recomputes; --only <step ...> runs selected steps)
python research_rescue/run_all_experiments.py
```

Second round only (run from the repository root after the first-round steps; outputs in `results/v2/`):

```bash
python research_rescue/experiments/v2/verify_review_claims.py        # re-reads v1 results to check the review
python research_rescue/experiments/sim_generate.py telecompliant phonerigid   # V7, V8 (seeds 41001, 41002)
python research_rescue/experiments/v2/simreal_variants.py            # E1/E2/R3: zero-shot + calibration, all variants
python research_rescue/experiments/v2/value_of_simulation.py         # R4: equal profile budget, V0
python research_rescue/experiments/v2/value_of_simulation_variants.py  # E5: same for V1-V8 (or: ... V1 V2 / V3 V4 / ... then 'merge')
python research_rescue/experiments/v2/value_real_index.py            # E9: real-only vibration index, same draws
python research_rescue/experiments/v2/inference_blocks.py            # R6: block/route inference, ACF, variance components
python research_rescue/experiments/v2/speed_real.py                  # R5: fixed-road speed elasticities
python research_rescue/experiments/v2/speed_paired.py                # E8: paired elasticity differences
python research_rescue/experiments/v2/real_baselines_v2.py           # R2 unit-disjoint, R7 Bajic anchor, R8 passes
python research_rescue/experiments/v2/aran_rematch.py                # R9: second profilometer
python research_rescue/experiments/v2/physics_inversion.py           # R10: calibrated quarter-car inversion M7
python research_rescue/experiments/v2/spectra.py                     # E3: spectra on common segment x speed cells
python research_rescue/experiments/v2/band_gain.py && python research_rescue/experiments/v2/band_gain.py by_class   # E4
python research_rescue/experiments/v2/speed_scaling_sim.py           # E7: speed scaling, simulation vs real
python research_rescue/experiments/v2/ranking_untrained.py           # E10: ranking by untrained statistics
python research_rescue/experiments/v2/vehicle_sweep.py               # S1: number of training vehicles
python research_rescue/experiments/v2/summarise_v2.py                # summary tables
python research_rescue/experiments/v2/paired_vs_real.py              # E5/E6/E9 paired draw-by-draw comparisons
python research_rescue/make_figures_v2.py && python research_rescue/make_tables_v2.py
python research_rescue/make_numbers_v2.py && python research_rescue/make_final_results_v2.py
python research_rescue/paper/make_bib_cited.py
cd research_rescue/paper && pdflatex supplementary.tex && pdflatex main.tex && pdflatex supplementary.tex && pdflatex main.tex
```

`evaluation/PROTOCOL_V2.md` maps every script to its protocol item and evidence class (C1 confirmatory, R
re-analysis, E exploratory, S controlled simulation).

Third round only (after the second round; outputs in `results/v3/`; the same as
`python research_rescue/run_all_experiments.py --force --only v2_physics_inversion v2_summarise v2_numbers v2_tables v3_pooled v3_pooled_merge v3_calib_uncertainty v3_band_limited v3_level_and_bands v3_rank_paired v3_rank_scope v3_speed_robustness v3_nosim_index v3_pass_density v3_numbers v3_tables v3_figures v3_final_results bib_cited paper v3_verify final_verify`):

```bash
python research_rescue/experiments/v2/physics_inversion.py           # V3-8: M7 with the fixed segment grid
python research_rescue/experiments/v2/summarise_v2.py && python research_rescue/make_numbers_v2.py && python research_rescue/make_tables_v2.py
python research_rescue/experiments/v3/pooled_vs_real.py              # V3-1 joint training, V0-V8 + V10 (or in parallel:
                                                                     #   ... V0 V1 V2 / V3 V4 V5 / V6 V7 V8 / V10, then 'merge')
python research_rescue/experiments/v3/pooled_vs_real.py merge
python research_rescue/experiments/v3/calib_uncertainty.py           # V3-2 test-route intervals (needs the merged pooled arm)
python research_rescue/experiments/v3/band_limited.py                # V3-3 band-limited retraining
python research_rescue/experiments/v3/level_and_bands.py             # V3-4 band associations, V3-5 level decomposition
python research_rescue/experiments/v3/rank_paired.py                 # V3-6 paired within-route ranking
python research_rescue/experiments/v3/rank_scope.py                  # final audit: per-route ranking of every estimator
python research_rescue/experiments/v3/speed_robustness.py            # V3-7 speed robustness rows
python research_rescue/experiments/v3/nosim_index.py                 # V3-9 no-simulator index
python research_rescue/experiments/v3/pass_density.py                # V3-10 pass density (delete a partial results/v3/pass_density.csv before rerunning)
python research_rescue/make_numbers_v3.py && python research_rescue/make_tables_v3.py && python research_rescue/make_figures_v3.py
python research_rescue/make_final_results_v3.py                      # headline numbers with provenance
python research_rescue/paper/make_bib_cited.py
cd research_rescue/paper && pdflatex supplementary.tex && pdflatex main.tex && pdflatex supplementary.tex && pdflatex main.tex && cd ../..
python research_rescue/evaluation/verify_v3.py                       # 25 independent checks -> results/v3/verification_v3.json
python research_rescue/evaluation/verify_final.py                    # 15 checks of the final corrections -> results/v3/verification_final.json
```

`make_numbers_v3.py` asserts that the joint-training arm reproduces the reviewer's check c4 (within 0.0025 m/km), that
no macro is missing (`??`) and that no macro name collides with `numbers.tex` or `numbers_v2.tex`.

## Provenance of the numbers

Every number in `paper/main.tex` and `paper/supplementary.tex` is a LaTeX macro: `paper/numbers.tex` (first round,
`make_numbers.py`) and `paper/numbers_v2.tex` (second round, `make_numbers_v2.py`, written from `results/v2/*`; a
missing input prints `??` in the PDF, and the script asserts that none is missing). `results/v2/final_results_v2.json`
/ `.csv` list each headline number with its macro, source file, script, evidence class and location in the paper.
Rerunning the generators (`summarise_v2.py` ... `make_numbers_v2.py`) on the same result files reproduces
`numbers_v2.tex` byte for byte (checked 2026-10-03). Third round: `paper/numbers_v3.tex` from `make_numbers_v3.py`
(also `results/v3/paper_numbers_v3.json`); `results/v3/final_results_v3.json` / `.csv` list each new headline number
with its macros, source file, script, protocol item and evidence class; `evaluation/verify_v3.py` re-derives the key
numbers independently and checks the PDFs, the frozen protocol hash and the checkpoint manifest.

## Seeds and determinism

* Simulation: fixed generator seeds in `experiments/sim_generate.py` (V7 41001, V8 41002; vehicle-number sweep pool
  20261003); V7/V8 random half of passes: seed 7 (`common_v2.variant_training_set`).
* Calibration and equal-budget draws: `numpy.random.default_rng(1000 * d + 7)` for draw d = 0..19, identical across
  all arms, so draws are paired.
* Bootstraps: fixed seeds in each script (2000 resamples; 1000 for spectra). Third round: test-route intervals seed
  3003 (B = 2000), paired ranking seed 2026 (B = 2000), speed robustness seed 5 (B = 1000), pass-density subsampling
  `default_rng(100000 + 1000 * d + m)`.
* Neural nets (first round): seeds 0-4; cuDNN kernels are not bit-deterministic, so neural-net metrics can differ in
  the last digits across GPU/driver versions. LightGBM runs with `random_state=0`.

## Run times (development machine: RTX 4050 Laptop 6 GB, 12 logical CPUs)

First round: download 1-2 h (network-bound), datasets ~20 min, BeamNG ~1.5 h, LiRA-CD experiments ~3 h, controlled
simulation ~1 h. Second round: run times were not logged systematically; the equal-budget runs for V1-V8 took about
16 min with four parallel processes (`OMP_NUM_THREADS=3`), and the summary, figure, table and macro steps take
under a minute each. Third round (from `logs/v3/`): joint-training arm about 28 min with four parallel processes
(three variants each, and V10 alone); pass density 19 min (`OMP_NUM_THREADS=10`); test-route intervals about 2 min; the other
v3 analyses a few minutes each; numbers, tables, figures and the two LaTeX passes under a minute each.

## Not done (needs the authors)

Nothing has been committed to git; committing (with tags at the protocol-freeze points) and publishing the code and
the BeamNG corpus are the authors' decisions. Before submission a human should read the primary articles that are
cited at title level or through a secondary description (`references/REFERENCE_AUDIT.md` §E) and confirm the target
venue's page limit (main paper: 10 pages, supplement 18). New paired data (another car, sensor or city) are needed for any
external-validity claim.
