# Final report: research rescue of the desk-rejected IRI paper

Original: "Simulation-Based Multi-Vehicle IRI Estimation via Physics-Informed Smartphone Sensing" (IEEE ICONAT 2026,
paper 3979, desk-rejected). Rewritten: "How Far Can Simulation Take Vehicle-Based IRI Estimation? A Route-Disjoint
Study on Profilometer-Referenced Car Data" (`paper/main.pdf`, 10 pages; `paper/supplementary.pdf`, 6 pages).
Date: 2026-10-02. The original code, data and paper are untouched (`BASELINE_STATE.md`).

## A. What changed

1. **Question and evidence.** The paper no longer claims a new estimator validated in a game engine. It asks how far
   simulation takes vehicle-based IRI estimation and answers on public real-car data with profilometer IRI
   (LiRA-CD, 168 km of distinct 100 m segments, 4 routes, leave-one-route-out). The BeamNG corpus is used only to
   diagnose the earlier protocol.
2. **Labels.** A new IRI implementation (ASTM E1926 / Sayers 1995) is validated against the P79 profilometer's own
   IRI; all labels are recomputed from P79 profiles. The earlier "curvature-adaptive mesh correction" was shown to
   remove real roughness (it is no longer used).
3. **Protocol.** Frozen before test evaluation (`evaluation/FINAL_EVALUATION_PROTOCOL.md`): route/map-disjoint
   splits, segment-level units, cluster bootstrap (2000 resamples), paired tests with Holm correction, no filtering,
   capping or calibration on test data, claim criteria for speed invariance and vehicle generalisation fixed in advance.
4. **Baselines.** A ladder M0-M6: constant, speed only, four vibration indices RMS/v^alpha, LightGBM, MLP, the earlier
   1D-CNN, and inner-validation model selection; the earlier full recipe is re-implemented and checked against the
   earlier tensors.
5. **Simulator.** A new parametric half-car with randomised vehicles and a sensor model replaces BeamNG as the
   simulation source; it is unit-tested (state-space, Runge-Kutta, modal frequencies, preprocessing).
6. **Experiments.** Zero-/few-shot simulation-to-real, controlled speed sweeps, unseen-vehicle tests, sensor
   robustness, PVS re-analysis, BeamNG protocol re-analysis, one-at-a-time ablations, a post-hoc sensor sensitivity
   analysis.
7. **Writing.** Every number in the paper is a generated macro (`make_numbers.py`, 1699 macros); promotional
   wording removed; "pre-registered" replaced by "fixed in advance"; "physics index" renamed "vibration index".
8. **References.** 4 non-existent references removed, wrong metadata corrected, all 37 citations of the new paper
   claim-checked (`references/REFERENCE_AUDIT.md`).
9. **Review.** Two rounds of adversarial self-review with 32 fixes (`REVIEWER_AUDIT.md`).

## B. Experiments completed

| Experiment | Script | Main outputs |
|---|---|---|
| Audit of the legacy pipeline (leakage, labels, duplicates, weighting) | `audit/run_audits.sh` | `audit/outputs/` |
| IRI implementation vs P79 (and legacy pipeline, ARAN9000) | `evaluation/iri_unit_test.py` | `results/iri_validation.json`, Fig. 2 |
| CPH6-HH alignment search | `evaluation/cph6hh_alignment.py` | `results/iri_alignment_search.json` |
| LiRA-CD sensor statistics | `evaluation/lira_sensor_stats.py` | `results/lira_sensor_stats.json` |
| Route overlap | `evaluation/route_overlap.py` | `results/route_overlap.json` |
| Simulator unit tests | `evaluation/sim_unit_test.py` | `results/sim_unit_test.json` |
| Legacy re-implementation fidelity | `experiments/legacy_fidelity_check.py` | `results/legacy_fidelity_check.json` |
| BeamNG: S1/S2/S3 splits, legacy recipe, discard rule, unseen vehicle | `experiments/exp_beamng.py`, `exp_beamng_vehicle.py` | `results/beamng/` |
| LiRA-CD ladder M0-M6, per route, pass level, 1 km blocks | `experiments/exp_lira.py ladder` | `results/lira/ladder_*` |
| Simulation vs real vibration gap, speed exponents | `exp_lira.py gap`, `make_figures.py` | `results/lira/gap_summary.json`, Fig. 6 |
| Zero-shot (5 simulation sets + BeamNG) | `exp_lira.py zeroshot`, `exp_lira_compare.py` | `results/lira/zeroshot_*`, `compare_zeroshot_vs_real.csv` |
| Few-shot (1-20 km and all; 5 draws) | `exp_lira.py fewshot` | `results/lira/fewshot_raw.csv`, Fig. 5 |
| Within-route ranking given speed, passes needed, speed bands | `experiments/exp_lira_analysis.py` | `results/lira/analysis_*` |
| Controlled: unseen vehicles, suspension extrapolation, speed sweeps, robustness | `experiments/exp_sim_controlled.py` | `results/sim/` |
| Speed sweep for estimators trained on measured profiles (secondary) | `exp_sim_controlled.py speed_p79` | `results/sim/speed_invariance_p79trained.csv` |
| PVS: surface/quality AUCs for speed, vibration, earlier model | `experiments/exp_pvs.py` | `results/pvs/` |
| Post-hoc: zero-shot with sensor matched to measured LiRA-CD statistics | `sim_generate.py measuredsensor`, `exp_lira.py zeroshot_sensor` | `results/lira/zeroshot_sensor_*` |

## C. Experiments not completed, and why

| Not done | Why |
|---|---|
| Real-world test on other vehicles, phones or mountings | No public data with these and reference profiles were available to us; needs field drives over profiled roads |
| Data from another city or road network | LiRA-CD is the only public car-vibration dataset with profilometer IRI we used; adding another requires finding or collecting one |
| Re-collection of the BeamNG corpus with synchronised sampling | Needs the BeamNG.tech installation and manual driving; no longer needed, since BeamNG is only used for diagnosis |
| Hyper-parameter search for the CNN | Deliberately not done (fixed in advance); stated as a limitation |
| Few-shot CNN at 2 and 10 km; zero-shot CNN on all simulation sets | Compute allocation fixed in advance (S1 of the supplement) |
| Numerical comparison with Bajic et al. (2021, same data set) | Their split and numbers are not in the abstract; the full paper has to be read by a person |
| Window lengths other than 100 m | Out of scope; stated as a limitation |
| IRI-code validation on LTPP profiles | Replaced by validation on LiRA-CD's P79 profiles against the device's own IRI, i.e. on the data actually used |

## D. Final metrics

Generated from `results/paper_numbers.json` by `make_key_metrics.py` (identical to the numbers in the paper).

<!-- BEGIN KEY METRICS -->
| Quantity | Value |
|---|---|
| **Label validity** | |
| IRI code vs P79-reported IRI (100 m, 7 consistent files) | r = 1.000, bias +0.018 m/km, MAE 0.019 m/km, n = 1,520 |
| CPH6-HH reported IRI vs its own profile (best over +/-3 km shifts, reversal) | r = 0.13 (controls 1.000) |
| Earlier mesh correction on real profiles, urban / motorway | -28 % / -6 % (bias -1.10 / -0.09 m/km) |
| ARAN9000 vs P79, urban / motorway (MAE, r) | 1.69 m/km, 0.54 / 0.14 m/km, 0.95 |
| BeamNG: summed-IRI reduction by the correction; FHWA class changes | 64 %; 34 % |
| **Earlier protocol on BeamNG (earlier labels)** | |
| Earlier recipe, earlier split (S3) / leave-one-map-out (S1), MAE | 1.67 [1.29, 2.11] / 1.99 [1.76, 2.25] m/km |
| Same, uncalibrated, leave-one-map-out (mean over seeds) | 251 m/km |
| Discard rule (> 40 m/km) on uncalibrated S3 predictions | 1-2 segments/seed removed; worst MAE 1,555 -> 1.94 m/km |
| Vehicle and map unseen (S2): constant / vibration index / LightGBM / CNN | 7.60 / 6.88 / 7.25 / 11.06 m/km |
| **Real cars, LiRA-CD, leave-one-route-out, 100 m segments** | |
| LightGBM | MAE 0.42 [0.39, 0.45] m/km, Spearman 0.95, kappa 0.91 |
| MLP (= inner-validation choice M6) | MAE 0.42 [0.40, 0.45] m/km (diff +0.00, p = 0.458) |
| 1D-CNN (earlier architecture) | MAE 0.48 [0.45, 0.51] m/km (diff +0.06, p <0.001) |
| Vibration index, alpha fitted / alpha = 2 | 0.67 / 0.73 m/km |
| Speed only / constant | 0.74 / 1.67 m/km |
| LightGBM urban routes (CPH1, CPH6) / motorways (M3, M13) | 0.60, 0.70 / 0.13, 0.15 m/km |
| Partial Spearman given speed, LightGBM vs speed-only (urban / motorway) | 0.82 / 0.80 vs 0.07 / 0.30 |
| **Simulation to real (LiRA-CD, LightGBM)** | |
| Trained only on simulated drives over measured profiles of other routes | MAE 0.44 [0.41, 0.47] m/km (paired diff to real training +0.02 m/km, p = 0.001) |
| Same, urban / motorway | 0.63 / 0.20 m/km (real training: 0.64 / 0.14) |
| Synthetic profiles only / one fixed vehicle / ideal sensor | 0.71 / 0.63 / 0.67 m/km |
| Trained on the BeamNG corpus (earlier labels / raw-profile labels) | 1.36 / 1.97 m/km |
| Real-only with 1 / 5 / 20 km / all routes | 1.41 / 0.82 / 0.46 / 0.42 m/km |
| Simulation + 1 / 5 / 20 km / all routes | 0.46 / 0.45 / 0.43 / 0.41 m/km |
| **Speed** | |
| PVS AUC asphalt vs rest: speed / earlier model / RMS/sqrt(v) | 0.97 / 0.94 / 0.99 |
| PVS AUC bad vs regular: speed / earlier model / RMS | 0.75 / 0.41 / 0.23 |
| Sweep 40->100 km/h, trained on synthetic: on synthetic / on measured (LightGBM) | +1 % (yes) / +60 % (no) |
| Sweep 40->100 km/h, trained on measured profiles (LightGBM) | -1 % (yes) |
| Kinetic normalisation (v_ref/v)^2 on synthetic / measured | -52 % / -32 % |
| Speed exponent gamma of vibration: LiRA urban / motorway / simulator | 0.60 / 0.79 / 1.20 |
| **Controlled generalisation and robustness (simulation)** | |
| Unseen vehicles, parametric: LightGBM / CNN / vibration index (relative MAE increase) | +19 % / +24 % / +15 % (criterion <= 10 %: no/no/no) |
| Unseen vehicle, BeamNG: LightGBM / CNN | +21 % / +27 % |
| Sampling rate 200 / 50 / 25 Hz (LightGBM MAE) | 0.77 / 0.87 / 1.39 m/km |
<!-- END KEY METRICS -->

<!-- BEGIN POSTHOC -->
Post-hoc sensitivity analysis (added after all primary results; reported, not used for the primary claims):
zero-shot LightGBM and vibration index trained on simulated drives over measured profiles with
`p79` = the primary sensor mixture (telematics 55-62 Hz / smartphone-like, 50/50),
`p79-measuredsensor` = only a telematics sensor matched to the measured LiRA-CD statistics,
`p79-measuredmix` = the matched telematics sensor mixed 50/50 with the primary smartphone-like sensor.
Paired differences to `p79` LightGBM on the same 1,678 segments.

| Simulation set / estimator | MAE [95 % CI] | Spearman | paired diff to p79 LightGBM [95 % CI] |
|---|---|---|---|
| Z sim[p79] physics index (alpha fitted in sim) | 0.575 [0.543, 0.610] | 0.942 | +0.136 [+0.107, +0.168], p_Holm < 0.001 |
| Z sim[p79] LightGBM | 0.439 [0.412, 0.469] | 0.953 | ref. |
| Z sim[p79-measuredsensor] physics index (alpha fitted in sim) | 0.625 [0.595, 0.658] | 0.942 | +0.187 [+0.159, +0.216], p_Holm < 0.001 |
| Z sim[p79-measuredsensor] LightGBM | 0.687 [0.664, 0.714] | 0.942 | +0.248 [+0.233, +0.263], p_Holm < 0.001 |
| Z sim[p79-measuredmix] physics index (alpha fitted in sim) | 0.538 [0.511, 0.567] | 0.944 | +0.099 [+0.077, +0.123], p_Holm < 0.001 |
| Z sim[p79-measuredmix] LightGBM | 0.455 [0.427, 0.488] | 0.951 | +0.016 [+0.008, +0.024], p_Holm < 0.001 |
<!-- END POSTHOC -->

## E. Main finding

On real cars with profilometer IRI and unseen routes, gradient boosting on hand-crafted vibration and speed features
is the best estimator tried; an estimator trained only on a randomised half-car and sensor simulator driven over
measured road profiles is almost as accurate (equal on urban roads, worse on smooth motorways) and replaces about
20 km of profilometer-labelled car data, whereas the earlier game-engine pipeline does not transfer because its
labels were not IRI. The transfer depends on randomising the simulator broadly (measured profiles, many vehicles,
several sensor types): a single sensor configuration, even one matched to the car's measured sensor statistics,
transfers much worse (post-hoc: 0.69 instead of 0.44 m/km). Speed is both a necessary input and a confounder: pooled
metrics and crowdsourced labels reward speed shortcuts, learned speed corrections hold only for the road spectra
seen in training, and no accurate estimator generalised to unseen vehicles in simulation.

## F. Remaining limitations

- One car model and telematics unit type (Renault Zoe, AutoPi), four routes in one region; urban and motorway routes
  differ systematically; confidence intervals cover segment sampling within these routes, not route-to-route variation.
- Vehicle and phone generalisation tested only in simulation, where it failed for every accurate estimator.
- Linear half-car without roll (mean of both wheel-path profiles), tyre lift-off or non-linear suspension.
- The simulator's primary telematics configuration was set from an inaccurate preliminary inspection (disclosed).
  The post-hoc re-run with the telematics half matched to the measured statistics gives 0.46 instead of 0.44 m/km,
  so the primary result does not hinge on that error, but it does hinge on the breadth of the sensor model.
- The protocol was fixed before the test evaluation but not registered with a third party.
- The earlier study is unpublished; contributions (i)-(ii) are a case study.
- Three citations checked at title level only.

## G. Claims removed (from the submitted paper)

- "Physics-informed" pipeline, "multi-vehicle"/vehicle-agnostic generalisation, "speed invariance" (no controlled
  test supported them; the controlled tests now in the paper reject vehicle generalisation).
- MAE 1.650 m/km, R^2 0.521 as an IRI result (labels were not IRI; the test track was used for early stopping and
  calibration; predictions above 40 m/km were discarded).
- "77.9 % within the +/-1.5 m/km operational tolerance inspired by AASHTO R 56" (R 56 certifies profilers; it defines
  no tolerance for estimators).
- "Zero-shot validation on 108 km of PVS: correctly ranks surface degradation and pinpoints defects" (PVS has no IRI;
  speed alone explains the labels at least as well).
- "The curvature-adaptive mesh correction removes rendering artefacts to produce ground truth" (it removes 28 % of
  the IRI of real urban roads).
- "2-D inverse-frequency sampling" as a working component (the Keras loss ignored per-sample weights).
- Profilometer cost figures, road-statistics claims and all statements resting on the 4 non-existent and 4
  mis-attributed references.
- Promotional wording ("crucially", "universal benchmark", "state-of-the-art").

## H. Claims newly supported

| Claim | Evidence |
|---|---|
| The IRI implementation reproduces the profilometer's IRI from the same profiles | Fig. 2a, `iri_validation.json` |
| Game-engine-derived labels with the mesh correction are not IRI | Fig. 2b, BeamNG label statistics |
| Calibration on the test track and prediction filtering hid diverging predictions | `results/beamng/` |
| LightGBM/MLP on vibration and speed features beat a CNN and speed-only and vibration-index baselines on unseen routes | Table II, paired tests |
| Vibration-based estimators carry roughness information beyond speed within routes | partial Spearman, Section VII-D |
| Simulation over measured profiles transfers to real cars almost as well as real training and replaces about 20 km of labelled data | Tables III-IV, Fig. 5 |
| Vehicle randomisation, the sensor model and measured profiles each matter for transfer | Table IV ablations |
| Breadth of the sensor model matters more than matching the target sensor (post-hoc) | Table IV (marked), Supplement S1, section D above |
| PVS labels are explained by speed as well as by vibration | `results/pvs/pvs_auc.csv`, Fig. 4a |
| Learned speed corrections are tied to the training road spectrum | Fig. 4b, Table V |
| Accurate estimators do not generalise to unseen vehicles (in two simulators) | Table V |

## I. Target venue type

A journal or a long-format conference in transportation infrastructure sensing or pavement engineering that values
reproducible evaluation and accepts mixed positive/negative results, for example Transportation Research Record,
International Journal of Pavement Engineering, Road Materials and Pavement Design, Journal of Computing in Civil
Engineering, Measurement, IEEE Sensors Journal, or Data-Centric Engineering. The paper is 10 pages in IEEE conference
format; a 6-page conference would need Tables IV-V and Fig. 6 moved to the supplement. Check each venue's current
scope and length rules before submitting.

## J. Reproduction commands and remaining human actions

```bash
# everything (skips finished steps; --force recomputes; logs in research_rescue/logs/)
C:/Users/nishk/anaconda3/envs/torch_gpu/python.exe research_rescue/run_all_experiments.py
# only the paper from existing results
C:/Users/nishk/anaconda3/envs/torch_gpu/python.exe research_rescue/run_all_experiments.py --only figures tables numbers bib_cited paper
```
Individual steps and run times: `README.md`.

Actions that need a person:
1. Read and approve the rewritten paper with the co-author, including the disclosure that it revises an earlier,
   unpublished study of yours.
2. Choose the venue and adapt format and length (section I).
3. Decide where to release code, protocol and predictions (the paper says they are provided with it), and commit
   `research_rescue/` to version control so the protocol's timestamp can be verified. Nothing has been committed.
4. Read the three title-level references (`mounting2026`, `hanson2014iri`, `ngwangwa2010ann`) and Bajic et al.
   (2021) in full; add a numerical comparison with Bajic et al. if their protocol allows it.
5. Optional, to remove the main limitations: field drives with two or more vehicles or phone mountings over roads
   with a reference profile survey.
