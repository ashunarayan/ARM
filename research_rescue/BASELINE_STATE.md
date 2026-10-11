# Baseline state (before any research-rescue change)

Snapshot taken 2026-10-02. Nothing in `ml_model/`, `ml_model_work/`, `nish_conf_paper/` or `paper/` was modified by the rescue; all new work lives in `research_rescue/`.

## 1. Repository state

- Git HEAD: `4e3b3d6f384b9b4839111797971e9fcdcc6084fe` ("updated IRI conference paper"), branch `main`, remote `https://github.com/ashunarayan/ARM.git`.
- Working tree at snapshot: 133 uncommitted entries (modified `ml_model/iri_v3/*`, `ml_model/baseline/*`, `nish_conf_paper/main.tex`, images; untracked `ml_model/baseline/outputs/all_model_predictions_seed_4*.npz`). The rescue does not commit anything.
- Submitted paper: `nish_conf_paper/main.tex` (compiled `main.pdf`, 2026-07-31). Desk-rejected at IEEE ICONAT 2026 (Paper 3979); decision text in `nish_conf_paper/rejection.txt` (generic 9-point template).
- Python environments used to reproduce legacy results: `C:/Users/nishk/anaconda3/envs/tf` (TF 2.10, CPU only: CUDA DLLs absent). New work: `C:/Users/nishk/anaconda3/envs/torch_gpu` (PyTorch 2.7.1+cu118, RTX 4050 6 GB; numba is unusable there because NumPy 2.4.4 was installed in April 2026 — pre-existing).
- No requirements/environment file existed in the repository.

## 2. Claims made by the rejected paper (verbatim intent)

1. "Curvature-adaptive mesh tessellation correction" that "mathematically resolves" polygon-facet jitter and enables physics-based IRI ground truth.
2. A multi-vehicle (3 classes), multi-environment (3 maps) Sim2Real corpus "decoupling traversal velocity from reference 80 km/h IRI labels".
3. A "speed-invariant" dual-branch depthwise-separable 1D-CNN with inverse-quadratic kinetic normalisation, 2-D inverse-frequency sampling, asymmetric Huber loss and post-training isotonic calibration (PICA).
4. 5-seed test MAE 1.650 ± 0.061 m/km, R² 0.521 ± 0.027 on "an independent temporal test split"; "peak single-seed" R² 0.558 / MAE 1.689.
5. 77.9 % of test predictions within ±1.5 m/km ("AASHTO R 56-inspired screening tier"); 63.64 % within ±1.0; 86.53 % within ±2.0.
6. Ablation: kinetic normalisation "essential" (R² 0.521 → 0.441); 2-D sampling vital for edge cases.
7. Zero-shot on PVS (108.47 km) "correctly ranks surface degradation types and pinpoints defect locations".
8. Speed-invariant predictions 25–85 km/h across three chassis; "baseline models without speed normalisation display quadratic error growth".
9. 25,769 parameters; 1.12 ms on-device inference; weights/scripts open-sourced.

## 3. Existing data

| Data | Location | Content |
|---|---|---|
| BeamNG raw trips | `ml_model_work/data/simulation/data/IRI_new_experiments/{hopper,sunburst2,vivace}/{automation_test_track,east_coast_usa,west_coast_usa}/trip_N/` | 19 trips, 137.7 km, ~160 min, manually driven by one driver. `imu_speed_data.csv`, `iri_sensor_data.csv` (100 Hz nominal), labels `readings_2.csv` (also `readings_3/5/10.csv` variants) |
| Older BeamNG trips | `ml_model_work/data/simulation/data/IRI_old/roamer/...` | "roamer" vehicle; older label pipeline (`readings.csv`); used only in the stress-test figure |
| Cached windows | `ml_model/iri_v2/output/iri_v2_data.npz` | train 9,082 / val 2,796 / test 1,903 windows (100 m, 10 m stride) |
| Baseline windows | `ml_model/baseline/data/{train,val,test}_data.npz` | same windows, *different random resampling draw* |
| PVS | `ml_model_work/data/raw/multi_class_kaggle/PVS 1..9` | 9 trips = 3 routes × 3 passes; surface-type and quality labels (no IRI) |

## 4. Existing models

| Model | Location | Used for |
|---|---|---|
| Run 1–5 × 5 seeds (ablation) | `ml_model/iri_v3/outputs/run_0X/seed_4Y/best_model.keras` (+ `calibration_lut.json`) | Tables I (proposed row), II |
| iri_v2 / iri_compliant single model | `ml_model/iri_compliant/best_iri_model.keras`, `iri_background_model.tflite`, `mobile_calibration_lut.json` | Table III, Fig. 4, PVS (Table V, Figs. 5–6), stress test (Fig. 7) |
| Baseline families × 5 seeds | `ml_model/baseline/outputs/models/seed_4Y/` | Table I baseline rows |

## 5. Scripts that produced each reported number

| Paper item | Producing script | Notes |
|---|---|---|
| Labels (`readings_2.csv`) | `ml_model/iri_compliant/iri_calculation.py` (= `ml_model_work/data/simulation/scripts/IRI/iri_new_experiments_2.py`) | mesh correction + Golden Car |
| Raw collection | `ml_model/iri_compliant/collect.py` | BeamNG v0.38.3.0, BeamNGpy |
| Windows (`iri_v2_data.npz`) | `ml_model/iri_v2/model_4.ipynb` (mirrored in `ml_model/iri_v3/data_pipeline.py`) | |
| Table I proposed row, Table II | `ml_model/iri_v3/run_ablation.py` → `outputs/ablation_summary.csv` | |
| Table I baselines | `ml_model/baseline/01_*.py`, `02_*.py`, `03_*.py` | |
| Table III, Fig. 4 | `ml_model/iri_v2/model_4.ipynb` / `ml_model/iri_compliant/model.ipynb` | single model |
| Table IV (tiers) | 63.64 %: `ml_model/AASHTO_compliance/01_calculate_aashto_compliance.py`; 77.89 % and 86.53 %: **no producing script found** | |
| PVS Table V, violin, map | `ml_model/pvs_comparision/pvs_analysis.py`, `generate_asphalt_anomaly_map.py` | |
| Stress test Fig. 7 | `ml_model/speed_invariance_test/01_*.py`, `02_*.py` | |
| Edge-case Fig. | `ml_model/iri_v3/plot_edge_cases.py` | |

## 6. Known inconsistencies (paper vs. code), verified in the Sept-2026 audit

1. Windows: paper "100 m non-overlapping"; code 100 m with 10 m stride; window label = time-weighted mean of per-sample fixed-segment labels.
2. Resampling rates: paper 20/30/40/50/100 Hz "with sensor noise"; code 10/15/20/25/30/50 Hz, zero-order hold, no noise anywhere.
3. 250 mm tyre-enveloping filter: a no-op at DX = 0.25 m (`iri_calculation.py:163-164`).
4. v_safe: paper 3.0 m/s; code 5.0 m/s. LiDAR offset: paper ±0.85 m; code ±0.95 m.
5. Undisclosed: oversampling of IRI > 10 windows; predictions ≥ 40 m/km discarded before scoring (`iri_v3/evaluate.py:29-35`).
6. "Peak single-seed R² 0.558 / MAE 1.689" matches no saved run.
7. Table III and Fig. 4 come from a different model instance than Tables I–II; PVS and stress test use yet another (`iri_compliant`).
8. Stress-test "Hopper" is actually "roamer" from the older dataset; the "quadratic error growth of baselines" claim has no code.
9. Severity bin counts (paper 1,047 "Good"; actual 1,120) and "Very Poor > 8" (should be ≥ 14).
10. "1.12 ms on-device" and GitHub release URL: no evidence in repository.
11. References: [8], [14], [17], [19] not found; [18] wrong authors/topic; [16], [25] wrong volume/pages.

## 7. Known leakage

1. Validation (`automation_test_track` trip 1) and test (trips 2, 3) are the same track: 90–100 % of test samples within 2 m of a validation path. Validation drives early stopping, LR schedule and isotonic calibration (PICA).
2. Table IV calibration (`AASHTO_compliance/01_*.py:96`) is fitted on the test labels.
3. Test predictions ≥ 40 m/km discarded (prediction-dependent test filtering).
4. Test-set reuse across many model iterations (iri_v2 model_1–6, model_4_2 variants, iri_v3_pica_last, iri_v3).
5. Random resampling augmentation applied to validation/test; different draws for baselines vs. proposed model.
6. PVS: class thresholds grid-searched and scored on the same PVS data (`ml_model/review_work`), not used in the paper.

## 8. Known invalid methodology

1. Labels: the "mesh correction" leaves only 7.1 % of the profile untouched, fully smooths 63.9 %, lowers median segment IRI 9.2 → 3.1 m/km, changes the severity class of 74 % of segments; never validated against a reference.
2. Kinetic normalisation multiplies gravity-including a_z by (22.22/v)²: the normalised channel mean becomes a speed readout (Spearman 0.995 with speed). Measured body-acceleration scaling in the data is ~v^0–0.2, not v².
3. BeamNG acquisition: unsynchronised threads; 48–68 % of consecutive IMU rows are exact duplicates; `accSmooth` used; `sim_time` is a wall-clock index; no sensor noise model.
4. PVS evidence: speed alone separates surfaces better than the model (AUC 0.977 vs 0.937); within cobblestone/dirt the model inverts Regular vs Bad (AUC 0.33).
5. Uncertainty reported as seed std only; a 100 m-block bootstrap gives R² [0.36, 0.69] for one seed.
6. Cascaded ablation; asymmetric loss + PICA net ≈ 0; KN "collapse" driven by one seed.
7. AASHTO R 56 (profiler certification) used as an accuracy-tier framework for a software estimator.

Audit scripts that established sections 6–8 are re-run in `research_rescue/audit/` (outputs in `research_rescue/audit/outputs/`).
