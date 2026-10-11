
# Adversarial review: "How Far Can Simulation Take Vehicle-Based IRI Estimation?" (research_rescue/)

**Bottom line:** I found no leakage and no fatal flaw, and the headline numbers reproduce exactly. But the paper's explanation of its one positive result is contradicted by its own data. The "replaces ~20 km of labelled road" claim also comes from an unequal comparison. Conference **4/7** (borderline), journal **3/7** (major revision). Both problems can be fixed with data you already have. Generalising beyond one car on four routes cannot.

**What I did.** I read the paper, supplement, all audit documents and the core code (simulator, sensor model, preprocessing, features, models, statistics, experiment drivers). I traced every headline number to its result file. I also ran six independent analyses on your existing data without changing any repository file. The scripts (`rev_a`–`rev_f.py`) are in the session scratchpad: `C:/Users/nishk/AppData/Local/Temp/claude/d--Coding-Hackathon-GFG-ARM-ARM/7f41980c-…/scratchpad/`. Two of those analyses change how the paper's central result has to be read.

---

## 0. What the paper actually does

| Item                        | Reconstruction                                                                                                                                                                                                                                                                                     |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Research question           | When labels are valid and evaluation is route-disjoint on real cars, how much of the accuracy and properties claimed for simulation-trained IRI estimators survives? Can simulated responses replace real labelled car data?                                                                       |
| Hypotheses                  | H1–H3 are directional (label correction invalid; earlier result depends on test calibration and filtering; speed explains apparent skill). RQ4 and RQ5 have no direction. Two criteria were fixed in advance: speed invariance within ±10 %, and an unseen-vehicle MAE increase of at most 10 %. |
| Methodological contribution | No new estimator. The new parts are an evaluation protocol and a simulation pipeline built from standard parts: a linear 4-DOF half-car, a sensor model, domain randomisation, LightGBM on hand-crafted features.                                                                                  |
| Empirical contribution      | A model comparison on LiRA-CD (M0–M6); zero-shot and few-shot sim→real; controlled simulation tests; a post-mortem of the authors' earlier BeamNG pipeline.                                                                                                                                      |
| Real data                   | LiRA-CD: 4 routes (2 urban, 2 motorway), Renault Zoe cars, AutoPi telematics unit, P79 profiles.                                                                                                                                                                                                   |
| Simulated data              | Half-car driven over P79 profiles of the 3 training routes, or over ISO-8608-type synthetic profiles; 30 training vehicles; 50/50 mixture of a telematics-like and a phone-like sensor.                                                                                                            |
| Ground truth                | IRI recomputed from the P79 laser profiles (mean of both wheel paths, per 100 m). It is checked against the P79's own IRI, which is an algorithm check because both come from the same profiles.                                                                                                   |
| Independent unit            | Claimed: the 100 m segment. In practice: 1–5 km blocks within routes. For generalisation claims: the route (n = 4, i.e. 2 per road class).                                                                                                                                                        |
| Splits                      | Leave-one-route-out (both directions held out together). Model selection by inner leave-one-route-out on the training routes. Neural-net early stopping on a grouped 20 % of training segments.                                                                                                    |
| Positive results            | Label correction is not IRI; real-trained LightGBM 0.42; sim-only 0.44; vibration carries roughness information within routes.                                                                                                                                                                     |
| Negative results            | BeamNG does not transfer; unseen-vehicle criterion not met; speed correction learned on synthetic roads fails on measured profiles; CNN is not the best model.                                                                                                                                     |

---

## 1. Headline results traced to artifacts

| Paper claim                           | Artifact                                           | Verified?                                         | Reviewer note                                                                                                                                                                                          |
| ------------------------------------- | -------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| LightGBM 0.42 [0.39, 0.45]            | `results/lira/ladder_segment_metrics.csv`        | Yes (0.420)                                       | The CI treats spatially autocorrelated segments as independent. The 1 km-block CI is [0.36, 0.48].                                                                                                     |
| MLP 0.42, p = 0.458                   | same                                               | Yes (0.425)                                       |                                                                                                                                                                                                        |
| CNN 0.48                              | same                                               | Yes (0.475)                                       | Mean of per-seed MAEs; the 5-seed ensemble gets 0.465. The deficit comes from one route (CPH1 +0.14; other routes −0.02 to +0.02).                                                                    |
| Speed-only 0.74                       | same                                               | Yes                                               |                                                                                                                                                                                                        |
| Sim → real 0.44                      | `zeroshot_segment_metrics.csv`                   | **Reproduced exactly** (0.439, bias +0.010) | See §5: the primary sensor mixture is the only variant with near-zero bias.                                                                                                                           |
| BeamNG → real 1.36                   | same                                               | Yes                                               | The BeamNG-trained vibration index gets**0.85, ρ = 0.93**. Only the LightGBM is quoted.                                                                                                         |
| "About 20 km"                         | `fewshot_raw.csv`                                | Number yes, wording no                            | Real-only at 20 km: 0.456 (range 0.430–0.489). It is compared with**sim p79+iso, 0.459**, not the abstract's 0.44 model. Real-only at 10 km: 0.499. I reproduced 0.822 / 0.499 / 0.456 exactly. |
| Sensor-rate fix: 0.44 → 0.46         | `zeroshot_sensor_segment_metrics.csv`            | Yes (0.455)                                       | Uninformative: the phone half carries the result (§5).                                                                                                                                                |
| Single matched sensor 0.69            | same                                               | Yes (0.687)                                       | Matches my telematics-half-only run (0.678).                                                                                                                                                           |
| Unseen vehicles +19 % (upper CI 24 %) | `results/sim/unseen_vehicle_paired.csv`          | Yes                                               | In-distribution held-out draws, 30 training vehicles (§8).                                                                                                                                            |
| CIs                                   | [stats.py](research_rescue/common/stats.py#L54-L98) | Correctly implemented                             | Wrong resampling unit (§9).                                                                                                                                                                           |

**Chronology.** File timestamps are consistent with the claims: protocol 18:24, simulated data 18:46, LiRA dataset 19:08, first zero-shot metrics 19:33, model-ladder metrics 19:44. The simulator was fixed before any LiRA label was scored. This is self-attested on uncommitted files.

---

## 2. Dataset and ground truth

| Quantity                                        | Count                                                                                                      |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Segment-passes (the "windows")                  | **16,293**                                                                                           |
| Distinct 100 m segments                         | **1,678** (168 km)                                                                                   |
| 1 km blocks / 5 km blocks                       | 172 / 40                                                                                                   |
| Route-directions / routes                       | 8 /**4** (2 urban, 2 motorway)                                                                       |
| Passes / trips                                  | 91 / 37 (CPH6 has only 12 passes)                                                                          |
| Vehicles                                        | 1 model; ≥ 8 telematics units,**shared across routes** (TMU#10, #11 and #14 drive CPH1, M3 and M13) |
| Sensor types                                    | 1 (AutoPi; nominal rate 52.6 Hz in 66 % of passes, else 333 Hz)                                            |
| Passes per segment                              | median 10 (2–15)                                                                                          |
| Lag-100 m autocorrelation of LightGBM residuals | **0.25–0.56** within each route-direction (my check)                                                |

- **Effective sample size.** Accuracy *within* these roads is estimated from about 1,678 correlated segments, closer to about 172 independent blocks. Generalisation *across* roads rests on two routes per road class. The paper says this in Limitations, but its intervals and p-values still describe segments.
- **Labels.** IRI per 100 m from the P79 profile, aligned by GPS map matching (1–3.4 Hz GPS, lateral distance < 20 m). Survey dates differ from car-pass dates. This adds label noise but no leakage.
- **"Route-disjoint" is not "vehicle-disjoint".** The real-trained baseline sees the same physical cars in training and test; the simulation-trained model does not. This favours the real baseline. It is not disclosed explicitly.

---

## 3. Leakage audit

| #  | Type                            | Present?                                      | Evidence                                                                                                                                                                                           | Affects headline?                                                                                                                                                                                                                     |
| -- | ------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Road overlap                    | Negligible                                    | 7 of 1,678 segments within 15 m of another route (`route_overlap.json`)                                                                                                                          | No                                                                                                                                                                                                                                    |
| 2  | Route overlap                   | No                                            | Leave-one-route-out, both directions held out together ([exp_lira.py:126](research_rescue/experiments/exp_lira.py#L126))                                                                            | No                                                                                                                                                                                                                                    |
| 3  | Repeated passes                 | No                                            | All passes of a test segment are in test; predictions aggregated per segment                                                                                                                       | No                                                                                                                                                                                                                                    |
| 4  | Vehicle overlap                 | **Yes, by design (real baseline only)** | Same telematics units in train and test routes                                                                                                                                                     | Favours the real baseline; no inflation of the sim result                                                                                                                                                                             |
| 5  | Sensor overlap                  | Yes, by design                                | One device type                                                                                                                                                                                    | Limits generality; not leakage                                                                                                                                                                                                        |
| 6  | Temporal overlap                | No                                            | Surveys and passes on different dates                                                                                                                                                              | Label noise only                                                                                                                                                                                                                      |
| 7  | Overlapping windows             | No                                            | Test units are non-overlapping; simulated units are too                                                                                                                                            | No                                                                                                                                                                                                                                    |
| 8  | Normalisation                   | No                                            | Neural-net normalisation fitted on training data only ([models.py:172](research_rescue/common/models.py#L172-L177))                                                                                 | No                                                                                                                                                                                                                                    |
| 9  | Hyper-parameters                | No                                            | Inner leave-one-route-out over a 6-configuration grid                                                                                                                                              | No                                                                                                                                                                                                                                    |
| 10 | Calibration                     | No                                            | No test calibration, no capping                                                                                                                                                                    | No                                                                                                                                                                                                                                    |
| 11 | Feature engineering             | Not detectable                                | `features.py` written at 18:13, before any LiRA label was used                                                                                                                                   | No                                                                                                                                                                                                                                    |
| 12 | Thresholds                      | No                                            | FHWA bands fixed a priori                                                                                                                                                                          | No                                                                                                                                                                                                                                    |
| 13 | Test-set model selection        | **Mild**                                | The protocol named no primary simulation set. CNN compute and the few-shot runs used p79+iso, which suggests it was the planned main set; the abstract headlines the best set (p79, 0.44 vs 0.46). | ~0.02 m/km                                                                                                                                                                                                                            |
| 14 | Post-hoc experiments            | Disclosed                                     | Sensor analysis and the speed sweep on measured profiles are labelled post-hoc                                                                                                                     | The*interpretation* of the post-hoc sensor result is wrong (§5)                                                                                                                                                                    |
| 15 | Simulator tuned on test results | **Not found**                           | Simulated data produced before any LiRA metric existed; simulator unchanged afterwards                                                                                                             | No.**Warning:** there is no untouched test set. Leave-one-route-out uses all four routes as test, so any simulator change made from now on against these numbers (including adopting my phone-only finding) is test-set tuning. |

**Verdict: no leakage that inflates a headline number.** This is the paper's strongest asset.

---

## 4. Baseline fairness

- **Same inputs for everyone.** Features, preprocessing, log target, splits and test units are identical across models. LightGBM gets a 6-configuration inner search; the neural nets get fixed configurations with 5 seeds. That is fair enough.
- **CNN comparison.** The CNN is the legacy architecture with legacy hyper-parameters, reported as a per-seed mean rather than an ensemble (0.475 vs 0.465), and its deficit sits on one route. "CNN is worse" is true on this data but not robust across routes. The CNN result is not important to the contribution (§14 B).
- **Missing baselines that matter:**
  1. **Map-only road-class prior.** Predicting each held-out route with the median of the other same-class route needs only a map and gives **0.81 m/km**. Speed-only (0.74) is essentially this. The paper never states that speed-only is a road-class proxy *numerically*.
  2. **A calibrated physics inversion on the same cars:** Skar & Levenberg 2024 (§11). This is the natural non-learning competitor and is absent.
- **Is the proposed approach better than a well-tuned simple model?** There is no proposed estimator. LightGBM *is* the simple model and it wins. The contribution has to be the evaluation and the simulation evidence, which the paper partly recognises.

---

## 5. Simulation validity and the sim-to-real claim (central section)

**What the simulator reproduces.** Within-route ranking. Every estimator, including raw RMS and the synthetic-profile simulator, ranks segments within a route about equally well (partial Spearman given speed: LightGBM real 0.84 / 0.80 / 0.70 / 0.90; sim[iso] 0.83 / 0.79 / 0.71 / 0.90; raw RMS 0.79 / 0.75 / 0.73 / 0.91). It also learns a speed correction that is *less* confounded than the real-trained one (below).

**What it does not reproduce.**

- **Vibration level:** real vibration is ×1.23 the simulated level on matched segments.
- **IRI elasticity** of log RMS: 0.93 in simulation vs 0.65 real.
- **Speed exponent:** 1.20 in simulation vs 0.60–0.79 real.
- **Roll:** none; the half-car is driven by the mean of the two wheel paths.
- **Non-linearity:** none, and there are no structural or powertrain modes.
- **Sensor rates:** the telematics rates were set from an inaccurate preliminary inspection.

**Decisive check (new, existing data).** Split the primary simulation set by sensor half and retrain the same zero-shot LightGBM:

| Training data (P79 profiles, 30 vehicles)          | Zero-shot MAE   | Bias          | Motorway MAE |
| -------------------------------------------------- | --------------- | ------------- | ------------ |
| Mixture (paper's primary)                          | 0.439           | +0.01         | 0.197        |
| **Phone-like half only**                     | **0.409** | −0.09        | 0.139        |
| Telematics half only                               | 0.678           | +0.43         | 0.558        |
| (paper, post-hoc) Single matched telematics sensor | 0.687           | +0.40         | —           |
| (paper) Ideal sensor / fixed vehicle               | 0.666 / 0.626   | +0.40 / +0.40 | —           |

On matched segments at 60–100 km/h, simulated telematics vibration is **×1.40 below** real and the phone model is ×1.12 below. In the 10–15 Hz band the gaps are 1.07 vs 0.53 in log units.

**Consequences:**

1. **The paper's mechanism is contradicted.** "Transfer depends more on randomising over sensor types than on matching the target sensor" (Results VII-E, Discussion, Table IV) does not hold. A *narrower* model, the phone-holder configuration alone, transfers *better* than the mixture. That configuration includes a 15–40 Hz holder resonance and represents no component of the LiRA setup. The model meant to represent the target device transfers worst.
2. **The headline is fragile.** Four of five plausible simulator variants carry a ≈ +0.4 m/km bias. The 0.44 is one configuration whose absolute gain happens to fit. The robustness sweep agrees: holder resonance alone moves the bias from −0.65 to +0.37 m/km (`results/sim/robustness.csv`). The paper calls these sensor effects "no material effect" for other perturbations and does not flag this one.
3. **Shape versus level.** Adding one gain offset (log intercept) estimated from 5–20 km of real road brings the fixed-vehicle simulator to 0.43, the same as the primary. So the ablation claim that "vehicle randomisation matters" is mostly about level, not shape. Telematics, ideal-sensor and matched-sensor variants stay at 0.51–0.58 after the offset, because their spectral content is wrong (the 10–15 Hz band), not just their gain.

**What to call the 0.44 result.** It is partial transfer plus a fortuitous level match: comparable to the real baseline, partly explainable by a sensor-gain coincidence, and with the physical cause unidentified. It is genuine evidence that half-car simulations over measured profiles carry the *ranking and speed-shape* information. It is **not** evidence that a physically faithful, randomised simulator delivers calibrated IRI for an unseen car without real data.

**A point in the paper's favour that it doesn't report.** I regressed, on real data, log(prediction) on log(IRI) and log(speed) with route fixed effects. The speed elasticity of the predictions at fixed IRI is −0.16 [−0.18, −0.14] for real-trained LightGBM and −0.08 for sim-trained LightGBM. Read observationally, the real-trained model would *fail* the paper's own ±10 % speed criterion on real cars (about −15 % from 40 to 100 km/h), while the sim-trained model would pass (about −7 %). This is the best real-data evidence that simulation provides de-confounded training. It belongs in the paper, with the caveat that attenuation from label noise biases this coefficient for both models.

---

## 6. Value of simulation (the "20 km" claim)

1. **Wrong comparator in the abstract.** The abstract says real data "needs about 20 km to match it", where "it" is the 0.44 model. Real-only at 20 km is 0.456, which does not match 0.439. The 20 km crossover is against the p79+iso model (0.459).
2. **Crossover is imprecise.** It lies between 10 km (0.499) and 20 km (0.456), from 5 draws on 4 routes, with about 10 car passes per km. It is one realisation, not a constant.
3. **Unequal profilometer budgets (main problem).** The simulator used *all* training-route profiles, about 120–145 km per fold, while real-only used k km. The introduction motivates simulation because "each label requires a profilometer run", yet the simulator consumes about 6× more profilometer road. My equal-budget control, simulating only the same k km of blocks:

| Profiled road (km) | Real-only | Sim-only, same blocks |
| ------------------ | --------- | --------------------- |
| 5                  | 0.82      | 0.71                  |
| 10                 | 0.50      | 0.47                  |
| 20                 | 0.46      | 0.47                  |
| 40                 | 0.43      | 0.45                  |

Per km of profiled road, simulation is about as label-efficient as real data: slightly better below 10 km, slightly worse above. What simulation replaces is **co-registered car drives over profiled roads**, not profilometer labels. The Discussion half-says this ("needs profiled roads … but no instrumented drives"). The abstract and Conclusion say the opposite ("replace scarce labels", "replaces about 20 km of labelled road").

Fine-tuning and pooling are implemented correctly, and the test route stays untouched (blocks are sampled from training routes only).

**Verdict.** As stated, the result is not a durable empirical contribution. Restated as "simulation over already-surveyed profiles removes the need for paired car drives, at equal accuracy per km of profiled road, for this car", it is modest but true.

---

## 7. Speed as signal and shortcut

- Speed correlates with the label and is an input. Speed alone gives 0.74, which is about a road-class prior (0.81).
- **The model does sense roughness:** within-route partial Spearman given speed is 0.70–0.90, against −0.02 to 0.42 for speed-only. Supported.
- **Pooled metrics flatter the models.** Pooled Spearman 0.95, R² 0.79 and κ 0.91 are inflated by the urban/motorway separation. Within routes Spearman is 0.72–0.90, and raw RMS ranks almost as well as LightGBM. The abstract should headline within-route figures.
- **Speed-normalisation claims are simulation-only.** The simulator's speed exponent (1.20) differs from the real car's (0.60–0.79). "LightGBM trained on measured profiles is speed-invariant" is shown only in simulation. The real-data analysis in §5 is the missing link.
- **No speed-normalisation leakage:** α is fitted on training routes only (models.py).

---

## 8. Unseen vehicles

- **What "unseen" means here.** Random held-out draws from the *same* uniform parameter ranges (in-distribution interpolation), 30 training vehicles, and a *relative* criterion of at most +10 % ([sim_generate.py:127-148](research_rescue/experiments/sim_generate.py#L127-L148)).
- **LightGBM still generalises in absolute terms.** Its unseen-vehicle MAE (0.88) is better than the seen-vehicle MAE of every estimator except the CNN (0.81). The criterion penalises benefiting from having seen a vehicle, not failing on new ones.
- **The paper contains a successful unseen-vehicle test.** The LiRA zero-shot evaluation is itself one: the Zoe is not among the simulated vehicles, and it worked at 0.44.
- **Missing experiment:** does the seen/unseen gap shrink with 100–300 training vehicles? It is cheap to run, and without it "vehicle generalisation is unresolved" may simply reflect only 30 training vehicles.
- **Verdict:** a useful but over-framed negative result. Moderate.

---

## 9. Statistics

- The bootstrap code is correct, paired and Holm-corrected. The **resampling unit is wrong**: residual autocorrelation at 100 m is 0.25–0.56.
- **Sim vs real paired difference:** p = 0.001 with segment clusters, 0.026 with 1 km blocks, **0.10 with 5 km blocks**.
- **CNN vs LightGBM** holds at all levels (p ≤ 0.001), but is not consistent across routes.
- **MLP vs LightGBM:** not different at any level.
- No route-level inference is possible with n = 4; per-route numbers are shown, which is honest. CIs are conditional on the trained models and ignore training-set variability.
- **Recommendation:** 1 km or 5 km blocks as the primary cluster for *paired* tests (Table S6 does this only for marginal CIs). Report within-route Spearman and MAE as primary, pooled as secondary.

---

## 10. Other moderate issues

- **ARAN "reference uncertainty".** ARAN points are matched within 10 m of the P79 track with **no heading constraint** ([iri_unit_test.py:162-171](research_rescue/evaluation/iri_unit_test.py#L162-L171)). On two-way urban streets that can pull in opposite-lane data, and 42 points exceed 15 m/km. "Urban errors are smaller than the disagreement between two professional devices" therefore rests on an unvalidated alignment. Remove it or validate it.
- **BeamNG non-transfer.** Causes are confounded: invalid labels (shown), 48–68 % duplicated IMU rows, 3 vehicles, one driver. The vibration index trained on BeamNG ranks real segments well (ρ = 0.93) and is mainly off in level (bias −0.73), which fits the label finding. "Authored meshes provide neither realistic roughness nor valid labels" goes beyond what is isolated.
- **PVS claim.** "Speed predicts the quality labels better than vibration" holds against raw RMS and on the bad-vs-regular subtask (352 windows, 72 positives). It does not hold against RMS/√v on good-vs-rest (0.99 vs 0.97). Partially supported, and tangential to IRI.
- **Passes-needed analysis.** It compares different segment subsets (935 / 869 / 486 segments at 1 / 5 / 8 passes).
- **Editorial.** Table S4's caption still says "pre-registered"; the main text says "fixed in advance".

---

## 11. Novelty and literature

| Question                            | Answer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Already done?                       | IRI or roughness estimators trained on randomised half-car or quarter-car simulations:**Jeong et al. 2020 ([25])** trained CNNs on 4-DOF half-car responses of varied vehicles at randomised speeds, validated numerically. Simulation-trained classifiers: [23], [24]. ML on the same LiRA data: Bajic 2021 ([20]), cited but not compared. **Skar & Levenberg 2024** (*J. Transp. Eng. Part B* 150(1) 04023040): quarter-car calibrated to the Renault Zoe, profile inversion on LiRA cars against a laser profilometer. **Not cited**, and it is the closest physics competitor on the *same data*. |
| What is new?                        | (a) Zero-shot sim→real for continuous IRI on**real production cars with profilometer reference, route-disjoint, on public data**. (b) The equal-protocol comparison against a game-engine corpus. (c) Showing that a published-style label correction is not IRI. (d) A speed-confounding analysis with within-route controls.                                                                                                                                                                                                                                                                                        |
| Simulator new?                      | No: a linear half-car plus sensor noise model.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Sensor randomisation new?           | Domain randomisation is standard ([28]). Applying it to sensor models for IRI is a small extension, and its claimed mechanism is contradicted (§5).                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| Value-of-simulation experiment new? | The design is reasonable; its main result is an artifact of unequal budgets (§6).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Benchmark or protocol new?          | Partly. The rules are good practice rather than novel.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| BeamNG negative finding useful?     | Mainly as a caution about labels derived from authored geometry. The simulator-type comparison is not controlled.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| New empirical fact?                 | One, conditional: for one car type, simulated responses over measured profiles of other roads can stand in for paired car data.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Incremental?                        | Yes, as currently framed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

Jeong et al. 2020 is described in the paper only as "a CNN for calibration-free assessment", which hides that it is the direct precursor of the simulator idea. The Related Work closing sentence ("Compared with this work, we …") needs to name what Jeong et al. and Skar & Levenberg already did.

---

## 12. Reproducibility

**Strong:**

- Public primary data with MD5-verified downloader.
- One-command pipeline; every number in the paper is a generated macro.
- All predictions saved; seeds fixed.
- I reproduced the zero-shot and few-shot numbers exactly from the shipped code.

**Weak:**

- Nothing committed, so the "fixed in advance" timestamps are unverifiable.
- Absolute Windows interpreter paths; no lockfile.
- BeamNG and PVS corpora live in a cloud-synced private folder.
- No released checkpoints (cheap to retrain, so minor).

An independent researcher could reproduce all LiRA-CD results. **Grade: high for this field.**

---

## 13. Claim audit

| #  | Location                  | Claim                                                                    | Status                                                                           |
| -- | ------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| 1  | Abstract, C(i)            | Mesh correction lowers urban IRI by 28 %, so earlier labels were not IRI | SUPPORTED                                                                        |
| 2  | Abstract, C(i)            | Implementation reproduces P79 IRI (r = 1.000)                            | SUPPORTED (algorithm check, as stated)                                           |
| 3  | Abstract                  | GBM 0.42, ρ = 0.95                                                      | SUPPORTED; ρ OVERSTATED as a skill measure (pooled)                             |
| 4  | Abstract, Results         | Better than CNN (0.48)                                                   | PARTIALLY (one-route effect; untuned legacy CNN)                                 |
| 5  | Abstract                  | Speed predicts PVS labels better than vibration                          | PARTIALLY                                                                        |
| 6  | Abstract, Intro           | Sim-only 0.44, "nearly matches" real training                            | SUPPORTED as a measurement; motorway 0.20 vs 0.14 makes "nearly" PARTIAL         |
| 7  | Abstract, Conclusion      | Real data needs about 20 km to match it                                  | OVERSTATED (wrong comparator; unequal budget; 10–20 km range)                   |
| 8  | Abstract                  | Game-engine corpus does not transfer (1.36)                              | PARTIALLY (index: 0.85, ρ = 0.93; cause not isolated)                           |
| 9  | Abstract                  | Learned speed corrections hold only for the training road spectra        | SUPPORTED (simulation only)                                                      |
| 10 | Abstract, Conclusion      | No accurate estimator meets the unseen-vehicle criterion                 | Literally SUPPORTED; the framing "not achieved even in simulation" is OVERSTATED |
| 11 | Abstract                  | Simulation over measured profiles can replace scarce labels              | OVERSTATED (replaces paired drives, not profiles; relies on a gain coincidence)  |
| 12 | C(ii)                     | Calibration and filtering hid diverging predictions                      | SUPPORTED                                                                        |
| 13 | C(iii)                    | Route-disjoint comparison with segment-level uncertainty                 | SUPPORTED; precision OVERSTATED                                                  |
| 14 | Results VII-C             | Urban errors smaller than profilometer disagreement                      | UNSUPPORTED (ARAN alignment)                                                     |
| 15 | Results VII-D             | Within routes, vibration carries information speed lacks                 | SUPPORTED                                                                        |
| 16 | Results VII-E             | Each randomised component matters                                        | PARTIALLY (vehicle effect is mostly level)                                       |
| 17 | Results VII-E, Discussion | Breadth of sensor model matters more than matching the target            | **UNSUPPORTED / contradicted**                                             |
| 18 | Results VII-F             | Sampling rate matters most among perturbations                           | PARTIALLY (holder resonance moves bias more)                                     |
| 19 | Discussion                | Architecture is not where the gains are                                  | SUPPORTED on this dataset                                                        |
| 20 | Discussion                | Results favour randomised simulators over measured profiles              | OVERSTATED                                                                       |
| 21 | Discussion                | Authored meshes give neither realistic roughness nor valid labels        | PARTIALLY                                                                        |
| 22 | Conclusion                | GBM as accurate as anything tried                                        | SUPPORTED                                                                        |

---

## 14. Critical contribution test

**A. The one central contribution.** A leakage-free, route-disjoint, profilometer-referenced evaluation on public real-car data showing that an estimator trained only on half-car simulations over measured profiles of *other* roads approaches one trained on real car data from the same fleet. Everything else is support or diagnosis.

**B. If the CNN were removed.** Everything of value remains, and focus improves. The CNN only serves the post-mortem and the "architecture doesn't matter" remark.

**C. Is the sim-pretraining result novel and important?** The idea is not novel (Jeong et al. 2020). Real-car, profilometer-referenced, route-disjoint confirmation is new and useful. It would be important if shown robust across simulator configurations or vehicles; currently it is shown for one configuration that wins partly by gain coincidence.

**D. Is "replaces ~20 km" a meaningful empirical result?** No, as stated. It is an artifact of unequal profile budgets, compared against a different simulation set than the one quoted, and specific to this dataset's pass density and class mix. The equal-budget curve is the meaningful version, and it shows rough parity.

**E. Does BeamNG's failure give scientific insight?** Mainly it documents an inadequate corpus. The general insight, that labels derived from authored geometry must be validated against a profilometer, comes from RQ1, not from the transfer failure.

**F. What kind of paper is it?** A benchmark/evaluation paper with a sim-to-real component, plus a diagnostic post-mortem of an unpublished pipeline. It is not a methods paper.

**G. Is the positioning clear?** No. Three stories compete:

- the post-mortem (abstract opening, contributions i–ii);
- the benchmark (iii);
- sim-to-real (iv and the title).

A reader cannot tell which is the paper. Contributions about an unpublished pipeline are of interest mainly to its authors.

**H. Could a reviewer fairly say "many careful experiments, no sufficiently novel contribution"?** Yes, and fairly:

- every method component is standard and has precedent;
- (i) and (ii) concern a pipeline nobody else uses;
- the positive result is one dataset, one car, one simulator configuration, with a misidentified mechanism;
- the negative results are either confounded (BeamNG) or tested in an in-distribution design (vehicles).

**I. Could a reviewer say "the real contribution is the controlled evidence about when simulation helps"?** Yes, but the paper does not establish *when*. It shows one success and several failures without identifying the condition. My analyses suggest the condition is a match of sensor spectrum and gain to the real data. That is a hypothesis the paper could test with existing data but currently gets wrong.

**J. Strongest fully supported interpretation.** On four public profilometer-referenced routes driven by one car model:

- Gradient boosting on hand-crafted vibration and speed features reaches 0.42 m/km on unseen routes; within routes it ranks segments well beyond what speed explains.
- A model trained only on linear half-car simulations over measured profiles of other roads, with one particular sensor-model mixture, reaches 0.44 m/km with less speed confounding than the real-trained model.
- Pooled metrics, test-domain calibration, prediction filtering and an unvalidated label correction can each manufacture apparent accuracy.

**K. Strongest interpretation not justified.** None of these is shown:

- that randomised simulation is a general substitute for real calibration data;
- that sensor breadth rather than fidelity drives transfer;
- that simulation reduces the need for *profilometer* labels by about 20 km;
- that game-engine simulation cannot work;
- that vehicle generalisation fails;
- anything about other cars, phones or cities.

**One-sentence summaries:**

1. **Most favourable, defensible:** "A carefully controlled, route-disjoint study on public profilometer-referenced car data showing that, for one car type, an IRI estimator trained only on half-car simulations over measured profiles of other roads approaches one trained on real car data (0.44 vs 0.42 m/km), together with evidence that label derivation, test-domain calibration and speed confounding can manufacture apparent accuracy."
2. **Neutral:** "An evaluation of standard vehicle-based IRI estimators on four LiRA-CD routes, finding gradient boosting on hand-crafted features as good as anything tried, and reporting one simulator configuration that transfers nearly as well as real training alongside several simulation results that do not transfer or generalise."
3. **Most sceptical:** "A post-mortem of the authors' own unpublished pipeline attached to a single-dataset benchmark, in which the one positive sim-to-real result depends on an uncalibrated sensor-model component and is explained by a mechanism the authors' own data contradict."

---

## 15. Conference review

1. **Summary.** As in §0 and §14 J.
2. **Main contribution.** Real-car, route-disjoint evidence that simulation over measured profiles can stand in for paired car data for one car type.
3. **Strengths:**
   - Exemplary protocol hygiene: no leakage, no filtering, honest negative results, disclosed deviations.
   - Public data and full reproducibility (verified).
   - A useful speed-confounding analysis with within-route controls.
   - Valid labels, with a clear demonstration that an invalid correction is not IRI.
4. **Major weaknesses:**
   - (B1) The mechanism of the central result is contradicted, and the result is fragile across simulator variants.
   - (B2) The value-of-simulation claim is confounded by profile budget, and the abstract's comparator is wrong.
   - (B3) Four routes, one car, shared vehicles across routes.
   - (B4) Closest prior work missing (Skar & Levenberg 2024) or under-described (Jeong et al. 2020); no comparison with Bajic 2021.
5. **Minor weaknesses:** segment-level inference; pooled metrics headlined; ARAN comparison; BeamNG cause not isolated; framing of the unseen-vehicle result; one-route CNN effect; "pre-registered" caption.
6. **Technical soundness:** high in execution, medium in interpretation.
7. **Novelty:** low to moderate.
8. **Experimental quality:** high for internal validity, low for external validity.
9. **Statistical quality:** correct implementation, wrong unit, no route-level inference.
10. **Reproducibility:** high.
11. **Clarity:** good sentence level; diffuse positioning.
12. **Reviewer concerns:** §17.
13. **Required changes:**
    - Replace the "breadth" mechanism with the sensor-half and shape/level decomposition.
    - Add the equal-profile-budget curve and restate the 20 km claim.
    - Cite and position Skar & Levenberg 2024 and Jeong et al. 2020.
    - Use block-level paired tests.
    - Headline within-route metrics.
    - Drop or validate the ARAN argument.
    - Add the real-data speed-elasticity analysis.
14. **Optional improvements:**
    - Unseen-vehicle test as a function of the number of training vehicles.
    - BeamNG index result in the abstract.
    - Shorten the post-mortem.
    - Compare with a calibrated quarter-car inversion if feasible.

**Score: 4/7, Borderline.** At an applied transportation or sensing conference this leans weak accept on rigour; at a selective venue it leans weak reject on novelty.

**What separates 4 from 5.** The required changes in item 13. All need only existing data. They turn an over-claimed positive result into a correctly explained, robust one, and fix the positioning.

---

## 16. Journal review

**Journal-ready?** No.

**New experiments needed:**

- **With existing data:** sensor-half and spectral diagnosis of *why* the phone configuration matches (real vs simulated PSDs per band and speed); equal-budget curves; gain-calibration protocol; number-of-vehicles sweep; route-level analysis.
- **Needing new data or a new design** (the real blocker for archival durability):
  - A held-out real dataset, a second vehicle, or a second sensor, to test a simulator design *frozen now*. All four routes have already informed the interpretation.
  - A comparison with a calibrated physics inversion on the same cars.

**Is the contribution substantial enough for archival publication?** Only after reframing to "what simulation provides (ranking, speed shape) and what it does not (absolute gain without matching sensor dynamics)", and after at least one out-of-sample confirmation.

**Is the current evidence enough?** Not for the durability a journal expects. The conclusion rests on one sensor-model coincidence and two routes per class.

**Score: 3/7, major revision** (reject-and-resubmit at a strict journal).

**What separates 3 from 4:** the existing-data analyses above plus the reframing. **From 4 to 5:** one independent real confirmation (new vehicle, sensor or city).

---

## 17. Conference vs journal

|                        | Conference                                                          | Journal                                                                      |
| ---------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Scientific quality     | Sound execution; misexplained central result is fixable             | Same, plus mechanism must be*demonstrated* (PSD/gain diagnosis)            |
| Novelty                | Real-car confirmation of a known idea; enough if clearly positioned | Needs a general insight (when simulation helps), not one success             |
| Methodology            | Protocol is a strength                                              | Protocol fine; no untouched test set for simulator design is a problem       |
| Experiments            | Sufficient after equal-budget and sensor-half additions             | Needs out-of-sample vehicle/sensor/city, or at least a held-out design check |
| Statistics             | Block-level paired tests suffice                                    | Plus route-level or hierarchical treatment and power discussion with n = 4   |
| Reproducibility        | Exceeds expectations                                                | Commit, pin environment, release corpora or document access                  |
| Generalisation         | Scope limits acceptable if stated                                   | Single car and city is the main barrier                                      |
| Literature             | Add Skar & Levenberg; reposition Jeong                              | Plus quantitative comparison with a calibrated inversion and Bajic 2021      |
| Current readiness      | One revision cycle with existing data                               | New data needed                                                              |
| Main remaining blocker | Mechanism and claim wording (§5, §6)                              | Independent real confirmation of the transfer                                |

---

## 18. The single most dangerous reviewer objection

> "The 0.44 m/km zero-shot result is not evidence that a randomised, physics-based simulator transfers to real cars. It is one simulator configuration whose absolute gain happens to match the target car. The sensor model meant to represent the target device transfers at 0.68. A phone-holder model, which represents nothing in the LiRA setup, transfers at 0.41. Four of five plausible variants carry a +0.4 m/km bias. With four routes and no held-out data, a reader cannot tell whether a new vehicle or sensor would get 0.44 or 0.69, and the paper's 'sensor breadth' explanation is contradicted by its own data."

**Classification: C** (not answered, but answerable with existing data). The paper reports the 0.69 variant (partial B), but its interpretation goes the wrong way. The generalisation part of the objection is **D** (new experiment).

**Smallest analysis that most increases reviewer confidence.** Report the sensor-half decomposition and a shape/level decomposition: zero-shot, then plus one gain offset from 1–5 km, for every simulator variant. Add the real-vs-simulated PSD comparison per band. Then reframe the practical recipe as "simulation over measured profiles plus a few km of real gain calibration", evaluated across all variants, not only the lucky one. This takes about an hour of compute with the scripts I left in the scratchpad. **Do not adopt phone-only as the new primary configuration:** it was found by looking at the test routes.

---

## 19. Final verdict

**Conference:** Acceptance score **4/7**. Current status: **Borderline (major revision of claims, no new data needed).**

**Journal:** Acceptance score **3/7**. Current status: **Major revision (needs independent real confirmation).**

- **Strongest part:** the evaluation itself. It is leakage-free, uses public profilometer-referenced data, reproduces exactly, and has within-route speed controls.
- **Weakest part:** the explanation of why simulation transferred (§5) and the value-of-simulation claim (§6).
- **Most novel part:** real-car, route-disjoint zero-shot transfer from simulated responses over measured profiles of other roads.
- **Most vulnerable claim:** "transfer depends more on randomising over sensor types than on matching the target sensor", followed by "replaces about 20 km of labelled road".
- **Single most important experiment:** an independent real-car confirmation (another vehicle, sensor or road network) of a simulator design frozen *before* seeing it. Within existing data: the sensor-half, shape/level and PSD diagnosis.
- **Single most important writing change:** state one contribution. Simulation over surveyed profiles reproduces ranking and speed shape and can replace paired car drives for this car; absolute calibration depends on matching sensor dynamics, which happened here through an unintended component. Drop "breadth" and "replaces scarce labels".
- **Publishable?** Yes, as a careful empirical evaluation at an applied venue, once the interpretation is corrected. Not yet as a durable archival claim about sim-to-real IRI estimation.
- **To gain one point:**
  - Conference 4 → 5: the required changes in §15, all with existing data.
  - Journal 3 → 4: those changes plus the PSD diagnosis, the number-of-vehicles sweep and a comparison with a calibrated inversion.
  - 4 → 5 at either venue: one real out-of-sample confirmation.

**Separate compression issue (not scored).** The PVS section, the BeamNG protocol forensics (Table IV bottom) and the post-mortem framing in the Introduction take about 1.5 pages that serve the authors' history more than the contribution. They belong in the supplement.

---

**Sources (literature check):** [Jeong et al. 2020, calibration-free CNN](https://www.researchgate.net/publication/340232560_Convolutional_neural_networks_for_pavement_roughness_assessment_using_calibration-free_vehicle_dynamics) · [Skar &amp; Levenberg 2024, Road Profile Inversion from In-Vehicle Accelerometers](https://orbit.dtu.dk/en/publications/road-profile-inversion-from-in-vehicle-accelerometers/) · [Bajic et al. 2021, arXiv:2107.01199](https://arxiv.org/abs/2107.01199) · [LiRA-CD (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10375556/) · [Shangguan &amp; Lu, J. Comput. Civ. Eng.](https://ascelibrary.org/doi/10.1061/JCCEE5.CPENG-6782)

I didn't change any repository file. I did save the verified findings to memory for future revision sessions. If you want this review as a shareable page for your co-author, I can publish it as an artifact.

# Adversarial review: "How Far Can Simulation Take Vehicle-Based IRI Estimation?" (research_rescue/)

**Bottom line:** I found no leakage and no fatal flaw, and the headline numbers reproduce exactly. But the paper's explanation of its one positive result is contradicted by its own data. The "replaces ~20 km of labelled road" claim also comes from an unequal comparison. Conference **4/7** (borderline), journal **3/7** (major revision). Both problems can be fixed with data you already have. Generalising beyond one car on four routes cannot.

**What I did.** I read the paper, supplement, all audit documents and the core code (simulator, sensor model, preprocessing, features, models, statistics, experiment drivers). I traced every headline number to its result file. I also ran six independent analyses on your existing data without changing any repository file. The scripts (`rev_a`–`rev_f.py`) are in the session scratchpad: `C:/Users/nishk/AppData/Local/Temp/claude/d--Coding-Hackathon-GFG-ARM-ARM/7f41980c-…/scratchpad/`. Two of those analyses change how the paper's central result has to be read.

---

## 0. What the paper actually does

| Item                        | Reconstruction                                                                                                                                                                                                                                                                                     |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Research question           | When labels are valid and evaluation is route-disjoint on real cars, how much of the accuracy and properties claimed for simulation-trained IRI estimators survives? Can simulated responses replace real labelled car data?                                                                       |
| Hypotheses                  | H1–H3 are directional (label correction invalid; earlier result depends on test calibration and filtering; speed explains apparent skill). RQ4 and RQ5 have no direction. Two criteria were fixed in advance: speed invariance within ±10 %, and an unseen-vehicle MAE increase of at most 10 %. |
| Methodological contribution | No new estimator. The new parts are an evaluation protocol and a simulation pipeline built from standard parts: a linear 4-DOF half-car, a sensor model, domain randomisation, LightGBM on hand-crafted features.                                                                                  |
| Empirical contribution      | A model comparison on LiRA-CD (M0–M6); zero-shot and few-shot sim→real; controlled simulation tests; a post-mortem of the authors' earlier BeamNG pipeline.                                                                                                                                      |
| Real data                   | LiRA-CD: 4 routes (2 urban, 2 motorway), Renault Zoe cars, AutoPi telematics unit, P79 profiles.                                                                                                                                                                                                   |
| Simulated data              | Half-car driven over P79 profiles of the 3 training routes, or over ISO-8608-type synthetic profiles; 30 training vehicles; 50/50 mixture of a telematics-like and a phone-like sensor.                                                                                                            |
| Ground truth                | IRI recomputed from the P79 laser profiles (mean of both wheel paths, per 100 m). It is checked against the P79's own IRI, which is an algorithm check because both come from the same profiles.                                                                                                   |
| Independent unit            | Claimed: the 100 m segment. In practice: 1–5 km blocks within routes. For generalisation claims: the route (n = 4, i.e. 2 per road class).                                                                                                                                                        |
| Splits                      | Leave-one-route-out (both directions held out together). Model selection by inner leave-one-route-out on the training routes. Neural-net early stopping on a grouped 20 % of training segments.                                                                                                    |
| Positive results            | Label correction is not IRI; real-trained LightGBM 0.42; sim-only 0.44; vibration carries roughness information within routes.                                                                                                                                                                     |
| Negative results            | BeamNG does not transfer; unseen-vehicle criterion not met; speed correction learned on synthetic roads fails on measured profiles; CNN is not the best model.                                                                                                                                     |

---

## 1. Headline results traced to artifacts

| Paper claim                           | Artifact                                           | Verified?                                         | Reviewer note                                                                                                                                                                                          |
| ------------------------------------- | -------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| LightGBM 0.42 [0.39, 0.45]            | `results/lira/ladder_segment_metrics.csv`        | Yes (0.420)                                       | The CI treats spatially autocorrelated segments as independent. The 1 km-block CI is [0.36, 0.48].                                                                                                     |
| MLP 0.42, p = 0.458                   | same                                               | Yes (0.425)                                       |                                                                                                                                                                                                        |
| CNN 0.48                              | same                                               | Yes (0.475)                                       | Mean of per-seed MAEs; the 5-seed ensemble gets 0.465. The deficit comes from one route (CPH1 +0.14; other routes −0.02 to +0.02).                                                                    |
| Speed-only 0.74                       | same                                               | Yes                                               |                                                                                                                                                                                                        |
| Sim → real 0.44                      | `zeroshot_segment_metrics.csv`                   | **Reproduced exactly** (0.439, bias +0.010) | See §5: the primary sensor mixture is the only variant with near-zero bias.                                                                                                                           |
| BeamNG → real 1.36                   | same                                               | Yes                                               | The BeamNG-trained vibration index gets**0.85, ρ = 0.93**. Only the LightGBM is quoted.                                                                                                         |
| "About 20 km"                         | `fewshot_raw.csv`                                | Number yes, wording no                            | Real-only at 20 km: 0.456 (range 0.430–0.489). It is compared with**sim p79+iso, 0.459**, not the abstract's 0.44 model. Real-only at 10 km: 0.499. I reproduced 0.822 / 0.499 / 0.456 exactly. |
| Sensor-rate fix: 0.44 → 0.46         | `zeroshot_sensor_segment_metrics.csv`            | Yes (0.455)                                       | Uninformative: the phone half carries the result (§5).                                                                                                                                                |
| Single matched sensor 0.69            | same                                               | Yes (0.687)                                       | Matches my telematics-half-only run (0.678).                                                                                                                                                           |
| Unseen vehicles +19 % (upper CI 24 %) | `results/sim/unseen_vehicle_paired.csv`          | Yes                                               | In-distribution held-out draws, 30 training vehicles (§8).                                                                                                                                            |
| CIs                                   | [stats.py](research_rescue/common/stats.py#L54-L98) | Correctly implemented                             | Wrong resampling unit (§9).                                                                                                                                                                           |

**Chronology.** File timestamps are consistent with the claims: protocol 18:24, simulated data 18:46, LiRA dataset 19:08, first zero-shot metrics 19:33, model-ladder metrics 19:44. The simulator was fixed before any LiRA label was scored. This is self-attested on uncommitted files.

---

## 2. Dataset and ground truth

| Quantity                                        | Count                                                                                                      |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Segment-passes (the "windows")                  | **16,293**                                                                                           |
| Distinct 100 m segments                         | **1,678** (168 km)                                                                                   |
| 1 km blocks / 5 km blocks                       | 172 / 40                                                                                                   |
| Route-directions / routes                       | 8 /**4** (2 urban, 2 motorway)                                                                       |
| Passes / trips                                  | 91 / 37 (CPH6 has only 12 passes)                                                                          |
| Vehicles                                        | 1 model; ≥ 8 telematics units,**shared across routes** (TMU#10, #11 and #14 drive CPH1, M3 and M13) |
| Sensor types                                    | 1 (AutoPi; nominal rate 52.6 Hz in 66 % of passes, else 333 Hz)                                            |
| Passes per segment                              | median 10 (2–15)                                                                                          |
| Lag-100 m autocorrelation of LightGBM residuals | **0.25–0.56** within each route-direction (my check)                                                |

- **Effective sample size.** Accuracy *within* these roads is estimated from about 1,678 correlated segments, closer to about 172 independent blocks. Generalisation *across* roads rests on two routes per road class. The paper says this in Limitations, but its intervals and p-values still describe segments.
- **Labels.** IRI per 100 m from the P79 profile, aligned by GPS map matching (1–3.4 Hz GPS, lateral distance < 20 m). Survey dates differ from car-pass dates. This adds label noise but no leakage.
- **"Route-disjoint" is not "vehicle-disjoint".** The real-trained baseline sees the same physical cars in training and test; the simulation-trained model does not. This favours the real baseline. It is not disclosed explicitly.

---

## 3. Leakage audit

| #  | Type                            | Present?                                      | Evidence                                                                                                                                                                                           | Affects headline?                                                                                                                                                                                                                     |
| -- | ------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | Road overlap                    | Negligible                                    | 7 of 1,678 segments within 15 m of another route (`route_overlap.json`)                                                                                                                          | No                                                                                                                                                                                                                                    |
| 2  | Route overlap                   | No                                            | Leave-one-route-out, both directions held out together ([exp_lira.py:126](research_rescue/experiments/exp_lira.py#L126))                                                                            | No                                                                                                                                                                                                                                    |
| 3  | Repeated passes                 | No                                            | All passes of a test segment are in test; predictions aggregated per segment                                                                                                                       | No                                                                                                                                                                                                                                    |
| 4  | Vehicle overlap                 | **Yes, by design (real baseline only)** | Same telematics units in train and test routes                                                                                                                                                     | Favours the real baseline; no inflation of the sim result                                                                                                                                                                             |
| 5  | Sensor overlap                  | Yes, by design                                | One device type                                                                                                                                                                                    | Limits generality; not leakage                                                                                                                                                                                                        |
| 6  | Temporal overlap                | No                                            | Surveys and passes on different dates                                                                                                                                                              | Label noise only                                                                                                                                                                                                                      |
| 7  | Overlapping windows             | No                                            | Test units are non-overlapping; simulated units are too                                                                                                                                            | No                                                                                                                                                                                                                                    |
| 8  | Normalisation                   | No                                            | Neural-net normalisation fitted on training data only ([models.py:172](research_rescue/common/models.py#L172-L177))                                                                                 | No                                                                                                                                                                                                                                    |
| 9  | Hyper-parameters                | No                                            | Inner leave-one-route-out over a 6-configuration grid                                                                                                                                              | No                                                                                                                                                                                                                                    |
| 10 | Calibration                     | No                                            | No test calibration, no capping                                                                                                                                                                    | No                                                                                                                                                                                                                                    |
| 11 | Feature engineering             | Not detectable                                | `features.py` written at 18:13, before any LiRA label was used                                                                                                                                   | No                                                                                                                                                                                                                                    |
| 12 | Thresholds                      | No                                            | FHWA bands fixed a priori                                                                                                                                                                          | No                                                                                                                                                                                                                                    |
| 13 | Test-set model selection        | **Mild**                                | The protocol named no primary simulation set. CNN compute and the few-shot runs used p79+iso, which suggests it was the planned main set; the abstract headlines the best set (p79, 0.44 vs 0.46). | ~0.02 m/km                                                                                                                                                                                                                            |
| 14 | Post-hoc experiments            | Disclosed                                     | Sensor analysis and the speed sweep on measured profiles are labelled post-hoc                                                                                                                     | The*interpretation* of the post-hoc sensor result is wrong (§5)                                                                                                                                                                    |
| 15 | Simulator tuned on test results | **Not found**                           | Simulated data produced before any LiRA metric existed; simulator unchanged afterwards                                                                                                             | No.**Warning:** there is no untouched test set. Leave-one-route-out uses all four routes as test, so any simulator change made from now on against these numbers (including adopting my phone-only finding) is test-set tuning. |

**Verdict: no leakage that inflates a headline number.** This is the paper's strongest asset.

---

## 4. Baseline fairness

- **Same inputs for everyone.** Features, preprocessing, log target, splits and test units are identical across models. LightGBM gets a 6-configuration inner search; the neural nets get fixed configurations with 5 seeds. That is fair enough.
- **CNN comparison.** The CNN is the legacy architecture with legacy hyper-parameters, reported as a per-seed mean rather than an ensemble (0.475 vs 0.465), and its deficit sits on one route. "CNN is worse" is true on this data but not robust across routes. The CNN result is not important to the contribution (§14 B).
- **Missing baselines that matter:**
  1. **Map-only road-class prior.** Predicting each held-out route with the median of the other same-class route needs only a map and gives **0.81 m/km**. Speed-only (0.74) is essentially this. The paper never states that speed-only is a road-class proxy *numerically*.
  2. **A calibrated physics inversion on the same cars:** Skar & Levenberg 2024 (§11). This is the natural non-learning competitor and is absent.
- **Is the proposed approach better than a well-tuned simple model?** There is no proposed estimator. LightGBM *is* the simple model and it wins. The contribution has to be the evaluation and the simulation evidence, which the paper partly recognises.

---

## 5. Simulation validity and the sim-to-real claim (central section)

**What the simulator reproduces.** Within-route ranking. Every estimator, including raw RMS and the synthetic-profile simulator, ranks segments within a route about equally well (partial Spearman given speed: LightGBM real 0.84 / 0.80 / 0.70 / 0.90; sim[iso] 0.83 / 0.79 / 0.71 / 0.90; raw RMS 0.79 / 0.75 / 0.73 / 0.91). It also learns a speed correction that is *less* confounded than the real-trained one (below).

**What it does not reproduce.**

- **Vibration level:** real vibration is ×1.23 the simulated level on matched segments.
- **IRI elasticity** of log RMS: 0.93 in simulation vs 0.65 real.
- **Speed exponent:** 1.20 in simulation vs 0.60–0.79 real.
- **Roll:** none; the half-car is driven by the mean of the two wheel paths.
- **Non-linearity:** none, and there are no structural or powertrain modes.
- **Sensor rates:** the telematics rates were set from an inaccurate preliminary inspection.

**Decisive check (new, existing data).** Split the primary simulation set by sensor half and retrain the same zero-shot LightGBM:

| Training data (P79 profiles, 30 vehicles)          | Zero-shot MAE   | Bias          | Motorway MAE |
| -------------------------------------------------- | --------------- | ------------- | ------------ |
| Mixture (paper's primary)                          | 0.439           | +0.01         | 0.197        |
| **Phone-like half only**                     | **0.409** | −0.09        | 0.139        |
| Telematics half only                               | 0.678           | +0.43         | 0.558        |
| (paper, post-hoc) Single matched telematics sensor | 0.687           | +0.40         | —           |
| (paper) Ideal sensor / fixed vehicle               | 0.666 / 0.626   | +0.40 / +0.40 | —           |

On matched segments at 60–100 km/h, simulated telematics vibration is **×1.40 below** real and the phone model is ×1.12 below. In the 10–15 Hz band the gaps are 1.07 vs 0.53 in log units.

**Consequences:**

1. **The paper's mechanism is contradicted.** "Transfer depends more on randomising over sensor types than on matching the target sensor" (Results VII-E, Discussion, Table IV) does not hold. A *narrower* model, the phone-holder configuration alone, transfers *better* than the mixture. That configuration includes a 15–40 Hz holder resonance and represents no component of the LiRA setup. The model meant to represent the target device transfers worst.
2. **The headline is fragile.** Four of five plausible simulator variants carry a ≈ +0.4 m/km bias. The 0.44 is one configuration whose absolute gain happens to fit. The robustness sweep agrees: holder resonance alone moves the bias from −0.65 to +0.37 m/km (`results/sim/robustness.csv`). The paper calls these sensor effects "no material effect" for other perturbations and does not flag this one.
3. **Shape versus level.** Adding one gain offset (log intercept) estimated from 5–20 km of real road brings the fixed-vehicle simulator to 0.43, the same as the primary. So the ablation claim that "vehicle randomisation matters" is mostly about level, not shape. Telematics, ideal-sensor and matched-sensor variants stay at 0.51–0.58 after the offset, because their spectral content is wrong (the 10–15 Hz band), not just their gain.

**What to call the 0.44 result.** It is partial transfer plus a fortuitous level match: comparable to the real baseline, partly explainable by a sensor-gain coincidence, and with the physical cause unidentified. It is genuine evidence that half-car simulations over measured profiles carry the *ranking and speed-shape* information. It is **not** evidence that a physically faithful, randomised simulator delivers calibrated IRI for an unseen car without real data.

**A point in the paper's favour that it doesn't report.** I regressed, on real data, log(prediction) on log(IRI) and log(speed) with route fixed effects. The speed elasticity of the predictions at fixed IRI is −0.16 [−0.18, −0.14] for real-trained LightGBM and −0.08 for sim-trained LightGBM. Read observationally, the real-trained model would *fail* the paper's own ±10 % speed criterion on real cars (about −15 % from 40 to 100 km/h), while the sim-trained model would pass (about −7 %). This is the best real-data evidence that simulation provides de-confounded training. It belongs in the paper, with the caveat that attenuation from label noise biases this coefficient for both models.

---

## 6. Value of simulation (the "20 km" claim)

1. **Wrong comparator in the abstract.** The abstract says real data "needs about 20 km to match it", where "it" is the 0.44 model. Real-only at 20 km is 0.456, which does not match 0.439. The 20 km crossover is against the p79+iso model (0.459).
2. **Crossover is imprecise.** It lies between 10 km (0.499) and 20 km (0.456), from 5 draws on 4 routes, with about 10 car passes per km. It is one realisation, not a constant.
3. **Unequal profilometer budgets (main problem).** The simulator used *all* training-route profiles, about 120–145 km per fold, while real-only used k km. The introduction motivates simulation because "each label requires a profilometer run", yet the simulator consumes about 6× more profilometer road. My equal-budget control, simulating only the same k km of blocks:

| Profiled road (km) | Real-only | Sim-only, same blocks |
| ------------------ | --------- | --------------------- |
| 5                  | 0.82      | 0.71                  |
| 10                 | 0.50      | 0.47                  |
| 20                 | 0.46      | 0.47                  |
| 40                 | 0.43      | 0.45                  |

Per km of profiled road, simulation is about as label-efficient as real data: slightly better below 10 km, slightly worse above. What simulation replaces is **co-registered car drives over profiled roads**, not profilometer labels. The Discussion half-says this ("needs profiled roads … but no instrumented drives"). The abstract and Conclusion say the opposite ("replace scarce labels", "replaces about 20 km of labelled road").

Fine-tuning and pooling are implemented correctly, and the test route stays untouched (blocks are sampled from training routes only).

**Verdict.** As stated, the result is not a durable empirical contribution. Restated as "simulation over already-surveyed profiles removes the need for paired car drives, at equal accuracy per km of profiled road, for this car", it is modest but true.

---

## 7. Speed as signal and shortcut

- Speed correlates with the label and is an input. Speed alone gives 0.74, which is about a road-class prior (0.81).
- **The model does sense roughness:** within-route partial Spearman given speed is 0.70–0.90, against −0.02 to 0.42 for speed-only. Supported.
- **Pooled metrics flatter the models.** Pooled Spearman 0.95, R² 0.79 and κ 0.91 are inflated by the urban/motorway separation. Within routes Spearman is 0.72–0.90, and raw RMS ranks almost as well as LightGBM. The abstract should headline within-route figures.
- **Speed-normalisation claims are simulation-only.** The simulator's speed exponent (1.20) differs from the real car's (0.60–0.79). "LightGBM trained on measured profiles is speed-invariant" is shown only in simulation. The real-data analysis in §5 is the missing link.
- **No speed-normalisation leakage:** α is fitted on training routes only (models.py).

---

## 8. Unseen vehicles

- **What "unseen" means here.** Random held-out draws from the *same* uniform parameter ranges (in-distribution interpolation), 30 training vehicles, and a *relative* criterion of at most +10 % ([sim_generate.py:127-148](research_rescue/experiments/sim_generate.py#L127-L148)).
- **LightGBM still generalises in absolute terms.** Its unseen-vehicle MAE (0.88) is better than the seen-vehicle MAE of every estimator except the CNN (0.81). The criterion penalises benefiting from having seen a vehicle, not failing on new ones.
- **The paper contains a successful unseen-vehicle test.** The LiRA zero-shot evaluation is itself one: the Zoe is not among the simulated vehicles, and it worked at 0.44.
- **Missing experiment:** does the seen/unseen gap shrink with 100–300 training vehicles? It is cheap to run, and without it "vehicle generalisation is unresolved" may simply reflect only 30 training vehicles.
- **Verdict:** a useful but over-framed negative result. Moderate.

---

## 9. Statistics

- The bootstrap code is correct, paired and Holm-corrected. The **resampling unit is wrong**: residual autocorrelation at 100 m is 0.25–0.56.
- **Sim vs real paired difference:** p = 0.001 with segment clusters, 0.026 with 1 km blocks, **0.10 with 5 km blocks**.
- **CNN vs LightGBM** holds at all levels (p ≤ 0.001), but is not consistent across routes.
- **MLP vs LightGBM:** not different at any level.
- No route-level inference is possible with n = 4; per-route numbers are shown, which is honest. CIs are conditional on the trained models and ignore training-set variability.
- **Recommendation:** 1 km or 5 km blocks as the primary cluster for *paired* tests (Table S6 does this only for marginal CIs). Report within-route Spearman and MAE as primary, pooled as secondary.

---

## 10. Other moderate issues

- **ARAN "reference uncertainty".** ARAN points are matched within 10 m of the P79 track with **no heading constraint** ([iri_unit_test.py:162-171](research_rescue/evaluation/iri_unit_test.py#L162-L171)). On two-way urban streets that can pull in opposite-lane data, and 42 points exceed 15 m/km. "Urban errors are smaller than the disagreement between two professional devices" therefore rests on an unvalidated alignment. Remove it or validate it.
- **BeamNG non-transfer.** Causes are confounded: invalid labels (shown), 48–68 % duplicated IMU rows, 3 vehicles, one driver. The vibration index trained on BeamNG ranks real segments well (ρ = 0.93) and is mainly off in level (bias −0.73), which fits the label finding. "Authored meshes provide neither realistic roughness nor valid labels" goes beyond what is isolated.
- **PVS claim.** "Speed predicts the quality labels better than vibration" holds against raw RMS and on the bad-vs-regular subtask (352 windows, 72 positives). It does not hold against RMS/√v on good-vs-rest (0.99 vs 0.97). Partially supported, and tangential to IRI.
- **Passes-needed analysis.** It compares different segment subsets (935 / 869 / 486 segments at 1 / 5 / 8 passes).
- **Editorial.** Table S4's caption still says "pre-registered"; the main text says "fixed in advance".

---

## 11. Novelty and literature

| Question                            | Answer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Already done?                       | IRI or roughness estimators trained on randomised half-car or quarter-car simulations:**Jeong et al. 2020 ([25])** trained CNNs on 4-DOF half-car responses of varied vehicles at randomised speeds, validated numerically. Simulation-trained classifiers: [23], [24]. ML on the same LiRA data: Bajic 2021 ([20]), cited but not compared. **Skar & Levenberg 2024** (*J. Transp. Eng. Part B* 150(1) 04023040): quarter-car calibrated to the Renault Zoe, profile inversion on LiRA cars against a laser profilometer. **Not cited**, and it is the closest physics competitor on the *same data*. |
| What is new?                        | (a) Zero-shot sim→real for continuous IRI on**real production cars with profilometer reference, route-disjoint, on public data**. (b) The equal-protocol comparison against a game-engine corpus. (c) Showing that a published-style label correction is not IRI. (d) A speed-confounding analysis with within-route controls.                                                                                                                                                                                                                                                                                        |
| Simulator new?                      | No: a linear half-car plus sensor noise model.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Sensor randomisation new?           | Domain randomisation is standard ([28]). Applying it to sensor models for IRI is a small extension, and its claimed mechanism is contradicted (§5).                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| Value-of-simulation experiment new? | The design is reasonable; its main result is an artifact of unequal budgets (§6).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Benchmark or protocol new?          | Partly. The rules are good practice rather than novel.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| BeamNG negative finding useful?     | Mainly as a caution about labels derived from authored geometry. The simulator-type comparison is not controlled.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| New empirical fact?                 | One, conditional: for one car type, simulated responses over measured profiles of other roads can stand in for paired car data.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Incremental?                        | Yes, as currently framed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |

Jeong et al. 2020 is described in the paper only as "a CNN for calibration-free assessment", which hides that it is the direct precursor of the simulator idea. The Related Work closing sentence ("Compared with this work, we …") needs to name what Jeong et al. and Skar & Levenberg already did.

---

## 12. Reproducibility

**Strong:**

- Public primary data with MD5-verified downloader.
- One-command pipeline; every number in the paper is a generated macro.
- All predictions saved; seeds fixed.
- I reproduced the zero-shot and few-shot numbers exactly from the shipped code.

**Weak:**

- Nothing committed, so the "fixed in advance" timestamps are unverifiable.
- Absolute Windows interpreter paths; no lockfile.
- BeamNG and PVS corpora live in a cloud-synced private folder.
- No released checkpoints (cheap to retrain, so minor).

An independent researcher could reproduce all LiRA-CD results. **Grade: high for this field.**

---

## 13. Claim audit

| #  | Location                  | Claim                                                                    | Status                                                                           |
| -- | ------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| 1  | Abstract, C(i)            | Mesh correction lowers urban IRI by 28 %, so earlier labels were not IRI | SUPPORTED                                                                        |
| 2  | Abstract, C(i)            | Implementation reproduces P79 IRI (r = 1.000)                            | SUPPORTED (algorithm check, as stated)                                           |
| 3  | Abstract                  | GBM 0.42, ρ = 0.95                                                      | SUPPORTED; ρ OVERSTATED as a skill measure (pooled)                             |
| 4  | Abstract, Results         | Better than CNN (0.48)                                                   | PARTIALLY (one-route effect; untuned legacy CNN)                                 |
| 5  | Abstract                  | Speed predicts PVS labels better than vibration                          | PARTIALLY                                                                        |
| 6  | Abstract, Intro           | Sim-only 0.44, "nearly matches" real training                            | SUPPORTED as a measurement; motorway 0.20 vs 0.14 makes "nearly" PARTIAL         |
| 7  | Abstract, Conclusion      | Real data needs about 20 km to match it                                  | OVERSTATED (wrong comparator; unequal budget; 10–20 km range)                   |
| 8  | Abstract                  | Game-engine corpus does not transfer (1.36)                              | PARTIALLY (index: 0.85, ρ = 0.93; cause not isolated)                           |
| 9  | Abstract                  | Learned speed corrections hold only for the training road spectra        | SUPPORTED (simulation only)                                                      |
| 10 | Abstract, Conclusion      | No accurate estimator meets the unseen-vehicle criterion                 | Literally SUPPORTED; the framing "not achieved even in simulation" is OVERSTATED |
| 11 | Abstract                  | Simulation over measured profiles can replace scarce labels              | OVERSTATED (replaces paired drives, not profiles; relies on a gain coincidence)  |
| 12 | C(ii)                     | Calibration and filtering hid diverging predictions                      | SUPPORTED                                                                        |
| 13 | C(iii)                    | Route-disjoint comparison with segment-level uncertainty                 | SUPPORTED; precision OVERSTATED                                                  |
| 14 | Results VII-C             | Urban errors smaller than profilometer disagreement                      | UNSUPPORTED (ARAN alignment)                                                     |
| 15 | Results VII-D             | Within routes, vibration carries information speed lacks                 | SUPPORTED                                                                        |
| 16 | Results VII-E             | Each randomised component matters                                        | PARTIALLY (vehicle effect is mostly level)                                       |
| 17 | Results VII-E, Discussion | Breadth of sensor model matters more than matching the target            | **UNSUPPORTED / contradicted**                                             |
| 18 | Results VII-F             | Sampling rate matters most among perturbations                           | PARTIALLY (holder resonance moves bias more)                                     |
| 19 | Discussion                | Architecture is not where the gains are                                  | SUPPORTED on this dataset                                                        |
| 20 | Discussion                | Results favour randomised simulators over measured profiles              | OVERSTATED                                                                       |
| 21 | Discussion                | Authored meshes give neither realistic roughness nor valid labels        | PARTIALLY                                                                        |
| 22 | Conclusion                | GBM as accurate as anything tried                                        | SUPPORTED                                                                        |

---

## 14. Critical contribution test

**A. The one central contribution.** A leakage-free, route-disjoint, profilometer-referenced evaluation on public real-car data showing that an estimator trained only on half-car simulations over measured profiles of *other* roads approaches one trained on real car data from the same fleet. Everything else is support or diagnosis.

**B. If the CNN were removed.** Everything of value remains, and focus improves. The CNN only serves the post-mortem and the "architecture doesn't matter" remark.

**C. Is the sim-pretraining result novel and important?** The idea is not novel (Jeong et al. 2020). Real-car, profilometer-referenced, route-disjoint confirmation is new and useful. It would be important if shown robust across simulator configurations or vehicles; currently it is shown for one configuration that wins partly by gain coincidence.

**D. Is "replaces ~20 km" a meaningful empirical result?** No, as stated. It is an artifact of unequal profile budgets, compared against a different simulation set than the one quoted, and specific to this dataset's pass density and class mix. The equal-budget curve is the meaningful version, and it shows rough parity.

**E. Does BeamNG's failure give scientific insight?** Mainly it documents an inadequate corpus. The general insight, that labels derived from authored geometry must be validated against a profilometer, comes from RQ1, not from the transfer failure.

**F. What kind of paper is it?** A benchmark/evaluation paper with a sim-to-real component, plus a diagnostic post-mortem of an unpublished pipeline. It is not a methods paper.

**G. Is the positioning clear?** No. Three stories compete:

- the post-mortem (abstract opening, contributions i–ii);
- the benchmark (iii);
- sim-to-real (iv and the title).

A reader cannot tell which is the paper. Contributions about an unpublished pipeline are of interest mainly to its authors.

**H. Could a reviewer fairly say "many careful experiments, no sufficiently novel contribution"?** Yes, and fairly:

- every method component is standard and has precedent;
- (i) and (ii) concern a pipeline nobody else uses;
- the positive result is one dataset, one car, one simulator configuration, with a misidentified mechanism;
- the negative results are either confounded (BeamNG) or tested in an in-distribution design (vehicles).

**I. Could a reviewer say "the real contribution is the controlled evidence about when simulation helps"?** Yes, but the paper does not establish *when*. It shows one success and several failures without identifying the condition. My analyses suggest the condition is a match of sensor spectrum and gain to the real data. That is a hypothesis the paper could test with existing data but currently gets wrong.

**J. Strongest fully supported interpretation.** On four public profilometer-referenced routes driven by one car model:

- Gradient boosting on hand-crafted vibration and speed features reaches 0.42 m/km on unseen routes; within routes it ranks segments well beyond what speed explains.
- A model trained only on linear half-car simulations over measured profiles of other roads, with one particular sensor-model mixture, reaches 0.44 m/km with less speed confounding than the real-trained model.
- Pooled metrics, test-domain calibration, prediction filtering and an unvalidated label correction can each manufacture apparent accuracy.

**K. Strongest interpretation not justified.** None of these is shown:

- that randomised simulation is a general substitute for real calibration data;
- that sensor breadth rather than fidelity drives transfer;
- that simulation reduces the need for *profilometer* labels by about 20 km;
- that game-engine simulation cannot work;
- that vehicle generalisation fails;
- anything about other cars, phones or cities.

**One-sentence summaries:**

1. **Most favourable, defensible:** "A carefully controlled, route-disjoint study on public profilometer-referenced car data showing that, for one car type, an IRI estimator trained only on half-car simulations over measured profiles of other roads approaches one trained on real car data (0.44 vs 0.42 m/km), together with evidence that label derivation, test-domain calibration and speed confounding can manufacture apparent accuracy."
2. **Neutral:** "An evaluation of standard vehicle-based IRI estimators on four LiRA-CD routes, finding gradient boosting on hand-crafted features as good as anything tried, and reporting one simulator configuration that transfers nearly as well as real training alongside several simulation results that do not transfer or generalise."
3. **Most sceptical:** "A post-mortem of the authors' own unpublished pipeline attached to a single-dataset benchmark, in which the one positive sim-to-real result depends on an uncalibrated sensor-model component and is explained by a mechanism the authors' own data contradict."

---

## 15. Conference review

1. **Summary.** As in §0 and §14 J.
2. **Main contribution.** Real-car, route-disjoint evidence that simulation over measured profiles can stand in for paired car data for one car type.
3. **Strengths:**
   - Exemplary protocol hygiene: no leakage, no filtering, honest negative results, disclosed deviations.
   - Public data and full reproducibility (verified).
   - A useful speed-confounding analysis with within-route controls.
   - Valid labels, with a clear demonstration that an invalid correction is not IRI.
4. **Major weaknesses:**
   - (B1) The mechanism of the central result is contradicted, and the result is fragile across simulator variants.
   - (B2) The value-of-simulation claim is confounded by profile budget, and the abstract's comparator is wrong.
   - (B3) Four routes, one car, shared vehicles across routes.
   - (B4) Closest prior work missing (Skar & Levenberg 2024) or under-described (Jeong et al. 2020); no comparison with Bajic 2021.
5. **Minor weaknesses:** segment-level inference; pooled metrics headlined; ARAN comparison; BeamNG cause not isolated; framing of the unseen-vehicle result; one-route CNN effect; "pre-registered" caption.
6. **Technical soundness:** high in execution, medium in interpretation.
7. **Novelty:** low to moderate.
8. **Experimental quality:** high for internal validity, low for external validity.
9. **Statistical quality:** correct implementation, wrong unit, no route-level inference.
10. **Reproducibility:** high.
11. **Clarity:** good sentence level; diffuse positioning.
12. **Reviewer concerns:** §17.
13. **Required changes:**
    - Replace the "breadth" mechanism with the sensor-half and shape/level decomposition.
    - Add the equal-profile-budget curve and restate the 20 km claim.
    - Cite and position Skar & Levenberg 2024 and Jeong et al. 2020.
    - Use block-level paired tests.
    - Headline within-route metrics.
    - Drop or validate the ARAN argument.
    - Add the real-data speed-elasticity analysis.
14. **Optional improvements:**
    - Unseen-vehicle test as a function of the number of training vehicles.
    - BeamNG index result in the abstract.
    - Shorten the post-mortem.
    - Compare with a calibrated quarter-car inversion if feasible.

**Score: 4/7, Borderline.** At an applied transportation or sensing conference this leans weak accept on rigour; at a selective venue it leans weak reject on novelty.

**What separates 4 from 5.** The required changes in item 13. All need only existing data. They turn an over-claimed positive result into a correctly explained, robust one, and fix the positioning.

---

## 16. Journal review

**Journal-ready?** No.

**New experiments needed:**

- **With existing data:** sensor-half and spectral diagnosis of *why* the phone configuration matches (real vs simulated PSDs per band and speed); equal-budget curves; gain-calibration protocol; number-of-vehicles sweep; route-level analysis.
- **Needing new data or a new design** (the real blocker for archival durability):
  - A held-out real dataset, a second vehicle, or a second sensor, to test a simulator design *frozen now*. All four routes have already informed the interpretation.
  - A comparison with a calibrated physics inversion on the same cars.

**Is the contribution substantial enough for archival publication?** Only after reframing to "what simulation provides (ranking, speed shape) and what it does not (absolute gain without matching sensor dynamics)", and after at least one out-of-sample confirmation.

**Is the current evidence enough?** Not for the durability a journal expects. The conclusion rests on one sensor-model coincidence and two routes per class.

**Score: 3/7, major revision** (reject-and-resubmit at a strict journal).

**What separates 3 from 4:** the existing-data analyses above plus the reframing. **From 4 to 5:** one independent real confirmation (new vehicle, sensor or city).

---

## 17. Conference vs journal

|                        | Conference                                                          | Journal                                                                      |
| ---------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Scientific quality     | Sound execution; misexplained central result is fixable             | Same, plus mechanism must be*demonstrated* (PSD/gain diagnosis)            |
| Novelty                | Real-car confirmation of a known idea; enough if clearly positioned | Needs a general insight (when simulation helps), not one success             |
| Methodology            | Protocol is a strength                                              | Protocol fine; no untouched test set for simulator design is a problem       |
| Experiments            | Sufficient after equal-budget and sensor-half additions             | Needs out-of-sample vehicle/sensor/city, or at least a held-out design check |
| Statistics             | Block-level paired tests suffice                                    | Plus route-level or hierarchical treatment and power discussion with n = 4   |
| Reproducibility        | Exceeds expectations                                                | Commit, pin environment, release corpora or document access                  |
| Generalisation         | Scope limits acceptable if stated                                   | Single car and city is the main barrier                                      |
| Literature             | Add Skar & Levenberg; reposition Jeong                              | Plus quantitative comparison with a calibrated inversion and Bajic 2021      |
| Current readiness      | One revision cycle with existing data                               | New data needed                                                              |
| Main remaining blocker | Mechanism and claim wording (§5, §6)                              | Independent real confirmation of the transfer                                |

---

## 18. The single most dangerous reviewer objection

> "The 0.44 m/km zero-shot result is not evidence that a randomised, physics-based simulator transfers to real cars. It is one simulator configuration whose absolute gain happens to match the target car. The sensor model meant to represent the target device transfers at 0.68. A phone-holder model, which represents nothing in the LiRA setup, transfers at 0.41. Four of five plausible variants carry a +0.4 m/km bias. With four routes and no held-out data, a reader cannot tell whether a new vehicle or sensor would get 0.44 or 0.69, and the paper's 'sensor breadth' explanation is contradicted by its own data."

**Classification: C** (not answered, but answerable with existing data). The paper reports the 0.69 variant (partial B), but its interpretation goes the wrong way. The generalisation part of the objection is **D** (new experiment).

**Smallest analysis that most increases reviewer confidence.** Report the sensor-half decomposition and a shape/level decomposition: zero-shot, then plus one gain offset from 1–5 km, for every simulator variant. Add the real-vs-simulated PSD comparison per band. Then reframe the practical recipe as "simulation over measured profiles plus a few km of real gain calibration", evaluated across all variants, not only the lucky one. This takes about an hour of compute with the scripts I left in the scratchpad. **Do not adopt phone-only as the new primary configuration:** it was found by looking at the test routes.

---

## 19. Final verdict

**Conference:** Acceptance score **4/7**. Current status: **Borderline (major revision of claims, no new data needed).**

**Journal:** Acceptance score **3/7**. Current status: **Major revision (needs independent real confirmation).**

- **Strongest part:** the evaluation itself. It is leakage-free, uses public profilometer-referenced data, reproduces exactly, and has within-route speed controls.
- **Weakest part:** the explanation of why simulation transferred (§5) and the value-of-simulation claim (§6).
- **Most novel part:** real-car, route-disjoint zero-shot transfer from simulated responses over measured profiles of other roads.
- **Most vulnerable claim:** "transfer depends more on randomising over sensor types than on matching the target sensor", followed by "replaces about 20 km of labelled road".
- **Single most important experiment:** an independent real-car confirmation (another vehicle, sensor or road network) of a simulator design frozen *before* seeing it. Within existing data: the sensor-half, shape/level and PSD diagnosis.
- **Single most important writing change:** state one contribution. Simulation over surveyed profiles reproduces ranking and speed shape and can replace paired car drives for this car; absolute calibration depends on matching sensor dynamics, which happened here through an unintended component. Drop "breadth" and "replaces scarce labels".
- **Publishable?** Yes, as a careful empirical evaluation at an applied venue, once the interpretation is corrected. Not yet as a durable archival claim about sim-to-real IRI estimation.
- **To gain one point:**
  - Conference 4 → 5: the required changes in §15, all with existing data.
  - Journal 3 → 4: those changes plus the PSD diagnosis, the number-of-vehicles sweep and a comparison with a calibrated inversion.
  - 4 → 5 at either venue: one real out-of-sample confirmation.

**Separate compression issue (not scored).** The PVS section, the BeamNG protocol forensics (Table IV bottom) and the post-mortem framing in the Introduction take about 1.5 pages that serve the authors' history more than the contribution. They belong in the supplement.

---

**Sources (literature check):** [Jeong et al. 2020, calibration-free CNN](https://www.researchgate.net/publication/340232560_Convolutional_neural_networks_for_pavement_roughness_assessment_using_calibration-free_vehicle_dynamics) · [Skar &amp; Levenberg 2024, Road Profile Inversion from In-Vehicle Accelerometers](https://orbit.dtu.dk/en/publications/road-profile-inversion-from-in-vehicle-accelerometers/) · [Bajic et al. 2021, arXiv:2107.01199](https://arxiv.org/abs/2107.01199) · [LiRA-CD (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10375556/) · [Shangguan &amp; Lu, J. Comput. Civ. Eng.](https://ascelibrary.org/doi/10.1061/JCCEE5.CPENG-6782)

I didn't change any repository file. I did save the verified findings to memory for future revision sessions. If you want this review as a shareable page for your co-author, I can publish it as an artifact.
