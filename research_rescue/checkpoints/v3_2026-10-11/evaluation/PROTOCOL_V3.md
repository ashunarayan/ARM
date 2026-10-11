# Evaluation protocol, revision 3 (frozen 2026-10-10, before any v3 analysis was run)

Response to `INDEPENDENT_REVIEW_V3.md`. This document extends `FINAL_EVALUATION_PROTOCOL.md` (v1) and
`PROTOCOL_V2.md` (v2, including its addenda E5-E10). Nothing in v1 or v2 is changed except the bug fix of item V3-8,
whose before/after values are both reported.

## 0. Status of the evidence

The reviewer has already run several of the analyses below on the same data (`review/v3_checks/`): the pooled arm
for V0, V1, V3 and V5 at k = 5, 10 and 20 km (check c4), the band-limited retraining for V0-V8 (c8), the paired
ranking test (c3), the speed-robustness rows (c6) and the no-simulator comparator (c2). Their outcomes are known to
us. No v3 analysis is therefore confirmatory. Classes, as in `PROTOCOL_V2.md`:

* **R** - design specified in an earlier protocol, now evaluated on routes whose results are known (V3-1, V3-5, V3-8).
* **E** - diagnostic analysis specified here (all other items).

Rules (unchanged from v2): no variant, draw, k, feature set or subset is chosen after seeing its result; every
variant and every draw is reported; nothing from a test route enters training, calibration, model selection or
preprocessing; claims rest on the range over all variants, not the best one.

## 1. Unchanged

Leave-one-route-out over CPH1, CPH6, M3, M13 (both directions of the test route held out); IRI labels from the P79
profiles; features and preprocessing; LightGBM configurations (inner leave-one-route-out selection only for the
full real-data model M3, first configuration otherwise); simulator variant datasets V0-V10 as generated in v2; the
calibration-block sampler (`sample_blocks`, contiguous 1 km blocks of the training routes,
`numpy.random.default_rng(1000 * d + 7)`, draws d = 0..19) shared by all arms so that draws are paired; the 5 km-block
cluster bootstrap as the decision rule for differences between estimators; route-level intervals descriptive only.

Metric definitions used throughout v3:
* *Pooled MAE*: segment MAE over all 1,678 segments of the four held-out routes (n_seg-weighted mean of the
  per-route MAEs). Primary for the value-of-simulation analyses, as in v2 (R4).
* *Within-route MAE*: mean over the four held-out routes of the per-route segment MAE (v2 primary for Table I).
* *Level* of an estimator on a route: mean over the route's segments of log(prediction / label) (v2 R3 estimand).
* *k km of paired drives*: k contiguous 1 km blocks of training-route road with all real passes over them; the pass
  density is reported (segment-passes per segment).

## 2. Items

### V3-1 (R) Pooled simulation + real training ("sim_real_pooled")
* *Question.* Does the paired-data requirement depend on simulator fidelity when simulated and real passes are
  trained jointly, rather than combined through a level offset or affine map?
* *Origin.* v1 protocol §1 ("real-only vs. simulation-pretrained + real fine-tuned"); implemented in v1 for LightGBM as
  `sim+real LightGBM (balanced weights)` (`experiments/exp_lira.py`, `part_fewshot`) and omitted in v2.
* *Design.* For held-out route R, variant v, k km and draw d: LightGBM (first configuration) trained on the union of
  the variant's simulated units of the training routes (`variant_training_set(v, R)`) and the real units of the k km
  (same blocks as all other arms), with weight 1 for each simulated unit and n_sim / n_real for each real unit (equal
  total weight), exactly as in v1; it predicts all units of R. Variants V0-V8 and V10; k in {1, 2, 5, 10, 20};
  d = 0..19; 4 folds (4,000 rows).
* *Comparators (same draws).* real-only LightGBM (R4), real-only index (E9), simulation + level offset and + affine
  map (R3).
* *Metrics.* pooled MAE (primary), within-route MAE, pooled bias; mean paired difference to each comparator and the
  number of the 20 draws in which the pooled arm is better; per held-out route.
* *Hypothesis H1 (from the review).* With joint training, the advantage over real-only training no longer depends on
  the variant: for every variant the pooled arm is better than real-only LightGBM on average at k <= 10 km and not
  worse by more than 0.02 m/km at 20 km.
* *Decision rule for the wording.* The pooled arm is said to beat real-only training for a variant at a given k if
  the mean difference is negative and it is better in at least 15 of 20 draws; "within +-0.02 m/km" otherwise if
  applicable. The variant dependence is summarised by the range over V0-V8 of the pooled MAE at each k, next to the
  same range for the level-offset arm.
* *Reproduction check.* V0, V1, V3, V5 at k = 5, 10, 20 must match `review/v3_checks/outputs/c4b_compare.txt` within
  +-0.002 m/km; otherwise the discrepancy is investigated before anything is reported.

### V3-2 (E) Test-route uncertainty of the calibration comparison
For k in {5, 20}, arms sim_all_cal and sim_real_pooled (V0-V8) against real-only LightGBM: per draw, segment absolute
errors (segment mean of pass predictions); per segment, the mean over the 20 draws of the difference arm minus
real-only; pooled estimate = mean over segments; 95 % interval from a 5 km-block bootstrap of test segments
(B = 2000, seed 3003). Route-level per-route means are reported descriptively. The interval conditions on the 20
calibration draws and describes these four routes.

### V3-3 (E) Band-limited zero-shot intervention
* *Question.* Do the level differences between sensor variants act through simulated energy above 10 Hz?
* *Design.* Zero-shot LightGBM (first configuration) retrained for V0-V8 on three fixed feature sets:
  `full` (all 13 features); `no1015` (all but `log_band_10_15`); `lt10` (`log_v_mean`, `v_cv`, `log_band_0.5_2`,
  `log_band_2_5`, `log_band_5_10`: no feature with content above 10 Hz). Evaluated on the held-out routes; level
  offset from 5 km (20 draws) as in R3.
* *Metrics.* pooled MAE and bias; urban, motorway and mean log level; within-route Spearman; pooled MAE after the 5 km
  level offset.
* *Primary quantity.* spread (max - min) over the eight sensor variants (V0-V3, V5-V8) of the mean log level and of
  the urban and motorway log levels; V4 (one vehicle, V0 sensor mixture) reported separately.
* *Hypothesis H3.* The sensor-path level differences act through features carrying energy above 10 Hz: under `lt10`
  the spread of the mean log level and of both class levels is at most half of that under `full`, while dropping only
  the 10-15 Hz band feature changes the spreads by less than 20 %. *H3b.* V4's level offset, which comes from the
  vehicle population, persists under `lt10` (V4 outside the range of the eight sensor variants).
* *Reproduction check.* `full` reproduces the zero-shot MAEs of `summary_variants.csv` to three decimals.
* *Interpretation limits.* `lt10` removes eight features, including broadband ones that also carry energy below
  10 Hz; the test is model-level (which inputs carry the variant differences), not a physical demonstration.

### V3-4 (E) Band associations, all bands
Spearman and Pearson correlations, and R^2 of a linear fit, over V0-V8 between the zero-shot pooled bias and the log
real/simulated amplitude ratio of each of the five features in `band_gain.csv` (0.5-2, 2-5, 5-10, 10-15 Hz, overall
RMS); the same against the mean log level. All are reported.

### V3-5 (R) Level decomposition
Per variant (V0-V10, real-trained): urban, motorway and mean log level and the motorway-minus-urban spread, from the
`level_*` columns of `variants_zeroshot.csv` (v2 R3 estimand). Spearman over V0-V8 of the spread with the pooled MAE
after a 5 km level offset.

### V3-6 (E) Paired test of within-route ranking
Per route, Spearman and partial Spearman (given segment speed) of real-trained LightGBM, V0- and V1-trained LightGBM
minus those of the untrained statistic RMS/v^0.5 (segment means); mean over routes; 95 % intervals from 5 km blocks
resampled within each route (B = 2000, seed 2026). The wording on ranking follows the per-route differences.

### V3-7 (E) Robustness of the fixed-road speed elasticities
For raw log RMS, real-trained LightGBM, V0-trained LightGBM and their difference, by road class: (a) the v2 design;
(b) plus telematics-unit fixed effects (point estimate); (c) plus the log within-pass speed SD as a covariate (5 km-
block interval, B = 1000, seed 5); (d) plus the speed coefficient of variation as a covariate, reported with the
caveat that it is mechanically tied to 1/v. Also the within-segment correlation of log speed with log speed SD.

### V3-8 (bug fix) M7 segment grid
`physics_inversion.py` builds road-spectrum segments at multiples of 100 m along each P79 run, which misses the
M13-VH segments (starts at ...60 m), so M7 was evaluated on 119 of 228 M13 segments. Fix: build the segment windows
from the segment starts of the real units of each route-direction. Rerun M7 and the summaries; report the old and the
new M13 values.

### V3-9 (E) No-simulator comparator
On the same draws, log IRI = c + b log(RMS / v^alpha) calibrated on the k km of real passes (k in {1, 2, 5, 10, 20}):
alpha = alpha_car, the label-free within-segment speed exponent of the car's raw RMS on the training routes, with an
affine fit; and alpha = 0.5 with a level offset and with an affine fit. Question: does the simulation contribute more
than a speed exponent and a slope?

### V3-10 (E) Pass density of the calibration data
At k = 5 km, each segment of the k km keeps at most m of its real passes (m in {1, 2, 5}; random, seeded by
`default_rng(100000 + 1000 * d + m)`, independent of labels); arms real-only LightGBM, simulation + level offset
(V0-V8) and pooled (V0-V8), paired by draw. Question: is the ~10-pass density of LiRA-CD needed for the calibration?

### V3-11 (E) Relative errors per road class
MAE divided by the mean IRI of the class, per estimator of Table I (supplement).

## 3. Non-experimental items

Literature additions are verified against Crossref metadata and abstracts (and full text where a specific method or
split is attributed); dataset facts are taken from the LiRA-CD data article and the dataset readme files.

## 4. Deviations

Any change to the items above after a result is seen is recorded here with its reason; the original analysis is
reported next to the changed one.
