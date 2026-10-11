# Independent Review V3

**Paper:** "Simulated Drives over Measured Road Profiles for Car-Based IRI Estimation: What Transfers and What Needs Calibration" (N. Singhal, G. Bhola)
**Version reviewed:** `paper/main.pdf` (10 pp.) and `paper/supplementary.pdf` (14 pp.), compiled 2026-10-03 23:38; sources `paper/main.tex`, `paper/sections/*.tex`, `paper/supplementary.tex`, macros `paper/numbers_v2.tex`
**Review date:** 2026-10-10. Review only: no paper source, script, configuration, dataset or result was modified.

**What I inspected.** The full main paper and supplement (rendered PDFs and LaTeX sources); `evaluation/PROTOCOL_V2.md` and `evaluation/FINAL_EVALUATION_PROTOCOL.md`; the simulator, sensor model, preprocessing, features, models and statistics code in `common/`; the v2 analysis scripts in `experiments/v2/` and the v1 drivers they reuse (`experiments/sim_generate.py`, `experiments/exp_lira.py`); the result files in `results/v2/` and `results/lira/`; the LiRA-CD car readme; the earlier review `review/first.md`; the v2 audit documents (`FINAL_REPORT_V2.md`, `CLAIM_AUDIT_V2.md`, `REVIEWER_AUDIT_V2.md`, `REVISION_PLAN_V2.md`, `references/REFERENCE_AUDIT.md`). I treated the earlier audits as claims to check, not as evidence.

**What I ran.** Read-only analyses of existing data and results, plus two re-fits that use the paper's own code paths, configuration and paired draws: a pooled simulation+real training arm and a band-limited zero-shot retraining. Scripts and outputs are in `review/v3_checks/` (new folder; see its README). Each check first reproduces a published number as a sanity check (Section J).

**Labels used below.** *Verified*: reproduced from data or code, or read in a primary source. *Plausible*: supported by the evidence but not demonstrated. *Severity*: High = changes an abstract-level conclusion; Medium = changes how a section or secondary claim should be read; Low = presentation.

---

## A. Executive summary

The paper asks what an IRI estimator trained on simulated drives over measured road profiles transfers to a real production car, and how much paired real data it still needs. It answers on LiRA-CD (Renault Zoe cars with an AutoPi telematics unit; four Copenhagen routes; 1,678 segments of 100 m). The design uses leave-one-route-out evaluation, IRI labels recomputed from the P79 laser profiles, nine simulator variants over measured profiles, level calibration from k km of paired drives, an equal-profile-budget comparison, fixed-road speed elasticities, and same-segment comparisons of real and simulated vibration spectra.

This is a careful and unusually transparent empirical study. I found no leakage in the code paths behind the headline numbers. Every headline number I traced reproduces from the shipped results. Inference is dependence-aware, and the authors report unfavourable results and correct their own earlier claims. The weaknesses are interpretive rather than methodological, and none of them needs new data.

Four issues matter.

1. **The value-of-simulation conclusion depends on how simulation and real data are combined (High).**
   - v2 combines them only through a level offset or an affine output map. The v1 protocol pre-specified a "simulation + real" training arm, implemented and reported in v1 as pooled LightGBM with balanced weights. v2 dropped it without comment.
   - I re-ran that arm on the paper's own 20 paired draws. The three worst-matched variants (V1, V3, V5) beat real-only LightGBM at 10 km (0.467–0.476 vs 0.523 m/km; better in 18–19 of 20 draws) and at 20 km (0.442–0.447 vs 0.461; 16–18 of 20). The spread between variants nearly disappears.
   - The paper's own affine arm already beats real-only at 10 km for all three variants.
   - So "with 10 km or more, real drives alone beat the three variants with the largest deficit" and "how many it saves depends on how well the simulated vibration matches the car" describe level-offset calibration, not the simulators.
2. **The mechanism of the level error is over-attributed and mislocated (Medium–High).**
   - V4 uses V0's sensor mixture, holder resonance included, with one mid-range vehicle, and its bias is +0.40 m/km against V0's +0.01. V0's level therefore did not arise "only because half of its passes carried a phone-holder resonance".
   - Across the nine variants, the overall vibration gain explains the bias at least as well as the 10–15 Hz band (linear R² 0.78 vs 0.71). The 5–10 Hz band (Spearman 0.80) is not reported.
   - A band-limited retraining supports a sharper and stronger version of the authors' idea. With features limited to content below 10 Hz, the zero-shot bias of the eight sensor variants collapses from a 0.52 m/km range to 0.14 m/km. Removing only the 10–15 Hz band feature changes nothing, and V4 stays at +0.28 m/km.
3. **The closest prior work is missing (Medium).**
   - Nitsche et al. (2014) trained ML on simulated vehicle responses and validated it on a real probe vehicle against an inertial profilometer.
   - Ngwangwa et al. (2014) applied a simulation-trained network to experimental vehicle data.
   - Wu et al. (2023) calibrated a full-car model with impact tests and validated simulation-derived IRI relations on real roads.
   - Jeong & Jo (2024) validated a deep IRI estimator on 29 real vehicles.
   - The introduction's "what is missing" sentence must be narrowed. The paper's own contribution stays distinct.
4. **Metrics and denominators blur the story (Medium).**
   - The abstract mixes within-route MAE (0.39, 0.42) with pooled MAE (0.42–0.56, 0.68).
   - "5 km of paired drives" means 4.9 km of profiled road driven about ten times per segment (about 475 segment-passes). The paper never says this.
   - Class biases in m/km hide that V0 over-predicts motorway IRI by about 16% (mean log level +0.145, against +0.016 for the real-trained model).

Several potential objections did not survive checking, and they count in the paper's favour.
- The fixed-road speed results are robust to telematics-unit fixed effects and to a control for within-pass speed variability.
- The simulator's value is not reducible to a fitted slope. A no-simulator vibration index with the car's label-free speed exponent, calibrated on the same 5 km, reaches only 0.78 m/km against 0.42–0.56.
- The claim that an untrained statistic "ranks as well" holds on average. A paired test shows a road-class pattern that the text should mention.

One minor bug: the M7 baseline is evaluated on only the HH direction of M13 (119 of 228 segments).

**Short answers to the review questions.**
1. *Central contribution:* empirical evidence on simulation-to-real transfer, decomposed into ranking, level and speed dependence, plus the paired-data requirement (Section C).
2. *Technically sound and clearly communicated:* sound in execution. Communication is precise but over-compressed, and two interpretive claims overreach (D1, D2).
3. *Experiments sufficient for the claims:* yes for the within-dataset claims, once the pooled arm is reported and the mechanism claim is narrowed. No for generality, which the paper does not claim.
4. *Related work accurate and complete:* accurate for what is cited; incomplete for the closest simulation-trained, real-validated work (D3).
5. *Weaknesses a competent reviewer would raise:* D1–D5.
6. *Addressable with existing data and code:* all except D5.
7. *Improvements that materially strengthen the paper:* the pooled arm, the band-limited intervention, the level decomposition, and the related-work repositioning (Section G).
8. *Minor or not worth addressing:* listed at the end of Section D and under "Not recommended" in Section G.

---

## B. What the paper does well

Preserve all of the following.

1. **Valid reference labels.** IRI is recomputed from the raw P79 laser profiles with an implementation that reproduces the P79's own IRI (r = 1.000, bias +0.02 m/km, 1,520 segments). An inconsistent reference file (CPH6-HH) is detected and handled, and simulated units are labelled with the same code. This removes the label problem that sank the earlier game-engine study.
2. **Leakage-free, route-disjoint protocol.** Both directions of the test route are held out together. In the code, no test-route data reach training, calibration or model selection: `variant_training_set(vid, test_route)` drops the test route's profiles, and `sample_blocks(U, tr, ...)` draws calibration blocks from training routes only. The evaluation unit is the segment mean over passes, and nothing is filtered or capped.
3. **A design that only this dataset allows.** LiRA-CD publishes the raw laser profiles, so the simulator can drive exactly the segments the real cars drove. This enables same-segment, same-speed-band comparisons of real and simulated spectra (Fig. 3a, Table S15), which are rare and informative. I found no other public dataset that pairs production-car accelerations with raw profilometer profiles, and this is worth stating as a positioning point (Section F).
4. **Systematic simulator variation, fully reported.** Nine measured-profile variants plus synthetic-profile variants and a 2×2 sensor factorial. A protocol rule requires statements to rest on the range over all variants rather than the best one (`PROTOCOL_V2.md` §0, rule 2).
5. **Ranking separated from level.** The untrained-statistic control (E10) makes a methodological point the field needs: within-route rank correlation cannot detect calibration error.
6. **An equal-profile-budget design.** It separates profile information from paired drives and answers the obvious objection to "simulation replaces labels". Its variant-dependent answer is reported honestly.
7. **Two real-only comparators**, including a three-parameter index suited to very small samples (E9).
8. **Fixed-road speed elasticity from naturalistic repeated passes.** An elegant estimand that sidesteps the speed–roughness confounding of naturalistic driving. I verified that it is robust (E5).
9. **Dependence-aware inference.** The residual autocorrelation is reported, a 5 km block bootstrap is the decision rule, and route-level intervals are descriptive. The paper shows explicitly that segment-level intervals would have misled (V0 vs real).
10. **A broad, honest baseline ladder:** map-only road-class prior, speed only, physics index, calibrated quarter-car inversion, learned models, and simulation-trained estimators.
11. **Transparency.** Evidence classes, a protocol frozen before the v2 analyses with dated addenda, explicit corrections of earlier claims (sensor breadth; "about 20 km"), and negative results (BeamNG, PVS) moved to the supplement rather than dropped.
12. **Reproducibility.** Every number is a generated macro, all macros resolve, and every published number I re-derived matched (Section J).

Do not change the leave-one-route-out design, the label pipeline, the 5 km block decision rule, the equal-budget design, the fixed-road elasticity estimand, or the practice of reporting every variant and draw. No new estimator architecture is needed.

---

## C. Central contribution and novelty

**Strongest defensible contribution after revision.** On public profilometer-referenced data from one production car, with held-out routes and dependence-aware inference:

- (a) A randomised half-car simulator driven over measured profiles of other roads reproduces the car's within-route vibration-to-IRI mapping.
- (b) Its absolute level is not reliable. It depends on simulator choices that cannot be validated without real data: the simulated sensor path, through vibration above about 10 Hz, and the simulated vehicle population.
- (c) Simulation over all profiled roads, combined with a few kilometres of paired drives, approaches full real training and beats training on the same paired drives alone.
- (d) Same-segment comparisons show where the simulated vibration departs from the car's: above 10 Hz, and in how it scales with speed.

The dominant contribution is **empirical evidence about simulation-to-real transfer, decomposed into ranking, level and speed dependence, together with the real-data requirement.** The secondary contribution is methodological:
- within-route ρ is blind to calibration;
- spatial blocks, not segments, should be resampled;
- fixed-road elasticities measure speed dependence on real roads;
- simulated and real spectra can be compared on the same segments.

**Consistency of framing.** The title ("What Transfers and What Needs Calibration"), abstract, introduction ("the answer has three parts"), contribution list and conclusion tell the same story. This is a real improvement over v1. Two contribution statements claim more than their evidence:

- (ii) "a sensor factorial and a spectral comparison ... that locate the level error". The evidence is associational, and the factorial misses the vehicle-population effect (D2).
- (iii) "the amount of paired real data that simulation replaces ... for every simulator variant". This was measured for one way of combining the data only (D1).

**Novelty and differentiation.** The general idea is not new:
- training on simulated vehicle responses over measured profiles and testing on a real vehicle: Nitsche et al. 2014 (weighted longitudinal profile), Ngwangwa et al. 2014 (profile reconstruction and roughness classes), Xing et al. 2025 (roughness classes);
- using a calibrated vehicle simulation to set an IRI–vibration relation: Wu et al. 2023, and response-type calibration in general (Sayers TP 46).

As far as I can find, the following are new:
1. continuous IRI on held-out roads of a public dataset, for a production telematics unit;
2. systematic variation of simulator components showing that the level fails while the within-route shape transfers, with a same-segment spectral diagnosis;
3. the paired-data requirement, measured against both equal-profile-budget and equal-paired-drive comparators;
4. fixed-road speed elasticities on real roads.

This is a meaningful empirical contribution, and a careful empirical study does not need a new architecture. The novelty problem is one of positioning, fixable in writing (D3). It does not undermine the paper.

---

## D. Major issues

### D1. Value-of-simulation conclusions depend on the combination method, and a pre-specified arm was dropped

*Severity: High. Confidence: Verified.*

**Evidence.**

- The v1 protocol (`evaluation/FINAL_EVALUATION_PROTOCOL.md` §1) specifies the value-of-simulation comparison as "real-only vs. simulation-pretrained + real fine-tuned".
- v1 implemented it as `sim+real LightGBM (balanced weights)` (`experiments/exp_lira.py:289-290`). It reported in `paper/v1_archive/sections/results.tex:104` that "pooling them with the simulated units gives the lowest mean error at every budget" (`results/lira/fewshot_pooled_summary.csv`: 0.46 / 0.46 / 0.45 / 0.44 / 0.43 m/km at 1 / 2 / 5 / 10 / 20 km; V10 set; 5 draws).
- Neither the v2 paper nor its supplement reports this arm or explains why it was dropped. `PROTOCOL_V2.md` says "Nothing in v1 is changed".
- Check `c4` re-runs the same arm with v1's weighting and the paper's first LightGBM configuration on the paper's 20 draws (`default_rng(1000*d+7)`). Pooled segment MAE in m/km; in parentheses, the number of draws in which the pooled arm beats real-only:

| Variant | k (km) | Real-only | + level offset (paper) | + affine (paper) | Pooled sim+real (check c4) |
|---|---|---|---|---|---|
| V0 | 5 | 0.678 | 0.425 | 0.475 | 0.452 (20/20) |
| V0 | 10 | 0.523 | 0.425 | 0.451 | 0.453 (19/20) |
| V0 | 20 | 0.461 | 0.422 | 0.432 | 0.435 (20/20) |
| V1 | 5 | 0.678 | 0.528 | 0.497 | 0.467 (20/20) |
| V1 | 10 | 0.523 | 0.548 | 0.496 | 0.467 (18/20) |
| V1 | 20 | 0.461 | 0.542 | 0.477 | 0.443 (17/20) |
| V3 | 10 | 0.523 | 0.560 | 0.474 | 0.476 (18/20) |
| V3 | 20 | 0.461 | 0.554 | 0.455 | 0.447 (16/20) |
| V5 | 10 | 0.523 | 0.585 | 0.498 | 0.469 (19/20) |
| V5 | 20 | 0.461 | 0.579 | 0.480 | 0.442 (18/20) |

- The paper's own affine arm (`results/v2/paired_vs_real.csv`, arm `sim_all_aff`) already beats real-only at 10 km for the three worst variants: V1 −0.027 m/km (11 of 20 draws), V3 −0.048 (14/20), V5 −0.024 (11/20). Table S14 shows the affine arm only at 5 and 20 km.
- The 20 km margins are small. The pooled advantage there is −0.014 to −0.019 m/km. Per route, pooled V1, V3 and V5 are slightly worse than real-only on M3 (+0.007 to +0.016) and clearly better on CPH1 (−0.05 to −0.06). Draw counts carry no test-route uncertainty; the paper notes this itself.

**Why it matters.** Several passages present the paired-data requirement as a property of simulator fidelity: the last two sentences of the abstract, the introduction's "three parts" paragraph, the closing paragraph of Sec. V-D, the conclusion, and the road-agency recipe in the Discussion. With joint training the dependence on fidelity is much weaker. At 5 km, pooled MAE is 0.452–0.473 for all four variants tested.

For V0 the level offset is slightly better than pooling (0.425 vs 0.452 at 5 km). The honest recipe is therefore: a level offset suffices when the simulated vibration matches the car; joint training is the robust choice when it does not.

**Remedy.** Report the pooled arm for every measured-profile variant (and V10, for continuity with v1) at all k on the same draws. Label its status clearly: the design was pre-specified in v1 but is evaluated on known routes, so it is class R. Add it to Fig. 4b, Table III and Table S14, and restate the claims (handoff L1–L4). Keep the level-offset analysis as the diagnostic of shape versus level, which is the job it does well.

### D2. The mechanism of the level error is over-attributed and mislocated

*Severity: Medium–High. Confidence: Verified for the facts; Plausible for the refined mechanism.*

**Evidence.**

**(a) V4 contradicts "only because".**
- V4 (`p79_train_fixedvehicle`) is generated by `drive(rngA, P79, [(..., fixed_veh)]*30, ...)` with the default `sensor_kind="mix"` (`experiments/sim_generate.py:170`). `PROTOCOL_V2.md` §3 lists it as "one mid-range vehicle, V0 sensor mixture", so it carries the holder resonance in half its passes, exactly as V0 does.
- Its zero-shot bias is +0.397 m/km (urban +0.389, motorway +0.407), against +0.010 for V0.
- The abstract says V0 "matched it ... only because half of its passes carried a phone-holder resonance", and the Discussion says "V0's level came from the holder resonance in half of its passes". Both statements need the vehicle population as a second necessary ingredient.

**(b) The 10–15 Hz band is not distinguished from broadband gain.**

From `results/v2/band_gain.csv` and `summary_variants.csv` (check `c1`), the correlation over V0–V8 between each feature's real/simulated amplitude ratio and the pooled zero-shot bias is:

| Real/simulated ratio of | Spearman | Pearson |
|---|---|---|
| 0.5–2 Hz band | 0.22 | 0.32 |
| 2–5 Hz band | 0.25 | 0.44 |
| 5–10 Hz band | 0.80 | 0.81 |
| 10–15 Hz band | 0.97 | 0.85 |
| overall RMS | 0.88 | 0.88 |

- The paper reports only the first two contrasts (0.22 and 0.25) next to 0.97.
- A linear fit of bias on the overall-RMS ratio has R² 0.78, against 0.71 for the 10–15 Hz ratio.
- V4's 10–15 Hz ratio is close to V0's (1.93 vs 1.86). Its overall-RMS ratio (1.23 vs 1.12) and 2–5 Hz ratio (2.09 vs 1.80) are not. V4's bias is therefore a broadband-gain effect, and V4 is the largest residual of the 10–15 Hz fit (+0.20 m/km).
- In log-level terms rather than m/km, the Spearman correlations are 0.90 (10–15 Hz), 0.83 (overall RMS) and 0.80 (5–10 Hz) (check `c1b`).
- The nine variants are not independent: V0 is a mixture of V1 and V2, and V6 shares V2's phone-like sensor.

**(c) An interventional check supports a sharper version.**

I retrained zero-shot LightGBM for V0–V8 with the paper's loaders and first configuration (check `c8`). The full feature set reproduces Table II exactly (V0 0.439 ... V5 0.687 m/km).

| Feature set | Pooled zero-shot bias across V0–V8 (m/km) | Reading |
|---|---|---|
| all 13 features (paper) | −0.09 to +0.43 (spread 0.52) | — |
| all except the 10–15 Hz band | −0.07 to +0.44 (spread 0.51) | no change |
| only content below 10 Hz (speed, speed CV, bands 0.5–2, 2–5, 5–10 Hz) | eight sensor variants −0.19 to −0.05 (spread 0.14); V4 +0.28 | sensor-variant differences collapse; V4 does not |

- The sensor-path effect therefore sits in simulated energy above 10 Hz. That energy reaches the estimator through broadband features (log RMS, 95th percentile, maximum, RMS above 1 Hz, RMS at wavelengths below 5 m), not through the 10–15 Hz band feature itself.
- The vehicle population moves the level through the lower bands.
- Band-limiting has a cost. After a 5 km level offset, well-matched variants get worse (V0 from 0.425 to 0.508 m/km), and within-route ρ drops from about 0.83 to 0.80. Correctly simulated high-frequency content carries useful information.

**Why it matters.** The abstract, Sec. V-C, the Discussion and the Conclusion present "a deficit of simulated vibration at 10–15 Hz" as the thing the level follows, and recommend checking it before trusting a simulator. The evidence supports two separate ingredients: simulated energy above 10 Hz from the sensor path, and the vehicle population. The intervention is much stronger support than a nine-point rank correlation.

**Remedy.**
1. Reword "only because" to name both ingredients, and report V4 in the Discussion's correction paragraph.
2. Report all five correlations (Spearman and Pearson) in Table S16 or the text.
3. Add the band-limited intervention as a class E diagnostic, including its accuracy cost (handoff L5, L6).
4. In the practical advice, speak of "simulated vibration above 10 Hz" and of overall gain, not of a single band ratio.

### D3. Positioning against the closest prior work

*Severity: Medium. Confidence: Verified bibliographic details; the training data of Jeong & Jo (2024) are known from the abstract only.*

**Evidence.** The introduction says: "Estimators trained this way have been validated in simulation [7], [8] or, for roughness classes, with a real-vehicle test [9] ... What is missing is evidence on real cars, on roads not used for training, of what a simulation-trained IRI estimator actually transfers and how much paired real data it still needs." Four close works are not cited (details and links in Section F):

- **Nitsche et al. (2014)** trained MLP, SVR and random-forest regressors on simulated vehicle responses and validated them on a real probe vehicle against an inertial profilometer. Their target was the weighted longitudinal profile. Bajic et al. (2021), whom the paper cites, single out this study for exactly that design.
- **Ngwangwa et al. (2014)** applied a simulation-trained neural network to experimental Land Rover data. The paper cites only their 2010 numerical study.
- **Wu et al. (2023)** updated a full-car model from a few impact tests, derived a linear IRI–RMS relation by simulation, and validated it on real roads (mean IRI difference 0.5 m/km per 100 m). This is a direct alternative to "a level from 5 km of paired drives".
- **Jeong & Jo (2024)** report full-scale experimental validation of their deep IRI estimator (IRI-Net; 29 real vehicles; inertial-profiler reference). Per the abstract it is trained on real data; the split should be checked in the full text.

**Why it matters.** A reviewer who knows the LiRA literature will know Nitsche et al. through Bajic et al. The gap sentence as written invites a novelty objection that the paper can easily avoid.

**Remedy.** Cite and differentiate these works (suggested text in Section H). Narrow the gap statement to something like: "evidence, for continuous IRI from a production car on held-out roads of public data, of which parts of a simulation-trained estimator transfer, which simulator choices set its level, and how much paired data must accompany the simulation".

### D4. Metric and denominator ambiguities change how the results read

*Severity: Medium. Confidence: Verified.*

**(a) Within-route vs pooled MAE.**
- The abstract quotes within-route MAE for the real model (0.39) and V0 (0.42), then pooled MAE for calibrated simulation (0.42–0.56) and for real-only training on 5 km (0.68). A reader compares 0.42–0.56 with 0.39 and sees a gap.
- In pooled terms the best variants equal the real model (0.42 vs 0.42).
- In within-route terms, after a 5 km offset, V0 reaches 0.400, V2 0.395 and V7 0.405 m/km, against 0.395 for the real model (`variants_calibration.csv`, mean over the four routes).
- `PROTOCOL_V2.md` §2 declares within-route metrics primary, yet Sec. V-D reports pooled MAE only.

**(b) What "k km of paired drives" means.** At k = 5 the sampler selects 4.9 km of distinct profiled road with, on average, 475 segment-passes (range 301–640). That is about 9.7 passes per 100 m segment, or roughly 47 km of instrumented driving (`value_of_simulation.csv`, columns `km_real` and `n_real_units`). The paper never states this, and it is what determines the practical cost.

**(c) Level in m/km by class.**
- Table II and Fig. 2b report biases in m/km.
- V0's "matched" pooled level (+0.01) comes from cancellation: urban −0.12, motorway +0.17 m/km.
- In log terms (the `level_*` columns of `variants_zeroshot.csv`, which is the protocol's own R3 estimand), V0 is +0.006 on urban and +0.145 on motorway routes, an over-prediction of about 16% on motorways. The real-trained model is −0.013 and +0.016.

**Remedy.**
- Label every MAE in the abstract and key text as within-route or pooled.
- Add within-route values to Table III and Fig. 4.
- Define k km and its pass density in the Method section and the Table III caption.
- Add the mean log level per class, or a relative bias, to Table II (handoff L7, L8).

### D5. Structural limitations (acknowledged)

*Severity: High for generality, but correctly scoped. Confidence: Verified.*

The study has one car model and one sensor type on four routes, and road class is confounded with route. Every real-data result except the V0 comparison was analysed after the test routes were known, some after an external review had pointed at the sensor model. The paper states all of this clearly (Limitations; Evidence classes; `FINAL_REPORT_V2.md` §I). It cannot be fixed with existing data, and it does not invalidate the within-dataset findings.

The remedy is framing. Present the variant, spectral and calibration results as diagnostics that generate hypotheses, and give the confirmatory design concretely: freeze the simulator, the calibration protocol (k, sampler, combination method) and the analysis code, then test on a new car type or city. This limitation is acceptable for an applied venue.

### Potential criticisms examined and set aside

These need no further effort in the revision.

- **Leakage or test-route reuse.** None found (Section B, item 2).
- **Vehicle overlap favouring the real-trained model.** The authors' unit-disjoint check answers it (Table S7).
- **Speed results confounded by the telematics unit or driving dynamics.** Robust (E5, check `c6`).
- **"The simulator only supplies a slope or speed exponent."** Refuted (check `c2`).
  - A no-simulator index, log IRI = a + b·log(RMS/v^α_car), calibrated on the same 5 km, reaches 0.78 m/km. Here α_car is the car's label-free within-segment speed exponent, estimated from training-route passes (0.59–0.72).
  - With α fixed at 0.5 the same index reaches 0.92 m/km (affine calibration) or 0.98 (offset only).
  - Simulation-trained LightGBM with an offset reaches 0.42–0.56 m/km. Even the simulation-fitted three-parameter index with an offset reaches 0.52 (Table S13).
- **An unfair real-only comparator.** E9 adds the small-sample index, and the first LightGBM configuration is applied equally to all arms.
- **Spatial dependence in the inference.** Handled well. Population inference over routes is impossible with four routes, and the paper does not claim it.

---

## E. Experimental review

### E1. Real-world evaluation (Table I; Tables S4–S8)

- **Question.** How accurate are standard estimators on held-out routes, and how much of that accuracy comes from map or speed priors?
- **Design.** Adequate. Within-route metrics are primary, and the baselines cover the relevant alternatives. The real-trained LightGBM gets inner leave-one-route-out configuration selection and the simulation-trained one does not; this favours the real model, against the paper's conclusions.
- **Confounders.** Route is confounded with class (stated). Vehicle overlap is tested (Table S7). One undocumented subset:
  - M7 is evaluated only on the HH direction of M13 (119 of 228 segments). `experiments/v2/physics_inversion.py:73` builds segment keys at multiples of 100 m, while M13-VH segments start at 16 560 m, so no VH key matches.
  - The excluded segments have the same mean IRI (1.04 vs 1.04 m/km) and speed (92 km/h), and real LightGBM's MAE on them is 0.152 vs 0.147 (check `c5`). The conclusions stand.
  - The caption's "segments with a usable road spectrum" still hides that a whole route-direction is missing.
- **Sample size.** 1,678 segments in 40 blocks of 5 km, enough to resolve differences of about 0.05 m/km within this dataset. M13 has only six 5 km blocks, so its per-route intervals are coarse.
- **Interpretation.** Correct. Two optional additions:
  - Report errors relative to mean IRI (about 19% urban and 12% motorway for LightGBM). For a log-trained model, the factor of four in m/km overstates the class difference.
  - Note in one sentence that removing the speed inputs raises LightGBM's within-route MAE from 0.39 to 0.62 m/km, mainly through the class level.

### E2. Simulation-to-real transfer (Table II; Fig. 2; Tables S12–S13)

- **Question.** What transfers zero-shot, and which simulator components set the level?
- **Design.** A good variant matrix and factorial. All variants are reported, and the non-independence of the variants and the post hoc status are acknowledged.
- **Interpretation issues.**
  - D2 (V4; band specificity) and D4c (log levels).
  - The scale *b* is estimated with route fixed effects, so by construction it cannot see between-class level errors, which are exactly what a single offset cannot fix. The motorway-minus-urban log-level spread is 0.26–0.30 for V1, V3 and V5, but 0.09–0.16 for V0, V2, V4, V7 and V8, with V6 between at 0.22 (check `c1b`).
  - Reporting each variant as (mean log level, class spread) would explain directly why an offset rescues V4 but not V1, V3 or V5 (P2.2).
- **Zero-shot vs calibrated performance.** Distinguished clearly. The ranking claim needs qualifying (E7).

### E3. Sensor and frequency-domain analysis (Fig. 3; Tables S15–S16)

- **Strength.** The comparison is on the same segments in the same 10 km/h speed bands, with block-bootstrap bands.
- **Association vs mechanism.** A rank association over nine non-independent variants is suggestive. The band-limited retraining (D2c) is model-level interventional evidence and should become the main support. The physical cause of the car's extra vibration above 10 Hz remains open, as the paper says.
- **Candidate causes.** Extend the list:
  - suspension friction or other nonlinearity, which would make transmissibility depend on amplitude and raise the real/simulated ratio on smoother roads (consistent with the larger motorway deficit);
  - modes of the powertrain or motor mounts;
  - a local resonance of the console mount.

  The LiRA-CD data article states that the AutoPi units were "fixed to the frame in the middle of the GM car close to the front axle", inside the middle console. Cite this instead of saying the mounting is unknown.
- **Optional diagnostic.** Within each class and speed band, check whether the real/simulated ratio above 10 Hz varies with roughness (IRI terciles). A constant ratio points to an unmodelled linear mode; a ratio that falls with roughness points to friction or a noise floor.
- **Aliasing check.** Correctly reported as confounded with the device.

### E4. Value of simulation (Table III; Fig. 4; Table S14)

- **Questions.** What do simulated drives replace at equal profile budget, and what is a paired drive worth when the simulation covers all profiled roads?
- **Design.** Both framings are present and correctly separated, with two real-only comparators and 20 paired draws. This is the strongest part of the revision.
- **Problems.**
  - D1 (combination method) and D4b (pass density).
  - The ranges over draws describe sampling of calibration blocks, not test uncertainty (stated). For the headline 5 km comparison, a 5 km block bootstrap of the draw-averaged difference would add test-route uncertainty cheaply (P2.6).
  - The equal-budget statements ("from 5 km the answer depends on the simulator") are correct as written and unaffected by D1.
- **Missing comparator.** The `c2` comparator (a physics index with the label-free speed exponent, calibrated on the same k km) deserves one sentence, to pre-empt the "slope only" objection.

### E5. Speed dependence (Fig. 5; Tables S16–S17)

- **Design.** The within-segment elasticity with segment fixed effects is a strong estimand. The paper keeps the scaling of raw vibration (the car's physical exponent) separate from the scaling of estimator output, which is the technically correct distinction.
- **Robustness (check `c6`).** Point estimates with 5 km block intervals:

| Quantity | Paper design | + telematics-unit fixed effects | + log within-pass speed SD |
|---|---|---|---|
| raw RMS exponent, urban | 0.60 [0.51, 0.69] | 0.59 | 0.65 [0.49, 0.84] |
| raw RMS exponent, motorway | 0.85 [0.73, 0.92] | 0.83 | 0.86 [0.74, 0.96] |
| simulated V0 minus real LightGBM, urban | +0.117 [+0.089, +0.146] | +0.119 | +0.121 [+0.088, +0.159] |
| simulated V0 minus real LightGBM, motorway | +0.024 [−0.078, +0.060] | +0.037 | +0.014 [−0.071, +0.050] |

  - Controlling for the speed coefficient of variation instead flips the urban difference to −0.07 [−0.21, +0.01]. But v_cv = SD/mean is mechanically tied to 1/v (within-segment correlation with log speed −0.86), so that control over-adjusts.
  - Analyses restricted to steady-speed passes are too imprecise to be informative.
- **Conclusion.** The speed claims are robust. Add the two robustness rows to Table S17, and one sentence noting that slow urban passes are more dynamic (within-segment correlation of log speed with log speed SD: −0.50).
- **Open question (optional).** Why the simulated vibration scales more steeply with speed (0.92–1.40 vs 0.60 and 0.85). A linear model without friction is one candidate (E3).

### E6. Baselines

- The ladder is relevant and fairly implemented.
- M7 is built "in the spirit of" Skar & Levenberg (2024), whose calibrated vehicle parameters are not available, and is correctly labelled as not a reproduction.
- Bridgelall's road impact factor is in effect the RMS/v^α index, which is already covered.
- No missing baseline would change the conclusions. Pooled simulation+real training is not a missing baseline but a missing arm of the value-of-simulation analysis (D1).

### E7. Statistical inference

The inference is appropriate and well explained: a 5 km block bootstrap as the decision rule, residual autocorrelation reported, route-level t intervals used descriptively only, and an explicit statement that supported differences describe these four routes. Three refinements:

1. **Paired test of the ranking claim (check `c3`).** Real LightGBM minus RMS/v^0.5, within-route Spearman, with 5 km blocks resampled within each route:

| Route | Δρ, real LightGBM minus untrained [95% CI] |
|---|---|
| CPH1 | +0.042 [+0.027, +0.062] |
| CPH6 | +0.044 [+0.032, +0.066] |
| M3 | −0.020 [−0.034, −0.008] |
| M13 | −0.023 [−0.033, −0.010] |
| mean of routes | +0.011 [+0.004, +0.020] |

   For partial ρ the mean difference is +0.001 [−0.006, +0.009]. For simulation-trained V0 it is +0.012 [−0.001, +0.025].
   - The conclusion stands: ranking differences are small next to level differences.
   - But "ranks as well" should become "within 0.05 on every route: better on the urban routes, slightly worse on the motorways".
2. **Test-route uncertainty for the headline calibration comparison** (E4).
3. **Coarse M13 intervals.** M13 has only six 5 km blocks; mention this wherever per-route intervals are shown.

Not needed:
- mixed or hierarchical models (a random route effect is not identifiable from four routes);
- multiple-comparison corrections on the descriptive variant contrasts (class E).

### E8. Controlled simulation (Sec. V-F; Table IV; Fig. 6)

- Correctly labelled class S.
- The sensor-perturbation result (a holder resonance turns a bias of −0.65 into +0.37 m/km) supports the level story and is worth keeping.
- The vehicle-number sweep is sound but secondary, and it is framed around "the criterion of our earlier study", which is unpublished. If the venue limits pages, move it to the supplement and keep one sentence.

### E9. Supplement (BeamNG, PVS)

Appropriately scoped as negative references. No change needed.

---

## F. Related-work review

Bibliographic details below were checked against Crossref, publisher or repository pages, or the full text (Bajic et al.). "Cited?" refers to the current paper.

| Work | What it does | Data and protocol | Relation to this paper | Cited? Accuracy | Direct comparison feasible? |
|---|---|---|---|---|---|
| Skar & Levenberg 2024, *J. Transp. Eng. B* 150(1):04023040, [doi:10.1061/JPEODX.PVENG-1385](https://doi.org/10.1061/JPEODX.PVENG-1385) | Road-profile inversion: quarter car, PID controller, nonlinear error minimisation | 10 nominally identical electric cars; highways and urban roads; compared with a laser profilometer; raw data under the LiRA-CD DOI ([DTU Orbit](https://orbit.dtu.dk/en/publications/road-profile-inversion-from-in-vehicle-accelerometers/)) | Closest physics approach on the same data | Yes; accurate | No: no per-route IRI in the abstract, and calibrated parameters unavailable. M7 is the right compromise. |
| Jeong, Jo & Ditzler 2020, *CACAIE* 35(11):1209–1229, [doi:10.1111/mice.12546](https://doi.org/10.1111/mice.12546) | CNN on simulated responses of four vehicle types with real speed profiles ("calibration-free") | Numerical validation with real road IRI (Speedway, Tucson) | Direct precursor of the simulation-trained estimator | Yes; accurate | No (numerical study) |
| **Jeong & Jo 2024**, *IEEE IoT J.* 11(4):6328–6337, [doi:10.1109/JIOT.2023.3312353](https://doi.org/10.1109/JIOT.2023.3312353) | IRI-Net (fully convolutional) with crowdsourced data management | Full-scale validation: 29 real vehicles, inertial-profiler reference; trained on real data per the abstract | The calibration-free line moved to real data at scale, consistent with this paper's message | **No; add** | No (different data) |
| **Nitsche et al. 2014**, *J. Comput. Civ. Eng.* 28(4):04014015 (online 2012), [doi:10.1061/(ASCE)CP.1943-5487.0000285](https://doi.org/10.1061/(ASCE)CP.1943-5487.0000285) | MLP, SVR and random forest trained on features of simulated vehicle responses | Validated on probe-vehicle data against an inertial profilometer; target weighted longitudinal profile; no speed variation (per Bajic et al.) | **Closest precedent of the simulation-to-real design** | **No; add** | No (different index and data) |
| **Ngwangwa et al. 2014**, *J. Terramechanics* 53:1–18, [doi:10.1016/j.jterra.2014.03.002](https://doi.org/10.1016/j.jterra.2014.03.002) | Simulation-trained NARX network applied to experimental data | Land Rover Defender 110 over discrete obstacles and Belgian paving | Simulation-trained, tested on a real vehicle (profile reconstruction, roughness classes) | Only the 2010 numerical study is cited; add 2014 | No |
| **Wu et al. 2023**, *Int. J. Pavement Eng.* 25(1):2287688, [doi:10.1080/10298436.2023.2287688](https://doi.org/10.1080/10298436.2023.2287688) | Full-car model updated from a few impact tests; linear IRI–RMS relation derived by simulation over random profiles | Real roads in Shanghai; mean IRI difference 0.5 m/km per 100 m | An alternative way to "calibrate the level": calibrate the vehicle model, not the estimator | **No; add** | No (different data); discuss qualitatively |
| Bajic et al. 2021, [arXiv:2107.01199](https://arxiv.org/abs/2107.01199) | Classical ML regressors on time-domain and statistical features | GreenMobility Renault Zoe, AutoPi at 50 Hz; M3 (52.6 km, both lanes); Greenwood-profiler IRI per 10 m averaged over sliding 100 m windows (10 m step); holdout = last 20% (1,006 segments); best MAE 0.16–0.17, RMSE 0.21, R² 0.64–0.66 (MLP); mean baseline MAE 0.33 | ML on the same fleet with a within-road split | Yes; accurate. Anchor in Table S8 appropriately caveated. Bajic et al. name a Greenwood profiler and the LiRA-CD article does not name the P79's maker, so "different profiler" is unverified: write "different reference survey and processing". | Approximate anchor only (already done) |
| Skar et al. 2023, LiRA-CD, *Data in Brief* 49:109426 ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10375556/)) | The dataset | P79 surveys 10-09-2020 (CPH1, M3, M13) and 04-06-2020 (CPH6); car data 2020–2021; AutoPi "fixed to the frame in the middle of the GM car close to the front axle"; also a platoon test (39 passes over 1.5 km of CPH1) and CAN signals (longitudinal acceleration, wheel speeds, tyre pressures) | The data source | Yes; cite the mounting description and survey dates | — |
| Agebjär et al. 2025, FUSION, [doi:10.23919/FUSION65864.2025.11123970](https://doi.org/10.23919/FUSION65864.2025.11123970) | System identification plus Kalman-filter profile reconstruction | Production car, real data | Model-based alternative | Yes; accurate | No |
| Xing et al. 2025, *Machines* 13(5):391, [doi:10.3390/machines13050391](https://doi.org/10.3390/machines13050391) | Speed-adaptive roughness classification from the unsprung-mass response | Quarter-vehicle simulation plus a real-vehicle test | Simulation plus real test, roughness classes | Yes; accurate | No |
| Zhang, Sun, Bridgelall & Sun 2018, *J. Transp. Eng. B* 144(4):04018043, [doi:10.1061/JPEODX.0000074](https://doi.org/10.1061/JPEODX.0000074) | ML on simulated connected-vehicle signals; a convolution suppresses vehicle and speed effects; IRI classes | Simulation only | Earlier "learning from simulated responses" | No; optional | — |
| Wang, Burrow & Ghataora 2020, *J. Infrastruct. Syst.* 26(3):04020020, [doi:10.1061/(ASCE)IS.1943-555X.0000558](https://doi.org/10.1061/(ASCE)IS.1943-555X.0000558) | Simulation study of factors (vehicle type, driving style) affecting smartphone roughness measurement | Simulation | Context for vehicle and sensor sensitivity | No; optional | — |
| Shangguan et al. 2025, *J. Comput. Civ. Eng.* 39(6):04025099, [doi:10.1061/JCCEE5.CPENG-6782](https://doi.org/10.1061/JCCEE5.CPENG-6782) | VMD plus CNN predicting the road profile from connected-car acceleration; IRI computed from the predicted profile | **Data source not verified here** | If it uses LiRA-CD, related work on the same data | No; check the full text, then decide | Possibly, if routes and labels match |
| Nguyen, Lechner & Wong 2019, *Eur. Transp. Res. Rev.*, [doi:10.1186/s12544-019-0380-6](https://doi.org/10.1186/s12544-019-0380-6) | Review of response-based methods | About 130 documents | Survey reference | No; optional | — |
| Peng et al. 2018, ICRA, [doi:10.1109/ICRA.2018.8460528](https://doi.org/10.1109/ICRA.2018.8460528); Chebotar et al. 2019 ("SimOpt"), ICRA, [arXiv:1810.05687](https://arxiv.org/abs/1810.05687) | Dynamics randomisation; adapting the distribution of simulation parameters from a few real roll-outs | Robotics | Framing: the paper's spectral check and k km calibration are forms of real-data-informed simulation adaptation | Only Tobin et al. 2017 is cited; adding SimOpt is optional but sharpens the framing | — |

**Classifying the gaps.**
- *Missing citations.* Essential: Nitsche 2014, Ngwangwa 2014, Wu 2023, Jeong & Jo 2024. Optional: Zhang 2018, Wang 2020, Chebotar 2019.
- *Incorrect descriptions.* None material; only the "different profiler" wording is uncertain.
- *Insufficient differentiation.* The introduction's gap sentence.
- *Genuine novelty limitation.* The general design (simulate over measured profiles, test on a real vehicle) has precedent. The paper's decomposition of what transfers, its level diagnosis and its data-requirement analysis do not. All of this is fixable in writing.

**Datasets.** I found no other public dataset pairing production-car accelerations with raw profilometer profiles. The CE-MRR dataset (IEEE DataPort) combines GNSS/IMU data, smartphone-app IRI and passenger ratings, but I could not confirm a profilometer reference. The paper can say this carefully ("to our knowledge").

**LiRA-CD studies.** Beyond Bajic et al. (2021), Skar & Levenberg (2024) and possibly Shangguan et al. (2025), my searches found no 2024–2026 IRI-estimation study on LiRA-CD. The searches covered open web indexes only.

**Spot-checked references in the paper.** I verified [9] Xing 2025, [11] Agebjär 2025, [18] Yu et al. 2026 (*J. Comput. Civ. Eng.* 40(3):04026015) and [21] Sang et al. 2026 (*J. Comput. Civ. Eng.*, doi:10.1061/JCCEE5.CPENG-7395) against Crossref; all match. The bibliography is generated from Crossref by DOI (`references/build_bib.py`). The title-level citations flagged in `REFERENCE_AUDIT.md` (mounting2026, hanson2014iri, ngwangwa2010ann) still need a human read.

---

## G. Prioritized revision plan

Costs assume the development machine (12 CPU threads), where a LightGBM fit takes about 0.5 s.

### Priority 1: essential corrections

**P1.1 Pooled simulation + real arm for all variants (fixes D1).**
- *Research question:* Does the paired-data requirement depend on simulator fidelity when simulated and real passes are trained jointly, rather than combined through a level offset?
- *Hypothesis:* Joint training largely removes the dependence on the variant. Check `c4` supports this for V0, V1, V3 and V5.
- *Required data:* the existing variant sets (`data/processed/sim/*`) and the LiRA units.
- *Implementation:* new `experiments/v2/pooled_vs_real.py`, modelled on `review/v3_checks/c4_pooled_sim_real.py`:
  - v1 weighting from `exp_lira.part_fewshot`, first LightGBM configuration;
  - training sets from `variant_training_set(vid, R)`; calibration blocks from `sample_blocks` with `default_rng(1000*d+7)`;
  - variants V0–V8 and V10; k ∈ {1, 2, 5, 10, 20}; 20 draws;
  - extend `paired_vs_real.py` with an arm `sim_real_pooled`, paired with `real_only` and `real_only_index`, also per route.
- *Protocol:* add a dated addendum to `PROTOCOL_V2.md` §8, written before running the remaining variants. It should state that the design comes from v1 §1, that the arm was omitted in v2 and is restored, and that it is class R. Report every variant.
- *Primary metric:* pooled and within-route segment MAE; mean difference to real-only and number of better draws, against both comparators; per route.
- *Expected value:* decides how contribution (iii) and the abstract's closing sentences can be phrased.
- *Cost:* about 10 min per variant on CPU, under 2 h in total.
- *Status:* essential.

**P1.2 Correct the mechanism attribution (fixes D2a–b).**
- Extend `band_gain.py`, `summarise_v2.py` and `make_numbers_v2.py` with Spearman and Pearson correlations of the zero-shot bias against all four bands and the overall-RMS ratio (new macros).
- Add the V4 comparison: 10–15 Hz ratio 1.93 vs 1.86; overall RMS 1.23 vs 1.12; bias +0.40 vs +0.01.
- Rewrite the abstract, Sec. V-B, Sec. V-C, the Discussion paragraph "A correction to our earlier explanation", and the Conclusion.
- Cost: minutes. Essential.

**P1.3 Related work and the gap statement (fixes D3).** Add bibliography entries by DOI through `references/build_bib.py` for Nitsche 2014, Ngwangwa 2014, Wu 2023 and Jeong & Jo 2024. Rewrite the introduction's second paragraph and the related-work paragraph "Learning from simulated responses". Essential.

**P1.4 Metric and denominator clarity (fixes D4).**
- Label every MAE as within-route or pooled.
- Add within-route values for the calibration arms (macros from `variants_calibration.csv`: mean over the four routes of `seg_mae`).
- Define k km with its pass density (macros: 9.7 passes per segment; 475 segment-passes at 5 km, range 301–640).
- Add the mean log level per class to Table II (from the `level_*` columns of `variants_zeroshot.csv`).
- Essential.

**P1.5 Qualify the ranking claim.** Add the per-route paired Δρ with 5 km block intervals (logic of `review/v3_checks/c3_rank_paired.py`) to Table S5 or a new Table S5b. Reword "ranks as well" in the abstract, Sec. V-B, the Discussion and the Conclusion. About 10 min of compute. Essential (the wording); the computation is cheap.

### Priority 2: high-value improvements

**P2.1 Band-limited zero-shot intervention (strengthens the refined mechanism of D2).**
- *Research question:* Do the level differences between sensor variants come from simulated energy above 10 Hz?
- *Hypothesis:* With features limited to content below 10 Hz, the spread of bias across sensor variants collapses, while the single-vehicle variant V4 stays biased. Already observed in `c8`: the spread falls from 0.52 to 0.14 m/km, and V4 stays at +0.28.
- *Data and implementation:* port `review/v3_checks/c8_band_limited.py` (which uses `common_v2`) to `experiments/v2/band_limited.py`.
- *Protocol:* class E addendum. Report every variant and the accuracy cost (MAE after a level offset; within-route ρ).
- *Primary metric:* range of pooled bias across V0–V8; mean log level by class; MAE after a 5 km offset.
- *Expected value:* replaces a nine-point rank correlation with an intervention and makes the practical advice concrete.
- *Cost:* about 5 min.

**P2.2 Level decomposition.** For each variant, report the mean log level and the motorway-minus-urban log-level spread, and show that the error left after an offset follows the spread (check `c1b`). This explains which variants a single offset can fix. Minutes.

**P2.3 Speed robustness rows.** Add the unit fixed effects and the log speed-SD covariate to Table S17 (`review/v3_checks/c6_speed_robustness.py`), with one sentence in Sec. V-E. Minutes.

**P2.4 Fix the M7 segment grid.** In `experiments/v2/physics_inversion.py:73`, build segment keys from `data/processed/lira/p79_segments_100m.csv` (`start_m`) or from `U.segment` instead of multiples of 100 m, then rerun M7 and the summaries. If this is not done, state "M13: HH direction only (119 segments)" in the captions of Table I and Table S10. Minutes.

**P2.5 Show that the simulator is not just a slope.** Add the no-simulator index with the label-free speed exponent (check `c2`: 0.78 m/km at 5 km) as a comparator row or sentence in Sec. V-D. Note also that the simulation-fitted three-parameter index with an offset is insensitive to the variant (0.51–0.53 m/km; Table S13). Minutes.

**P2.6 Test-route uncertainty for the 5 km comparison.** Average each arm's pass predictions over the 20 draws, then bootstrap the difference to real-only over 5 km blocks of test segments, for both the level-offset and pooled arms. Minutes.

### Priority 3: optional

- **P3.1 Calibration pass budget.** At k = 5 km, subsample 1, 2 and 5 passes per segment for the level-offset and pooled arms. This tells practitioners whether ten passes per segment are really needed. About 10 min.
- **P3.2 Amplitude dependence of the real/simulated ratio above 10 Hz**, within class and speed band (IRI terciles). This separates unmodelled linear modes from friction or a noise floor. Extend the list of candidate causes (E3). Minutes.
- **P3.3 Platoon data** (39 passes over 1.5 km of CPH1; `data/raw/lira_cd/car/platoon_CPH1_*.hdf5`). Inspect the speeds and cars first. If speeds vary in a controlled way, these passes give a semi-controlled check of the car's speed exponent. 1–2 h.
- **P3.4 Relative or log-scale errors per class** in Table I. Minutes.
- **P3.5 Length.** Shorten the abstract, and move Sec. V-F to the supplement if the venue limits pages.
- **P3.6 Framing.** Use the dynamics-randomisation and SimOpt literature in Related Work and the Discussion.
- **P3.7 Version control.** Commit `research_rescue/` with tags at the protocol-freeze points so that "frozen before" can be verified. This is the authors' decision.

### Not recommended

- New architectures or CNN tuning.
- More simulator variants.
- Mixed or hierarchical models over four routes.
- Multiple-comparison corrections for the descriptive variant contrasts.
- A reproduction of Skar & Levenberg.
- Collecting new real data within this revision.

None of these would change a conclusion in proportion to its cost.

---

## H. Writing and presentation

**Title.** Accurate and aligned with the content; keep it.

**Abstract.** Accurate number by number but dense: about 250 words and 15 numbers. It mixes within-route and pooled MAE, over-attributes the mechanism, and states a method-dependent conclusion as general. A suggested structure follows; bracketed values come from the updated macros.

> Estimating the International Roughness Index (IRI) from the vibration of ordinary cars needs paired data: drives of the car type over road sections with surveyed profiles. Vehicle simulation can generate such pairs from the profiles alone. We test what estimators trained on simulated drives transfer to a real car, using public profilometer-referenced data from one car model (LiRA-CD; four routes, 168 km), held-out routes and 5 km-block bootstrap intervals. Gradient boosting trained on real drives reaches a within-route mean absolute error (MAE) of 0.39 m/km. Trained only on a randomised half-car simulation over measured profiles of the other routes, it ranks segments within routes about as well under each of nine sensor and vehicle models, and so does an untrained, speed-normalised vibration RMS; what has to be learned is the level. The zero-shot bias ranged from −0.09 to +0.43 m/km and depended on both the simulated sensor path and the simulated vehicle population; restricting the estimator to vibration below 10 Hz brought all sensor variants within 0.14 m/km of each other. With [5 km of profiled road, each segment driven about ten times], a level offset brought every variant to a pooled MAE of 0.42–0.56 m/km and joint training to [x–y] m/km, against 0.68 m/km for training on those drives alone; joint training remained at least as accurate as real-only training up to 20 km for every variant. Simulated vibration also grew faster with speed than the real car's. For this car, simulation over profiled roads plus a few kilometres of paired drives replaced most of the paired data; whether this holds for other vehicles requires new paired data.

**Introduction.**
- Second paragraph: add Nitsche 2014, Ngwangwa 2014, Wu 2023 and Jeong & Jo 2024, and narrow the gap sentence (D3).
- "The answer has three parts": update the level part (two ingredients; energy above 10 Hz) and the data part (combination method).
- Contribution (ii): change "locate" to "associate ... and test by band-limiting".
- Contribution (iii): name the combination methods.

**Related work.** Suggested additions:
- Under "Learning from simulated responses": "Nitsche et al. trained regressors on simulated responses over measured profiles and validated them on a probe vehicle against an inertial profilometer for the weighted longitudinal profile; Ngwangwa et al. applied a simulation-trained network to experimental vehicle data."
- Under "Response-type measurement": "Wu et al. calibrated a full-car model with impact tests and derived an IRI–vibration relation in simulation, validated on real roads."
- Under "Learned estimators on real data": "Jeong and Jo validated a deep IRI estimator on 29 real vehicles against an inertial profiler."
- New closing sentence: "We add continuous-IRI evidence on held-out roads of public data for a production car, a decomposition of what transfers, and the paired data that must accompany the simulation."

**Data and simulation.** Cite the LiRA-CD mounting description and the survey and drive dates (P79 surveys in 2020; car drives 2020–2021). State that "k km" means k km of profiled road with each segment driven about ten times.

**Estimators and evaluation.** Define the level as a mean log ratio, define within-route and pooled MAE, and describe the pooled arm and its v1 origin.

**Results.**
- V-A: note the M7 subset, or fix it.
- V-B: add V4 and the log levels.
- V-C: report all band correlations and the band-limited result. Replace "its physical source is not identified (... the mounting of the telematics unit ... unknown)" with the LiRA-CD mounting statement and the extended list of candidate causes.
- V-D: add the pooled arm, the pass density, the within-route numbers and the "not just a slope" comparator.
- V-E: add a robustness sentence.
- V-F: consider moving it to the supplement.

**Discussion.**
- "A correction to our earlier explanation": add V4 ("and its 30-vehicle population").
- Road-agency recipe: "simulate over roads that are already profiled; with a few kilometres of paired drives, either fit a level offset when simulated and real spectra agree, or train jointly, which was robust to the mismatch in our data".
- The statistics paragraph is fine as it is.

**Limitations.** Add that the calibration analyses compare specific methods of combining simulated and real data. If M7 is not fixed, state its evaluation subset.

**Conclusion.** Mirror the changes to the abstract. Avoid "depended on the simulated vibration at 10–15 Hz"; prefer "on the simulated vibration above 10 Hz and on the vehicle population".

**Figures.**
- Fig. 2c: add markers for the pooled arm.
- Fig. 3b: the labels of V1, V3 and V5 overlap. Add an inset or second panel with the overall-RMS ratio, or annotate V4.
- Fig. 4: add pooled curves to panel (b), and put "pooled MAE" in the axis label.
- Fig. 5: fine.
- Fig. 6: move with Sec. V-F if needed.

**Tables.**
- Table I: caption the M7 subset.
- Table II: add the log level per class. To make room, consider moving the speed-elasticity column to Table S12.
- Table III: add the pooled arm and within-route values, and define k km.
- Table S8: "different reference survey and processing".
- Table S14: add a 10 km column for the affine arm, and the pooled arm.

**Terminology.** "Paired drives" needs a definition that includes the pass density, and "level" needs its log-ratio definition. The route-disjoint versus vehicle-disjoint distinction is already handled well.

**Length.** The main paper runs to 10 pages. If the target venue limits regular papers to 6–8 pages, the natural cuts are Sec. V-F (with Table IV and Fig. 6) and part of Sec. V-A.

---

## I. Claim audit

| # | Claim (location) | Status | Evidence | Required change |
|---|---|---|---|---|
| 1 | Real-trained gradient boosting reaches within-route MAE 0.39 m/km (Abstract, V-A) | Supported | `summary_real_estimators.csv` (0.3950) | — |
| 2 | Simulation-trained model ranks within routes as well under each of nine models (ρ 0.82–0.84 vs 0.83) (Abstract, V-B) | Supported (route averages) | `summary_variants.csv` | — |
| 3 | An untrained RMS/v^0.5 ranks as well (0.82); "ranking does not discriminate" (Abstract, V-B, Discussion, Conclusion) | Partially supported | Mean Δρ +0.011 [+0.004, +0.020]: +0.04 on both urban routes, −0.02 on both motorways, every interval excludes 0 (`c3`) | "within 0.05 on every route"; report the paired Δρ |
| 4 | Zero-shot bias ranges from −0.09 to +0.43 m/km (Abstract) | Supported | `summary_variants.csv` | Add the log level per class |
| 5 | V0 matched the level only because half its passes carried a phone-holder resonance (Abstract, Intro, Discussion) | Not supported as worded | V4: same sensor mixture, bias +0.40 | Name the vehicle population as a second necessary ingredient |
| 6 | The bias follows a deficit of simulated vibration at 10–15 Hz (Abstract, V-C, Discussion, Conclusion) | Partially supported | Spearman 0.97, but R² 0.78 for overall RMS vs 0.71; 5–10 Hz (0.80) unreported; V4 residual +0.20; dropping the 10–15 Hz band changes nothing, while band-limiting below 10 Hz collapses the sensor-variant spread (`c1`, `c8`) | Say "above 10 Hz"; report all bands; add the intervention |
| 7 | A 5 km level offset brought every variant to 0.42–0.56 m/km, better than 5 km real-only (0.68) in 13–20 of 20 draws (Abstract, V-D, Conclusion) | Supported (pooled MAE) | `paired_vs_real.csv`; per route in `paired_vs_real_by_route.csv` | Define k km (about 475 segment-passes); label as pooled |
| 8 | With 10 km or more, real drives alone beat the three variants with the largest deficit (Abstract, Intro, Conclusion) | Requires qualification | True for the level offset only; the paper's own affine arm beats real-only at 10 km, and pooled training at 10 and 20 km (D1) | Name the combination method, or replace with the pooled-arm result |
| 9 | Simulated vibration grows faster with speed than the real car's (Abstract, V-C) | Supported | 0.92–1.40 vs 0.60 and 0.85; robust to unit fixed effects and the speed-SD control (`c6`) | Add the robustness rows |
| 10 | Simulation can stand in for most paired drives; how many it saves depends on how well the simulated vibration matches (Abstract) | First half supported (one car); second half depends on the method | D1 | Reword |
| 11 | "What is missing is evidence on real cars ..." (Intro) | Requires qualification | Nitsche 2014, Ngwangwa 2014, Wu 2023, Jeong & Jo 2024 | Narrow the gap; cite them |
| 12 | Contribution (ii): factorial and spectra "locate the level error" (Intro) | Partially supported | Associational; misses the vehicle effect | "associate, and test by band-limiting" |
| 13 | Contribution (iii): the paired data simulation replaces, "for every simulator variant" (Intro) | Partially supported | Depends on the method (D1) | Name the methods |
| 14 | M7 ranks as well but with larger error (+0.081 [+0.043, +0.115]); its output calibration made it worse (V-A) | Supported | M13 evaluated on HH only (119 of 228 segments); negligible effect (`c5`) | Caption it, or fix (P2.4) |
| 15 | Vehicle overlap did not measurably favour real-trained estimators (V-A) | Supported (three folds) | Table S7 | — |
| 16 | LightGBM and MLP differ negligibly; the CNN is worse, almost entirely on CPH1 (V-A) | Supported | Tables I, S4, S5 | — |
| 17 | Equal-budget statements: 1–2 km; variant dependence from 5 km; V4's gap closed by an offset (V-D) | Supported | Table S14 | — |
| 18 | Real-trained learned estimators over-correct for speed; V0 over-corrects less on urban roads (paired +0.09 [+0.06, +0.12]) (V-E) | Supported and robust | `c6` | Add the robustness rows |
| 19 | Unseen-vehicle penalty of +70, +16 and +6% (V-F) | Supported (class S) | `vehicle_sweep.csv` | — |
| 20 | V0's zero-shot accuracy is a fortunate match, not a property of randomising over sensors (Discussion) | Supported but incomplete | V4 | Add the vehicle population |
| 21 | Two-step recipe for road agencies (Discussion) | Partially supported | D1, D2 | Include joint training; "above 10 Hz"; label as post hoc |
| 22 | 5 km block intervals are 1.9–2.7 times as wide; a segment bootstrap would have declared V0 worse (Discussion) | Supported | `inference_blocks.csv` | — |
| 23 | ARAN agrees with the P79 in ranking and median level but disagrees on a few urban segments (Discussion) | Supported | Table S11 | — |
| 24 | The simulated level depended on the simulated vibration at 10–15 Hz (Conclusion) | Partially supported | `c1`, `c8` | "above 10 Hz, and on the vehicle population" |
| 25 | With 10 km or more of paired drives, the advantage depended on the variant (Conclusion) | Requires qualification | D1 | Name the method |

---

## J. Reproducibility and numerical consistency

**Verified by re-derivation in this review.**
- All number macros used in the main paper and the supplement resolve, and none is undefined (`c7_macros.py`). The abstract's values match the macros.
- Retraining reproduces the zero-shot MAEs of V0–V8 exactly (`c8`, full feature set: V0 0.439 ... V5 0.687 m/km), and likewise the MAEs after a 5 km level offset (V0 0.425 ... V5 0.562).
- My reimplementation of the block sampler reproduces the paired-draw arms exactly (`c2`): V0 plus level 0.425, real-only 0.678, real-only index 0.722, simulation-fitted index plus level 0.516 (Table S13: 0.52).
- The factorial effects follow from the pooled biases: holder resonance −0.355 and −0.361, sensor family −0.160 and −0.166 m/km (paper: −0.35, −0.36, −0.16, −0.17).
- Band associations: Spearman 0.967, 0.217 and 0.250 (paper: 0.97, 0.22, 0.25).
- Fixed-road elasticities: raw RMS 0.602 (urban) and 0.847 (motorway); paired urban difference +0.117 (paper: 0.60, 0.85, +0.12).

**Problems found.**
1. **M7 segment-grid bug** (`experiments/v2/physics_inversion.py:73`). Segment keys at multiples of 100 m exclude M13-VH, whose segments start at 16 560 m, so M7 is evaluated on 119 of 228 M13 segments. Impact is low (`c5`). Fix or document (P2.4).
2. **A pre-specified v1 arm is not reported in v2** (D1). This is a reporting-completeness problem.
3. **Metric labelling** in the abstract (D4a).
4. **Table S8's "different profiler"** is unverified (Section F).
5. **No version control.** `git ls-files research_rescue` returns nothing: the whole rescue, including the frozen protocols, is untracked, so "frozen before any test result" rests on file timestamps. Committing it is the authors' decision, but it costs little and makes the evidence-class labels checkable.
6. **Rounding.** The real model's within-route MAE is 0.3950, printed as 0.39. After a 5 km offset, V2's within-route MAE is 0.395. When within-route numbers are added, use three decimals in the supplement to avoid apparent ties or reversals.

**Review checks.** All read-only. Run them in the `torch_gpu` environment as `python -I <script> <path to research_rescue> ...`; outputs go to `review/v3_checks/outputs/`.

| Script | What it checks | Runtime |
|---|---|---|
| `c1_band_vs_bias.py`, `c1b_levels.py` | Band ratios against bias (m/km and log level); V4 residual | seconds |
| `c2_minimal_calibration.py` | No-simulator index arms on the paper's draws; reproduces V0 plus level, real-only, real index | ~20 s |
| `c3_rank_paired.py` | Paired within-route Δρ with block bootstrap | ~10 min |
| `c4_pooled_sim_real.py`, `c4b_compare.py` | v1 pooled arm for V0, V1, V3, V5 on the paper's draws | ~9 min |
| `c5_m7_subset.py` | The M13 subset used by M7 | seconds |
| `c6_speed_robustness.py` | Speed elasticities with unit fixed effects and dynamics controls | ~1 min |
| `c7_macros.py` | Macro resolution | seconds |
| `c8_band_limited.py` | Band-limited zero-shot intervention | ~4 min |

---

## K. Final assessment

**What the paper can defensibly claim after revision.** For one production car on four public profilometer-referenced routes, with held-out routes:
1. A randomised half-car simulation over measured profiles of other roads reproduces the within-route vibration-to-IRI mapping about as well as real training does. An untrained vibration statistic also largely does.
2. Its absolute level is not reliable. The level depends on the simulated sensor path (through energy above about 10 Hz) and on the simulated vehicle population.
3. Simulation over all profiled roads, combined with a few kilometres of profiled road with paired drives, approaches full real training and beats real training on the same drives. With joint training this held for every simulator variant tested, up to 20 km.
4. The simulated vibration scales with speed differently from the real car's. Simulation-trained estimators over-correct for speed less on urban roads.
5. Dependence-aware inference and fixed-road speed elasticities change conclusions relative to common practice.

**What remains uncertain.**
- The physical cause of the real car's extra vibration above 10 Hz and of its flatter speed scaling.
- Whether the size of the calibration requirement (5 km of profiled road at about ten passes per segment) transfers to other cars, sensors and road networks.
- Generalisation across routes, given only two routes per class.

**Acceptable limitations given the scope.** One car and one sensor type; post hoc evidence beyond the V0 comparison; a linear half-car without roll; no reference survey simultaneous with the drives. All are stated and labelled, and none invalidates the within-dataset findings.

**Readiness.**
- *Current state:* careful, but it carries an abstract-level conclusion (D1) and a mechanism claim (D2) that its own data do not support as worded, and a knowledgeable reviewer would flag the missing prior work (D3).
- *After P1:* a sound contribution for an applied ITS or pavement-engineering conference (indicatively 5/7, up from about 4/7 now).
- *After P1 and P2:* a credible journal submission at the boundary between major and minor revision (indicatively 4/7).
- *To go further:* a confirmatory test with a frozen protocol on a second car type.

---

## L. Implementation handoff

Work in this order: L1–L4 change numbers that later items quote.

Environment notes:
- Edit LaTeX and Python with the Write/Edit tools, not Bash heredocs or `sed`; in this environment those corrupt backslashes.
- After each analysis change, run `python research_rescue/run_all_experiments.py --only v2_summarise v2_paired v2_figures v2_tables v2_numbers v2_final_results bib_cited paper` and recompile in the order supplement, main, supplement, main.
- Record each change in `CHANGELOG.md`.

**L1. Protocol addendum for the pooled arm**
- *Task:* add a dated item (E11) to `PROTOCOL_V2.md` §8 *before* running new variants. It must state that the design is v1 §1's "simulation-pretrained + real fine-tuned", implemented as in `exp_lira.part_fewshot` (balanced weights, first LightGBM configuration); that it is class R; and that it covers V0–V8 and V10, k ∈ {1, 2, 5, 10, 20}, 20 draws, with every variant reported.
- *Files:* `evaluation/PROTOCOL_V2.md`, `CHANGELOG.md`.
- *Expected output:* the addendum text.
- *Acceptance:* the addendum is dated before the outputs of L2.

**L2. Implement and run the pooled arm**
- *Task:* create `experiments/v2/pooled_vs_real.py` by porting `review/v3_checks/c4_pooled_sim_real.py` to `common_v2` (`variant_training_set`, `sample_blocks`, `seg_table`), covering V10 as well. Add a step to `run_all_experiments.py`.
- *Expected output:* `results/v2/pooled_vs_real.csv` with columns `vid, fold, k_km, draw, arm, seg_mae, n_seg, seg_bias`.
- *Acceptance:* 10 variants × 4 folds × 5 k × 20 draws = 4,000 rows. Values for V0, V1, V3 and V5 at k = 5, 10 and 20 match `review/v3_checks/outputs/c4b_compare.txt` within ±0.002 m/km.

**L3. Pair and summarise**
- *Task:*
  - add the arm `sim_real_pooled` to `paired_vs_real.py`, in both `main()` and `by_route()`;
  - add macros for pooled MAE ranges and better-draw counts at 5, 10 and 20 km to `make_numbers_v2.py`;
  - add pooled columns to Table III and Table S14, plus an affine 10 km column in S14 (`make_tables_v2.py`);
  - add pooled curves to Fig. 4b and markers to Fig. 2c (`make_figures_v2.py`).
- *Expected output:* updated CSVs, macros, tables and figures.
- *Acceptance:* every new number in the text is a macro, and `numbers_v2.tex` contains no `??`.

**L4. Rewrite the value-of-simulation claims**
- *Task:* revise the abstract and the conclusion (`main.tex`), the "answer has three parts" paragraph and contribution (iii) (`sections/intro.tex`), Sec. V-D (`sections/results.tex`), and the recipe and Limitations (`sections/discussion.tex`).
- *Expected output:* revised text.
- *Acceptance:* no sentence says real drives beat any variant at 10 km or more without naming the combination method; the recipe mentions joint training; the CLAIM_AUDIT rows are updated.

**L5. Mechanism wording and the full band table**
- *Task:*
  - compute Spearman and Pearson correlations of the zero-shot bias, and of the mean log level, against `log_rms` and all four bands (`band_gain.py` or `summarise_v2.py`; new macros in `make_numbers_v2.py`);
  - add them to `tables/v2s_gap.tex` / Table S16;
  - revise Sec. V-B and V-C, the Discussion paragraph "A correction to our earlier explanation", the abstract and the conclusion, including V4 (same sensor mixture, bias +0.40).
- *Expected output:* new macros and revised text.
- *Acceptance:* `grep -n "only because\|only through a sensor"` over `paper/` returns nothing (the abstract says "only because", the introduction "only through a sensor component"); all five correlations are printed; V4 is discussed.

**L6. Band-limited intervention**
- *Task:* port `review/v3_checks/c8_band_limited.py` to `experiments/v2/band_limited.py`. Write a protocol addendum (class E). Add one paragraph to Sec. V-C and one supplement table.
- *Expected output:* `results/v2/band_limited.csv`.
- *Acceptance:* the full-feature rows reproduce the `summary_variants.csv` MAEs to three decimals. The text reports the bias range for the three feature sets (all, without the 10–15 Hz band, below 10 Hz only), V4's remaining bias, and the accuracy cost after an offset.

**L7. Level decomposition**
- *Task:* in `summarise_v2.py`, compute the mean log level, the urban and motorway log levels, and their spread from the `level_*` columns. Add log level per class to Table II and to Table S12.
- *Expected output:* macros and table columns.
- *Acceptance:* V0's motorway log level (+0.145, or about +16%) is visible, and one sentence links the spread to the MAE after an offset.

**L8. Metric labels and the k-km definition**
- *Task:* revise the abstract; the Method paragraph "Level calibration and value of simulation"; the Table III caption; and the Fig. 4 axis label. Add macros for passes per segment (9.7), segment-passes at 5 km (475; range 301–640) and within-route MAE after a 5 km offset (0.395–0.519).
- *Expected output:* revised text and macros.
- *Acceptance:* every MAE in the abstract is labelled, or a single metric is used throughout; "k km" is defined with its pass density.

**L9. Paired Δρ**
- *Task:* extend `experiments/v2/inference_blocks.py`, or add a script using the logic of `review/v3_checks/c3_rank_paired.py`. Add new rows to Table S5.
- *Expected output:* a CSV and macros giving per-route Δρ with 5 km block intervals, for real LightGBM and for V0, each against RMS/v^0.5.
- *Acceptance:* the abstract, Sec. V-B, the Discussion and the Conclusion say "within 0.05 on every route (better on urban, slightly worse on motorway routes)".

**L10. Speed robustness**
- *Task:* port `review/v3_checks/c6_speed_robustness.py` into the outputs of `speed_real.py` or `speed_paired.py`. Add rows to Table S17 and one sentence to Sec. V-E.
- *Acceptance:* the numbers match `outputs/c6_speed_robustness.txt` to three decimals, and the text notes the extra dynamics of slow urban passes.

**L11. M7 segment-grid fix**
- *Task:* at `experiments/v2/physics_inversion.py:73`, take segment starts from `data/processed/lira/p79_segments_100m.csv` (or key on `U.segment`). Rerun `physics_inversion.py` and `summarise_v2.py`.
- *Expected output:* updated `physics_inversion.csv`, Tables I, S4 and S10.
- *Acceptance:* M7 has 228 M13 segments; otherwise the captions state "HH direction only, 119 segments".

**L12. Related work**
- *Task:* add these DOIs to `references/build_bib.py`: 10.1061/(ASCE)CP.1943-5487.0000285, 10.1016/j.jterra.2014.03.002, 10.1080/10298436.2023.2287688 and 10.1109/JIOT.2023.3312353. Optionally also 10.1061/JPEODX.0000074, 10.1061/(ASCE)IS.1943-555X.0000558 and arXiv:1810.05687. Revise the second paragraph of `sections/intro.tex` and `sections/related.tex`.
- *Expected output:* new bibliography entries and revised text.
- *Acceptance:* `paper/make_bib_cited.py` passes, the gap sentence is narrowed, and `REFERENCE_AUDIT.md` gains a section E with the claim checks of the new citations. Before citing Jeong & Jo (2024) for anything beyond "real-vehicle validation", read their full text for the training split.

**L13. Facts in the Data section**
- *Task:* add to `sections/data.tex` the LiRA-CD mounting statement, the P79 survey dates against the car drives, and a pointer to the k-km definition. In the Table S8 caption, write "different reference survey and processing".
- *Acceptance:* each statement cites the LiRA-CD article.

**L14. The "not just a slope" comparator**
- *Task:* add the `c2` arm `idxcar_affine` (k = 1–20 km) to the outputs of `value_real_index.py` or a new script. Add one sentence to Sec. V-D.
- *Acceptance:* the numbers match `outputs/c2_minimal_calibration.txt`.

**L15. Test-route uncertainty at 5 km**
- *Task:* in `paired_vs_real.py`, add draw-averaged predictions with a 5 km block bootstrap of the difference to real-only, for the level-offset and pooled arms at k = 5 and 20.
- *Acceptance:* the intervals are reported in Sec. V-D or Table III.

**L16. Optional P3 items** as listed in Section G.

**L17. Final consistency pass**
- *Task:* regenerate everything. Update `CLAIM_AUDIT_V2.md` (or create a V3), `CHANGELOG.md`, sections E–G of `FINAL_REPORT_V2.md`, and the provenance in `README.md`.
- *Acceptance:*
  - `grep` for "only because", "only through a sensor", "10--15\,Hz", "with 10\,km or more" and "ranks segments within routes as well" finds no unqualified occurrence;
  - both PDFs compile without undefined references or `??`;
  - the page count fits the target venue.
