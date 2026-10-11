# Final evaluation protocol (frozen)

Frozen: 2026-10-02, **before** any model in the rescue was evaluated on a test fold.
Allowed changes after freezing: bug fixes that do not depend on test results (each logged in
`research_rescue/CHANGELOG.md` with the reason). Thresholds, splits, metrics and claim criteria below
are not modified after seeing test results.

## 0. General rules (all domains)

1. No test-fold labels or test-fold inputs are used for training, early stopping, calibration,
   normalisation statistics, feature selection, the speed exponent alpha, or hyper-parameter selection.
2. No prediction is removed, filtered or capped based on its value, except clipping to >= 0 m/km
   (IRI is non-negative by definition). Every prediction on every test unit is saved
   (`research_rescue/results/predictions/*.csv`).
3. Test tensors are built once, deterministically (no random augmentation of test inputs), and every
   model is scored on exactly the same test units.
4. Evaluation units are non-overlapping 100 m segments. Overlapping windows may be used for training only,
   and only with labels computed exactly for each window.
5. Uncertainty: cluster bootstrap with B = 2000 resamples of independent physical units (definitions below),
   95 % percentile intervals. Seed variation of neural models is reported separately (mean ± SD over seeds)
   and never used as the confidence interval. Model differences: paired cluster bootstrap on the same
   resamples; Holm correction within each comparison family (all models vs. the reference model of a table).
6. Every neural model is trained with 5 seeds (0-4). Tree/linear models are deterministic given the data.
7. Metrics: MAE (primary), RMSE, bias (mean prediction - label), Spearman rho, R^2 (reported, but not used for
   claims across datasets), class agreement on a-priori IRI condition bands (FHWA 23 CFR 490 thresholds:
   good < 1.50 m/km, fair 1.50-2.68, poor >= 2.68; accuracy and quadratic-weighted Cohen kappa).
8. Hyper-parameter budget (identical across model families): at most 6 configurations per family,
   selected by inner validation inside the training folds (defined per domain). Defaults are fixed in
   `research_rescue/config/models.json`.

## 1. Real data: LiRA-CD (primary evidence)

* Units: (100 m segment on the P79 chainage grid) x (car pass). A unit requires >= 90 % coverage of the
  segment by one contiguous traversal, mean speed >= 2 m/s, GPS lateral distance to the P79 track <= 20 m.
* Label: P79 IRI, mean of both wheel paths (MRI), recomputed from the published P79 laser profile with the
  validated implementation (`evaluation/iri_unit_test.py`). Sensitivity analysis: the P79-reported IRI on
  the 7 file pairs that pass the a-priori consistency rule.
* Outer split: leave-one-route-out over {CPH1, CPH6, M3, M13}; both driving directions of the test route
  are held out together. Results are reported per held-out route and pooled over the 4 test folds.
* Inner validation (early stopping, hyper-parameters, alpha, calibration): leave-one-route-out inside the
  three training routes for model selection; early stopping of neural nets on a grouped 20 % hold-out of
  training segments (all passes of a segment together).
* Primary granularity: segment level = mean of the pass-level predictions of a segment vs. its label
  (crowdsourcing aggregation). Secondary: pass level (each unit separately).
* Bootstrap clusters: segments (all passes of a segment resampled together). Route-level results are
  additionally shown per fold (n = 4 routes, no route-level CI claimed).
* Zero-shot simulation->real: models trained only on simulated data; the simulator may use the P79
  profiles of the three training routes or synthetic ISO 8608 profiles, never the test route's profile.
* Value of simulation: real training subsets of k km of distinct road (contiguous 1 km blocks sampled from
  the training routes), k in {1, 2, 5, 10, 20, all}; 5 random draws per k; real-only vs. simulation-
  pretrained + real fine-tuned; same test folds as above.

## 2. Game-engine simulation: BeamNG (secondary evidence; diagnostics)

* Units: 100 m segments on the 2-D-position chainage grid of each trip (the legacy label grid).
* Labels: `iri_raw` (validated algorithm on the raw LiDAR profile) and `iri_legacy` / `iri_corr` (legacy
  curvature-adaptive correction). Neither is validated as true IRI for BeamNG geometry; both are reported.
* Splits: (S1) leave-one-map-out (3 folds); (S2) leave-one-vehicle-and-map-out (9 folds: train on the two
  other vehicles on the two other maps); (S3) the legacy split (train east+west, validate on test-track
  trip 1, test on test-track trips 2-3) reproduced only to quantify protocol inflation.
* Inner validation for S1/S2: the highest-numbered trip of every (vehicle, map) pair in the training maps.
  (These trips overlap spatially with training trips; they are used only for early stopping/calibration.)
* Bootstrap clusters: physical location cells (map, 100 m x 100 m grid cell of the segment centre), so
  repeated traversals of the same road by several trips/vehicles are resampled together.

## 3. Parametric simulation (controlled experiments)

* Speed invariance: fixed held-out profiles traversed at 20, 40, 60, 80, 100, 110 km/h by held-out vehicle
  parameter sets. A model is called "speed-invariant over [40, 100] km/h" only if the mean relative change of
  its prediction between 40 and 100 km/h lies inside +-10 % with its 95 % CI (bootstrap over profiles)
  entirely inside +-10 %.
* Unseen vehicles: (a) random split of vehicle parameter sets (interpolation); (b) parameter-region split
  (train body-bounce frequency f_s <= 1.25 Hz, test f_s > 1.25 Hz; extrapolation). A model is said to
  generalise to unseen vehicles only if the unseen-vehicle MAE is within 10 % of the seen-vehicle MAE
  (relative) with the 95 % CI of the difference excluding a larger degradation.
* Robustness: perturbations applied to test inputs only (sampling rate, noise, quantisation, orientation
  error, speed error, missing samples, mount compliance); reported as degradation curves; no claim
  thresholds, descriptive only.

## 4. PVS (ordinal, no IRI)

* Labels are surface type and subjective quality; no absolute IRI claim is made from PVS.
* Leave-one-route-out over the 3 PVS routes (trips {1,4,7}, {2,5,8}, {3,6,9}); logistic models on feature
  sets {speed}, {RMS}, {RMS/sqrt(v)}, {model}, {model+speed}, {model+RMS}, {model+speed+RMS};
  AUC with 95 % CIs from a cluster bootstrap over 100 m GPS cells.

## 5. What is never done

* Choosing seeds, folds, thresholds or feature sets after looking at test metrics.
* Reporting the best seed. Seeds are averaged; all are listed in result files.
* Describing any simulation result as real-world validation.
