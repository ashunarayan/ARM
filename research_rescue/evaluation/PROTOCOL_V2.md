# Evaluation protocol, revision 2 (frozen before any v2 experiment was run)

Frozen: 2026-10-03, after reading the independent review (`review/first.md`) and after running only
`experiments/v2/verify_review_claims.py`, which re-reads existing result files and fits no model.
This document extends `FINAL_EVALUATION_PROTOCOL.md` (v1, frozen 2026-10-02). Nothing in v1 is changed.

## 0. Status of the evidence and what may be claimed

All four LiRA-CD routes have been used as test routes in v1 and their results, together with the reviewer's
re-analyses of them, are known. There is no untouched real test set. Consequently:

| Class | Meaning | May support |
|---|---|---|
| **C1** confirmatory (v1) | specified before any test result (v1 protocol); numbers unchanged | confirmatory statements about the pre-specified configurations |
| **R** pre-specified re-analysis (v2) | estimand and procedure fixed in this document before running; computed on the already-seen routes; reported in full whatever the outcome | descriptive statements, explicitly labelled as post-review analyses |
| **E** exploratory diagnostic (v2) | mechanism analyses (sensor variants, spectra) | explanations and hypotheses only; **never** used to choose a configuration for a headline |
| **S** controlled simulation (v2) | new simulated test sets generated after this freeze; design fixed here | confirmatory statements about the simulator only |

Rules that follow:
1. No simulator configuration is promoted to "primary" because of v2 results. The v1 measured-profile set
   (`p79`, primary 50/50 sensor mixture, 30 vehicles) stays the reference simulator. (The v1 protocol named no
   primary simulation set; the study plan framed RQ5 around measured profiles, hence `p79`. The `p79+iso` set used
   for the v1 CNN and few-shot runs is always reported next to it.)
2. Any statement about "simulation plus calibration" is based on the **range over all variants listed in
   Section 3**, never on the best variant.
3. Calibration, model selection and any fitted correction use only data of the training routes of each fold.
4. Every analysis listed here is reported, including unfavourable outcomes; nothing is dropped after running.
5. If an analysis turns out to be infeasible or buggy, the reason is logged in `CHANGELOG.md`; bug fixes may not
   depend on the outcome.

## 1. Unchanged (frozen in v1)

Units (100 m segment x pass), labels (MRI recomputed from the P79 profiles), outer leave-one-route-out folds,
segment-level aggregation (mean of pass predictions), metrics (MAE primary; RMSE, bias, Spearman, kappa on FHWA
bands), shared preprocessing (`common/preprocess.py`), features (`common/features.py`), model configurations
(`config/models.json`), the few-shot block sampler (contiguous 1 km blocks of one route-direction,
`numpy.random.default_rng(1000*d + 7)` for draw d), and LightGBM's first configuration whenever no inner validation
on real training routes is available (zero- and few-shot).

## 2. Inference (revised in the conservative direction)

* **Dependence.** Residual autocorrelation of segment errors is reported as a function of lag (100 m to 5 km) for
  the real-trained and the simulation-trained LightGBM.
* **Paired comparisons** (model A vs model B on the same segments): cluster bootstrap (B = 2000, paired resamples,
  Holm within each family) with three cluster definitions: segment, 1 km block, 5 km block (block id =
  route-direction + floor(start_m / L)). A difference is called *supported* only if the **5 km-block** 95 % interval
  excludes zero (40 clusters); segment- and 1 km-level intervals are reported alongside.
* **Route level.** Every headline quantity is shown per held-out route. For paired differences a route-level
  interval (mean of the 4 route-level differences, t distribution with 3 df) is reported as descriptive; with
  n = 4 no route-level inferential claim is made.
* **Within-route metrics** (MAE, Spearman and partial Spearman given segment mean speed, computed per route and
  averaged over routes) are the primary skill measures in the revised paper; pooled metrics are secondary.
* **Variance components.** Seed (neural nets: SD over the 5 seeds), segment sampling (bootstrap), route (per-route
  values), vehicle unit (pass-level log errors decomposed into segment effects and telematics-unit effects by
  two-way least squares; SD of unit effects with a pass-level bootstrap).

## 3. Simulator variant matrix (fixed list; class E for the explanation, R for the calibration results)

All variants: measured P79 profiles of the three training routes of each fold (never the test route), the 30 v1
training vehicles unless stated, the v1 speed model, zero-shot LightGBM (first configuration) and vibration index
(alpha fitted in simulation).

| id | sensor / vehicles | data |
|---|---|---|
| V0 | primary 50/50 mixture: telematics-like (55-62 Hz, rigid) + phone-like (90-210 Hz, holder resonance 15-40 Hz) | `p79_train` (v1) |
| V1 | telematics-like half of V0 only | subset of `p79_train` |
| V2 | phone-like half of V0 only | subset of `p79_train` |
| V3 | ideal sensor (100 Hz, no noise, quantisation, tilt, bias, loss) | `p79_train_idealsensor` (v1) |
| V4 | one mid-range vehicle, V0 sensor mixture | `p79_train_fixedvehicle` (v1) |
| V5 | single telematics sensor matched to measured LiRA-CD statistics | `p79_train_measuredsensor` (v1 post-hoc) |
| V6 | matched telematics half + phone-like half | `p79_train_measuredmix` (v1 post-hoc) |
| V7 | telematics-like sensor **with** the phone-like holder resonance (15-40 Hz, zeta 0.05-0.2) | new: `p79_train_telecompliant` |
| V8 | phone-like sensor **without** holder resonance (rigid) | new: `p79_train_phonerigid` |
| V9 | synthetic ISO-type profiles only, V0 sensor mixture | `iso_train` (v1) |
| V10 | measured + synthetic profiles | `p79_train` + `iso_train` (v1) |

V7 and V8 complete a 2 x 2 factorial (sensor family x holder resonance) with V1 and V2; they are generated with
their own random streams (seeds 41001 and 41002) and the 30 v1 training vehicles. Because V1 and V2 are halves of V0,
V7 and V8 enter the factorial as a random half of their passes (pass-level subsample, seed 7); the full sets are
reported as well.

## 4. Pre-specified re-analyses on LiRA-CD (class R)

* **R1 Map-only road-class prior:** each held-out route predicted by the median IRI of the other route of the same
  class (CPH1<->CPH6, M3<->M13).
* **R2 Unit-disjoint real baseline:** for held-out route R, train LightGBM (inner leave-one-route-out selection, as
  M3) only on passes of telematics units that never drive R; size-matched control: random subsets of the same number
  of training units from all units (5 draws). Folds whose unit-disjoint training set lacks a road class are reported
  but flagged.
* **R3 Shape/level decomposition** for every variant V0-V10, the real-trained LightGBM and the BeamNG-trained
  models: within-route Spearman; scale b = slope of segment-level log(prediction) on log(IRI) with route fixed
  effects; level = mean log(prediction/IRI) per route; then calibration with k in {1, 2, 5, 10, 20} km of real
  training-route data (20 draws, blocks by the v1 sampler with d = 0..19): (a) intercept only: median over the
  calibration passes of log((y + 0.001)/(p + 0.001)); (b) affine: OLS of log(y) on segment-mean log(p) over the
  calibration segments. Reported: pooled and per-class segment MAE, mean and 2.5-97.5 % range over draws.
* **R4 Equal profile budget.** For k in {1, 2, 5, 10, 20, 40} km and 20 draws (same blocks for all arms):
  (i) real-only LightGBM on the k km of real passes; (ii) simulation-only LightGBM on V0 units of the same k km of
  profiles; (iii) (ii) + intercept calibration on the same k km of real passes; reference lines: V0 on all
  training-route profiles, with and without calibration on k km. Reported as learning curves (mean, 2.5-97.5 %
  range over draws) and paired differences (ii)-(i) per k.
* **R5 Speed on real data.** (a) Within-segment speed elasticity: OLS of pass-level log(prediction) on log(pass mean
  speed) with segment fixed effects, segments with >= 3 passes, per road class and pooled; 95 % CI by 1 km-block
  bootstrap. Estimators: real-trained LightGBM (with/without speed), vibration indices, raw log RMS (physical speed
  exponent of the car), speed-only, V0-V10. Reading: a roughness estimator has elasticity 0; the +-10 % criterion
  of v1 between 40 and 100 km/h corresponds to |elasticity| <= ln(1.1)/ln(2.5) = 0.104. (b) Between-segment
  elasticity with route fixed effects and log(IRI) as covariate (reviewer's design), reported for comparison.
  (c) Within-route MAE and Spearman by pass-speed tercile.
* **R6 Block-level paired tests** (Section 2) for: V0 vs real LightGBM; V10 vs real LightGBM; CNN (per-seed mean and
  5-seed ensemble) vs LightGBM; MLP vs LightGBM; speed-only vs LightGBM; map prior vs speed-only; fitted index vs
  LightGBM.
* **R7 Anchor to Bajic et al. (2021):** within-route spatial holdout on M3 (each direction: first 80 % of the
  chainage for training, last 20 % for testing), LightGBM, MLP, fitted index and the training-mean baseline;
  segment-level MAE, RMSE, R^2. Reported in the supplement as an approximate anchor (different reference device and
  windowing in the original study).
* **R8 Passes needed** on a fixed segment set: segments with >= 8 passes; n in {1, 2, 3, 5, 8} random passes,
  20 repetitions.
* **R9 ARAN9000 alignment:** heading-constrained matching using the ARAN heading column, records with zero IRI
  excluded; agreement with the P79 per route.
* **R10 Calibrated physics inversion baseline (M7):** quarter-car (normalised parameters K1, K2, C, U) plus sensor
  gain fitted to the empirical acceleration/road transmissibility of the training routes; road displacement
  spectrum of each test unit obtained by spectral division; IRI from the Golden-Car response to that spectrum
  (Gaussian rectification); reported uncalibrated and with a log-linear correction fitted on the training routes.
  The spectral IRI formula is first checked against the validated IRI on the P79 profiles themselves. Exact
  reproduction of Skar & Levenberg (2024) is not possible (calibrated vehicle parameters not published); M7 is
  labelled "in the spirit of".

## 5. Diagnostics (class E)

* **E1** zero-shot results of V0-V10 (MAE, bias, per class).
* **E2** factorial reading of V1, V2, V7, V8: effect of the holder resonance and of the sensor family on bias.
* **E3** spectra: Welch PSD (50 Hz signal after the shared preprocessing, 2.56 s windows) per unit for real passes
  and for re-simulated passes of V1, V2, V7, V8 over the same P79 profiles; mean log-PSD difference real - sim on
  cells (segment x 10 km/h speed band) present in both, by frequency, with 1 km-block bootstrap CIs. Aliasing check:
  for the one telematics unit that logged at both 52.6 Hz and 333 Hz (TMU#10), log-PSD difference between the two
  rates on common cells; spectrum above 25 Hz from the 333 Hz passes.
* **E4** band-level gain/offset: segment-matched regression of real on simulated log band RMS.

## 6. Controlled simulation (class S)

* **S1 Number of training vehicles.** New vehicle pool (seed 20261003): 300 training and 30 test parameter sets
  from the documented ranges; synthetic training routes and held-out synthetic test routes as in v1
  (`iso_routes(rng(1), 40, "isotr")`, `iso_routes(rng(2), 15, "isote")`); V0 sensor mixture. For
  N in {3, 10, 30, 100, 300} training vehicles, 1,200 training passes in total (vehicles assigned round-robin), so
  the amount of data is constant. Test: the 30 unseen vehicles (unseen-vehicle MAE) and min(N, 30) training vehicles
  (seen-vehicle MAE) on the held-out routes, 2 passes each. LightGBM and the fitted index. v1 criterion (relative
  increase <= 10 %, upper CI) applied unchanged; absolute unseen MAE vs N reported. For N = 30, per-vehicle MAE vs
  standardised parameter distance to the nearest training vehicle (Spearman).

## 7. Never done

Choosing a variant, block size, k, draw, seed or subset after seeing its result; adopting the phone-like-only
variant (or any other) as the primary simulator; describing any v2 real-data analysis as confirmatory.

## 8. Addenda written after some v2 results were known (class E; reported in full, never used to choose anything)

* **E5 (added 2026-10-03, after the V0 results of R4 were known).** The equal-budget conclusion of R4 rests on V0,
  whose zero-shot level happens to be close to the real one. To check whether it depends on that, the arms
  `sim_same` and `sim_same_cal` of R4 are repeated for every measured-profile variant V1-V8 (variant training sets
  exactly as in E1, restricted to the same k km of blocks; same draws d = 0..19 and sampler as R4, so `real_only`
  of R4 is the paired comparator). V9 and V10 are excluded because their synthetic profiles are not part of the
  k km budget. All variants are reported.
* **E6 (added 2026-10-03).** Paired per-draw comparison of `sim_all_cal` of every variant (R3 calibration files) with
  `real_only` of R4 at the same k: mean difference of the pooled segment MAE, 2.5-97.5 % range over draws and the
  number of draws in which the calibrated simulation is better. Uses existing predictions only.
* **E7 (added 2026-10-03, after R6 was known).** Speed scaling of the raw vibration in simulation vs reality: the
  within-segment elasticity of log RMS on log speed (segment fixed effects, as R6) for the real units and for the
  simulated units of each measured-profile variant V0-V8 on the same segments, restricted to simulated passes whose
  speed lies within the range of the real passes over that segment; by road class; 5 km-block bootstrap (2000).
  Purpose: to tell whether the low speed dependence of simulation-trained estimators reflects a simulator that
  reproduces the real car's speed response. Diagnostic only.
* **E8 (added 2026-10-03, after R6 was known).** Paired difference of within-segment elasticities, simulation-trained
  minus real-trained estimator, on the same passes: slope of log(p_sim / p_real) on log speed with segment fixed
  effects, 5 km-block bootstrap (the inference rule of Section 2); every simulator variant, LightGBM and index.
* **E9 (added 2026-10-03, after R4/E5/E6 were known).** Fairness check of the real-only comparator: with 1-5 km of
  paired data a three-parameter vibration index (M2c) may suit the small sample better than LightGBM. The index is
  fitted on the real passes over the same k km (same draws and sampler as R4) and every simulation arm is also
  compared with it, draw by draw. Reported in full; not used to choose anything.
* **E10 (added 2026-10-03, during the final self-review).** How much of the within-route ranking needs no learning:
  within-route Spearman and partial Spearman (given segment speed) of fixed, untrained vibration statistics (raw RMS,
  RMS/v^0.5, RMS/v), computed exactly like those of the estimators (segment means of pass values). Spearman within a
  route is invariant to any monotone calibration, so these statistics need no training data.
