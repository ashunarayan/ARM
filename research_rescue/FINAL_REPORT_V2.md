# Final report, revision v2 (response to the independent review `review/first.md`)

Date: 2026-10-03. Scope: second research and revision cycle of the rescued IRI paper. Inputs: `review/first.md`, the
first-round paper and documents (`paper/v1_archive/`, `FINAL_REPORT.md`, `REVIEWER_AUDIT.md`). Protocol:
`evaluation/PROTOCOL_V2.md`, frozen before any v2 analysis, with dated addenda E5-E10 written before each added
analysis was run. Every number below is a macro of `paper/numbers_v2.tex` (generated from `results/v2/`); the headline
numbers and their provenance are in `results/v2/final_results_v2.csv`.

Deliverables: `paper/main.pdf` (10 pages), `paper/supplementary.pdf` (14 pages) and their sources; scripts in
`experiments/v2/` and `make_*_v2.py`; figures `figures/v2_*`; tables `tables/v2_*`; results `results/v2/`;
`REVISION_PLAN_V2.md`; `CLAIM_AUDIT_V2.md`; `REVIEWER_AUDIT_V2.md`; `CHANGELOG.md`; `README.md`;
`environment_lock.txt`; `run_all_experiments.py`.

## A. Reviewer criticisms that were verified

(Details, evidence and fixes per item: `REVISION_PLAN_V2.md`.)

1. **The "sensor breadth" mechanism is wrong.** V0's telematics half alone (V1) has zero-shot MAE 0.68 and bias +0.43
   m/km; its phone-like half (V2) 0.41 / -0.09. A new 2x2 factorial (V7 telematics + holder, V8 phone rigid) shows that
   the holder resonance changes the bias by -0.35 / -0.36 m/km, the sensor family by -0.16 / -0.17.
2. **The zero-shot headline was fragile.** Across nine measured-profile variants the bias spans -0.09 to +0.43 m/km.
3. **Shape vs level.** A level offset makes most variants usable; level is the part that does not transfer.
4. **The "about 20 km" statement** used the wrong simulation set and unequal profile budgets.
5. **Crossover imprecision** (5 draws) - now 20 matched draws, ranges and draw counts.
6. **Unequal profilometer budgets** - equal-budget design added for all variants.
7. **Route-disjoint is not vehicle-disjoint** - disclosed and tested (see B for the consequence).
8. **External validity** (one car, four routes) - stated; not fixable here.
9. **Missing literature** (Skar & Levenberg 2024; Jeong et al. under-described) - added and checked; Agebjar et al.
   2025 added; calibrated quarter-car inversion baseline M7 built.
10. **No anchor to Bajic et al. 2021** - within-road anchor on our M3 data (MAE 0.115, R^2 0.81), not like-for-like.
11. **Wrong resampling unit** - residual autocorrelation 0.44 at 100 m; 5 km-block intervals are 1.9-2.7x wider than
    segment-level ones; V0 vs real +0.019 [-0.003, +0.040] is not a supported difference.
12. **Pooled metrics headlined** - within-route metrics are primary.
13. **Missing map-only prior** - M0b, within-route MAE 0.75.
14. **Missing calibrated physics baseline** - M7 (0.46, rho 0.83; +0.081 [+0.043, +0.115] vs LightGBM).
15. **CNN reporting** - ensemble vs per-seed; its deficit sits on CPH1.
16-17. **Speed claims were simulation-only** - fixed-road elasticities on real roads added (R5, E7, E8).
20-21. **BeamNG and PVS statements over-reached** - re-scoped, moved to the supplement.
22. **Passes-needed curve used different segment subsets** - fixed subset.
23. **"Pre-registered"** - corrected everywhere, including a v1 table generator that still had it.
24. **No primary simulation set named** - V0 (`p79`) primary, V10 (`p79+iso`) beside it.
25. **Holder resonance moves the bias in the robustness sweep** (-0.65 -> +0.37) - reported for all perturbations.
26-29. **Structure, novelty, overstated claims, conditional CIs** - one story, empirical contributions, claim audit,
    stated conditioning.
31. **Independent real confirmation is needed for a journal** - true; not possible with the available data.

## B. Criticisms rejected or only partly accepted, and why

* **ARAN data contaminated by the opposite lane (#19): rejected.** ARAN files are per direction and their own
  heading agrees with the P79 track for >= 99.8 % of records in all eight files; the urban disagreement persists on
  CPH1 with surveys one month apart. *Accepted part:* the inference "estimator errors are smaller than device
  disagreement" was unvalidated - the disagreement is driven by a heavy tail (5 % of urban segments above 15 m/km,
  median ratio 1.07) - and was removed.
* **Vehicle overlap favours the real-trained model (#7, consequence): not supported.** Unit-disjoint training equals
  size-matched controls on the three interpretable folds (CPH1 0.63 vs 0.63, CPH6 0.69 vs 0.70, M13 0.15 vs 0.15).
  The disclosure itself was accepted.
* **"The LiRA zero-shot test is itself an unseen-vehicle test" (#18): partly.** The Renault Zoe is not among the
  simulated vehicles, but its zero-shot level depends on the sensor model (A.1-2), so it does not test vehicle
  generalisation cleanly. The controlled vehicle-number sweep was added instead.
* **Reproducibility (#30): partly.** PVS is public; committing the work and releasing the BeamNG corpus are the
  authors' decisions and were not done.
* **Novelty "low-moderate" (#27): accepted as a positioning issue**, not as a reason to inflate: the paper now claims
  empirical evidence, not methods.

## C. Experiments added (new simulation or new model fits)

| Item | Script | What it adds |
|---|---|---|
| V7, V8 simulator variants | `experiments/sim_generate.py telecompliant phonerigid` | complete 2x2 sensor factorial |
| Zero-shot + calibration, all variants (E1/E2/R3) | `experiments/v2/simreal_variants.py` | V0-V10, V7/V8 full, BeamNG; level offset and affine from k km, 20 draws |
| Equal profile budget, V0 (R4) and V1-V8 (E5) | `value_of_simulation.py`, `value_of_simulation_variants.py` | simulated vs real drives over the same k km |
| Real-only vibration index on the same draws (E9) | `value_real_index.py` | stronger small-sample comparator |
| Calibrated quarter-car inversion M7 (R10) | `physics_inversion.py` | physics baseline in the spirit of Skar & Levenberg |
| Unit-disjoint baseline, Bajic anchor, fixed-subset passes (R2/R7/R8) | `real_baselines_v2.py` | benchmark checks |
| ARAN heading-constrained re-match (R9) | `aran_rematch.py` | reference uncertainty |
| Re-simulated spectra of four sensor variants + ideal sensor (E3) | `spectra.py` | where simulated and real vibration differ |
| Number of training vehicles at fixed data (S1) | `vehicle_sweep.py` | unseen-vehicle penalty vs N (simulation only) |

## D. Analyses added (no new model fits)

`verify_review_claims.py` (checks of the review's statements on existing results), `inference_blocks.py` (segment,
1 km, 5 km and route-level intervals; residual ACF; variance components), `speed_real.py` (fixed-road speed
elasticities), `speed_paired.py` (E8, paired elasticity differences), `speed_scaling_sim.py` (E7, raw vibration speed
scaling in simulation vs reality), `band_gain.py` (E4, incl. by road class), `paired_vs_real.py` (E5/E6/E9, draw-by-draw
pairing, per-route version), `ranking_untrained.py` (E10, within-route ranking by untrained statistics),
`summarise_v2.py`, `make_final_results_v2.py`.

## E. Claims that changed

| First-round claim | Revised claim |
|---|---|
| Simulation-trained gradient boosting transfers to real cars (MAE 0.44 zero-shot) | The pre-specified simulator matched the level only because half of its passes carried a phone-holder resonance; across nine variants the zero-shot bias spans -0.09 to +0.43 m/km and follows a 10-15 Hz deficit |
| Ranking/"shape" transfers (first v2 draft) | Within-route ranking does not discriminate: an untrained RMS/v^0.5 ranks segments as well (0.82 vs 0.83); what has to be learned is the level |
| Simulation replaces scarce labels; real-only needs ~20 km to match | With a level offset from 5 km of paired drives, simulation beats training on those 5 km for every variant (13-20 of 20 draws, all four routes, against both real-only comparators); from 10 km real drives beat the three worst-matched variants |
| Simulated drives are as informative as real ones per km of profile (first v2 draft) | At equal profile budget the answer depends on the variant and on the real-only comparator |
| Simulation-trained estimators are speed-invariant / normalise speed | They over-correct less than real-trained ones on urban roads (paired +0.09 [+0.06, +0.12]) but not on motorways, and simulated vibration scales with speed differently from the real car's |
| Generalises to unseen vehicles | Simulation only: penalty +16 % at 30 vehicles, <= 10 % from 100 vehicles under the segment (not the route) bootstrap |
| CNN worse than LightGBM | CNN worse by +0.045 [+0.019, +0.075], almost entirely on one route; MLP negligibly worse on all four routes |
| Differences "significant" at segment level | Supported only if the 5 km-block interval excludes zero; route-level intervals include zero for most comparisons |

## F. Claims removed

Breadth of the sensor model explains transfer; "about 20 km" of real data needed; simulation "replaces labels";
simulated drives as informative as real ones per km; speed invariance on real cars; urban errors smaller than the
disagreement between two profilometers; "sampling rate matters most"; "pre-registered"; any generalisation from the
BeamNG result to game engines in general; PVS as evidence about IRI (moved to the supplement as a negative note).

## G. Strongest supported contribution now

On public profilometer-referenced data of one production car, with route-disjoint evaluation and spatially honest
inference: **a simulator built on measured road profiles supplies, for most sensor models, the vibration-to-IRI
mapping up to a level offset, but not the level itself; the level error depends on the simulated sensor path and
follows a 10-15 Hz vibration deficit; and simulation over all profiled roads plus a level offset from 5 km of paired
drives beats training on those 5 km for every simulator variant, while with >= 10 km of paired drives its advantage
depends on how closely the simulated vibration matches the car.** Supporting results: a benchmark with no-vibration,
physics-based (incl. a calibrated quarter-car inversion), learned and simulation-trained estimators; fixed-road speed
elasticities on real roads; a corrected post-mortem of the earlier BeamNG pipeline (supplement).

## H. What remains unresolved

* The physical cause of the real car's 10-15 Hz excess (sensor mounting, unsprung dynamics, tyre enveloping, roll,
  two-wheel-path averaging) and of the steeper simulated speed scaling.
* Whether the 10-15 Hz spectral check predicts the level error for other cars (found post hoc on nine non-independent
  variants).
* Evidence class: everything beyond the V0 comparison was analysed after the test routes were used.
* Route-level inference: with four routes, most differences are not resolved at the route level.
* Residual 5 km correlation (0.13), so even block intervals may be somewhat narrow.
* Three title-level citations (`mounting2026`, `hanson2014iri`, `ngwangwa2010ann`) should be read by a human.
* Nothing is committed to git (needs the authors' authorisation).

## I. What requires genuinely new physical or real-world data

1. Paired drives of a **second car type** (ideally a different telematics unit or mounting) over profiled roads,
   collected **after freezing** the simulator, the calibration protocol (k, block sampler) and the analysis code - the
   only way to make the level/calibration findings confirmatory and to test vehicle generalisation on real data.
2. A **different road network or city**, so that route-level inference has more than two routes per class.
3. A **transfer-function measurement of the telematics unit's mounting** (tap or shaker test in the car) to test
   whether the 10-15 Hz excess is the mounting or the vehicle.
4. **Controlled constant-speed runs** over a few profiled segments to measure the car's speed response without
   naturalistic confounding.
5. A **reference survey simultaneous** with the car passes (the P79 and car data are from different dates).

## J. Exact reproduction commands

Environment: `pip install -r research_rescue/environment_lock.txt` (Python 3.11; see `README.md`). From the
repository root:

```bash
# complete pipeline, both rounds, including the paper (skips steps whose outputs exist; --force recomputes)
python research_rescue/run_all_experiments.py

# second round only (after the first-round steps), in order
python research_rescue/run_all_experiments.py --only v2_verify_review v2_sim_factorial v2_variants v2_value \
    v2_value_variants v2_value_real_index v2_inference v2_speed_real v2_speed_paired v2_real_baselines v2_aran \
    v2_physics_inversion v2_spectra v2_band_gain v2_band_gain_class v2_speed_scaling v2_ranking_untrained \
    v2_vehicle_sweep v2_summarise v2_paired v2_figures v2_tables v2_numbers v2_final_results bib_cited paper
```

The individual commands behind each step are listed in `README.md` ("Second round only"). Regenerating the
summaries, tables, figures and macros from the same result files reproduces `paper/numbers_v2.tex` byte for byte.
