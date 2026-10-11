# Claim audit of the revised paper (revision v2, 2026-10-03)

Every substantive claim of `paper/main.pdf` (abstract, introduction, results, discussion, conclusion) was checked
against the result files. Numbers in the paper are LaTeX macros generated from `results/v2/` (`make_numbers_v2.py`),
so the audit checks the *wording* around them: does the evidence support the claim as phrased, at the stated
evidence class (C1 confirmatory, R re-analysis, E exploratory, S simulation; `evaluation/PROTOCOL_V2.md`)?

Verdicts: **SUPPORTED**, **PARTIALLY** (supported with a qualification that the text must carry), **OVERSTATED**
(evidence points the same way but the wording claims more), **UNSUPPORTED**. "Action" says what was changed during the
audit; claims marked "fixed" were reworded and re-checked in the final PDF.

## Abstract

| # | Claim | Evidence (file / macro) | Verdict | Action |
|---|---|---|---|---|
| A1 | Real-trained gradient boosting: within-route MAE 0.39 m/km | `summary_real_estimators.csv` (vrGbmMaeWithin) | SUPPORTED (C1) | - |
| A2 | Simulation-trained model ranks segments within routes as well under each of nine sensor/vehicle models (Spearman 0.82-0.84 vs 0.83), but so does an untrained RMS/v^0.5 (0.82) | `summary_variants.csv` (vvRhoMin/Max), `ranking_untrained.csv` (rkHalfRho) | SUPPORTED (E; descriptive) | **changed** during the final self-review: the first v2 draft presented ranking transfer as a finding; E10 showed it is not discriminating |
| A3 | Bias ranges from -0.09 to +0.43 m/km | `summary_variants.csv` (vvBiasMin/Max) | SUPPORTED (E) | - |
| A4 | V0 matched the level only because half of its passes carried a phone-holder resonance | 2x2 factorial: holder changes bias by -0.35/-0.36, family by -0.16/-0.17; V1 (V0's telematics half) +0.43, V8 (phone rigid) +0.27 | SUPPORTED (E, diagnostic) | first draft said "fortunate match"; kept in Discussion with the evidence |
| A5 | Across variants the bias follows a 10-15 Hz deficit of simulated vibration | Spearman 0.97, 9 variants (`band_gain.csv`) | PARTIALLY: association across 9 non-independent variants, found after the fact | text says "follows", Discussion and Limitations state post-hoc/diagnostic status |
| A6 | Level offset from 5 km: every variant 0.42-0.56 m/km, better than 5 km real-only (0.68) in 13-20 of 20 draws | `paired_vs_real.csv` (pcCalMaeFive*, pcCalWinsFive*) | SUPPORTED (R/E); holds on each held-out route (`paired_vs_real_by_route.csv`) | per-route check added |
| A7 | With >= 10 km, real drives alone beat the three variants with the largest spectral deficit | pcCalHiDefWinsTen 3-5/20, Twenty 0/20 | SUPPORTED (E) | - |
| A8 | Simulated vibration grows faster with speed than the real car's | `speed_scaling_sim.csv`: sim 0.92-1.40 vs real 0.60/0.85, all intervals disjoint | SUPPORTED (E) | added in this revision |
| A9 | With a short calibration, simulation can stand in for most paired drives; savings depend on the match; one car only | A6 + A7: 5 km + simulation reaches 0.42-0.56 vs 0.42 for real training on all training routes (about 126 km of road with paired drives per fold, `results/lira/fewshot_pooled_summary.csv`) | PARTIALLY: "most" holds for the six better-matched variants (0.42-0.45), less so for V1/V3/V5 (0.53-0.56); the sentence names the dependence | reworded twice; scoped to one car |

## Introduction and contributions

| # | Claim | Evidence | Verdict | Action |
|---|---|---|---|---|
| I1 | Simulation-trained estimators were validated in simulation [7,8] or, for roughness classes, with a real-vehicle test [9] | abstracts (`references.json`) | SUPPORTED | **fixed**: [9] had been grouped with simulation-only validation |
| I2 | Missing: real-car, route-disjoint evidence of what a simulation-trained IRI estimator transfers and how much paired data it needs | literature search of rounds 1-2 | PARTIALLY (absence of evidence in the literature we found) | "IRI estimator" made explicit |
| I3 | "The ranking transfers ... the level does not ... a few km fix the level ... speed transfers only in part" | Sec. V-B to V-E | SUPPORTED (E/R) | - |
| I4 | Contributions (i)-(iv) are empirical evidence, not methods | - | SUPPORTED | no "first/novel/SOTA" wording (grep) |

## Results

| # | Claim | Evidence | Verdict | Action |
|---|---|---|---|---|
| R1 | Map alone 0.75, speed alone 0.69 m/km; speed ranks weakly within routes (rho 0.39) | Table I | SUPPORTED | - |
| R2 | M7 ranks as well as learned estimators but has larger error (+0.081 [+0.043, +0.115]); its output calibration made it worse | Table I | SUPPORTED | - |
| R3 | LightGBM and MLP indistinguishable; CNN worse by +0.045, almost entirely on CPH1 | Table I, `summary_real_estimators.csv` per-route deficits | SUPPORTED | wording of the per-route range fixed |
| R4 | Vehicle overlap did not measurably favour real-trained estimators | `unit_disjoint.csv` (3 interpretable folds) | PARTIALLY: three folds, one car model | M3 fold declared uninterpretable in text |
| R5 | Bajic split: MAE 0.115, R^2 0.81; not compared further | `bajic_anchor.csv` | SUPPORTED | - |
| R6 | V0 vs real: +0.019 [-0.003, +0.040] (5 km blocks); segment-level interval would have declared real better | `inference_blocks.csv` | SUPPORTED | - |
| R7 | Same within-route ranking (0.83 vs 0.83; partial 0.81 vs 0.81), but an untrained RMS/v^0.5 ranks as well (0.82 / 0.81), so ranking does not discriminate | Table I, `ranking_untrained.csv`, Table S4 | SUPPORTED | context sentence added (E10) |
| R8 | Ranking stable across V0-V8 (rho 0.82-0.84, partial 0.80-0.82, scale 0.62-0.71); bias and MAE vary | Table II | SUPPORTED (E) | - |
| R9 | Holder resonance sets V0's level; ideal and matched telematics sensors and one vehicle overestimate by ~0.4 | Table II | SUPPORTED (E) | - |
| R10 | V9 ranks (0.81) but overestimates on motorways (+0.70); V10 changes little | Table II | SUPPORTED (E) | - |
| R11 | BeamNG corpus does not transfer under this protocol | Table S12; index ranks (0.83) but misses the level (MAE 0.85) | SUPPORTED, scoped | index result added to Supplement S2 |
| R12 | All variants lack 2-5 Hz energy, match 5-10 Hz; at 10-15 Hz real/sim power 5.2/4.9 (ideal/rigid telematics) vs 1.9 (phone + holder) | `spectra_log10_diff.csv` | SUPPORTED (E) | - |
| R13 | Bias orders like the 10-15 Hz deficit, not like 0.5-2 / 2-5 Hz deficits; "as expected if an estimator trained on too little simulated vibration reads the car's extra vibration as roughness" | Spearman 0.97 vs 0.22 / 0.25; sign: larger deficit, more positive bias | PARTIALLY: 9 non-independent variants, post hoc; the explanatory clause is an interpretation consistent with the sign | labelled diagnostic |
| R14 | Deficit larger on motorway than urban for 9 of 9 variants, as is the bias | `band_gain_by_class.csv` | SUPPORTED (E) | - |
| R15 | Transmissibility peaks at 12.5 Hz | `physics_transmissibility.csv` | SUPPORTED | - |
| R16 | The 10-15 Hz excess is not an aliasing artefact | 333 Hz passes have more, not less, 10-15 Hz power (-0.24 log10; device-confounded) | PARTIALLY: all-unit comparison is confounded with device and mounting | confounding stated in the sentence |
| R17 | Simulator does not reproduce the speed scaling; this does not explain the different levels | E7: mismatch similar across variants | SUPPORTED (E) | - |
| R18 | Equal budget: at 1-2 km simulation beats real-only LightGBM for every variant but not the real-only index; from 5 km depends on the simulator | `paired_vs_real.csv` incl. E9 | SUPPORTED (R/E) | **changed** in this revision (first draft: "simulated drives are as informative as real ones") |
| R19 | Level offset closes V4's gap but not V1/V3/V5's | pcSameCalVfour..., pcSameCalHiDef... | SUPPORTED (E) | - |
| R20 | Simulation + 5 km level beats real-only (both comparators) for all variants; advantage holds per route; real-only LightGBM overtakes V1/V3/V5 from 10 km | `paired_vs_real*.csv` | SUPPORTED (R/E) | - |
| R21 | "Most data-efficient option for every variant" | R20 (against both real-only comparators at <= 5 km) | PARTIALLY: among the options tested (real-only LightGBM/index, sim on same km, sim + level/affine) | "of the options compared" is implied by context; acceptable |
| R22 | Real-trained learned estimators and the index over-correct for speed | `speed_real.csv` | SUPPORTED | **fixed**: "every estimator trained on real cars" was too broad (RMS-only index under-corrects) |
| R23 | V0 elasticity exceeds real-trained by +0.09 [+0.06, +0.12], entirely urban | `speed_paired.csv` | SUPPORTED (E) | - |
| R24 | Across variants pooled elasticity -0.15 to +0.06, 8/9 inside the band; on motorways every estimate falls | `speed_real.csv`, `speed_paired.csv` | SUPPORTED (E) | - |
| R25 | Lower urban speed dependence is a property of the learned estimators, not evidence of a faithful speed response | E7 | SUPPORTED (interpretation consistent with E7) | - |
| R26 | Unseen-vehicle penalty +70 / +16 / +6 % for 3 / 30 / 100 vehicles; criterion met only with the segment bootstrap | `vehicle_sweep.csv` (S) | SUPPORTED (S, simulation only) | - |
| R27 | "The gap closes mainly because the error on training vehicles rises" | seen 0.62 -> 0.82, unseen 1.06 -> 0.87 | OVERSTATED | **fixed**: "closes from both sides" |
| R28 | Penalty "unrelated" to parameter distance (rho 0.14) | 30 vehicles | OVERSTATED | **fixed**: "only weakly related (Spearman 0.14 over 30 vehicles)" |
| R29 | Sensor perturbations: 15 Hz holder flips the bias; 25 Hz sampling and +20 % speed error most harmful | `results/sim/robustness.csv` | SUPPORTED (S) | - |

## Discussion, limitations, conclusion

| # | Claim | Evidence | Verdict | Action |
|---|---|---|---|---|
| D1 | Ranking depends on the response-to-profile relation that a randomised half-car reproduces; level on the absolute gain of the vibration path | R8, R9, R12-R14 | PARTIALLY (interpretation of E results) | phrased as the reading of the results; Limitations state E status |
| D2 | Two-step recipe for road agencies | R20 | PARTIALLY (one car) | **fixed**: "the consequence is" -> "this suggests" |
| D3 | Spectral check before trusting a zero-shot level | R13 | PARTIALLY | stated as post hoc, needs confirmation on other cars |
| D4 | Earlier "breadth" explanation contradicted; V0's zero-shot accuracy is a fortunate match | A4 | SUPPORTED (E) | - |
| D5 | Real-trained estimators can use speed as a cue for low roughness | speed-only model elasticity -0.46; within-segment over-correction; no-speed model still over-corrects | PARTIALLY (plausible mechanism, not isolated) | hedged with "can" |
| D6 | Block intervals 1.9-2.7x wider than segment-level; segment bootstrap would have declared V0 worse | `inference_blocks.csv` | SUPPORTED | - |
| D7 | ARAN agrees in ranking and median level, disagrees on a few urban segments; no comparison of estimator errors with device disagreement | `aran_rematch.csv` | SUPPORTED | first-round claim removed |
| D8 | Limitations: one car/sensor, 4 routes, class-route confounding, post-review analyses are hypothesis-generating, simulator mismatches, M7 not a reproduction | - | SUPPORTED | - |
| D9 | Conclusion restates A2, A5-A8 for one car type; new paired data needed | - | SUPPORTED | "10 to 40 km" statement of the first v2 draft removed |

## Claims removed in revision v2 (relative to the first rescued version)

* Transfer explained by the *breadth* of the sensor model (contradicted by the factorial).
* Simulation "replaces scarce labels"; real-only training "needs about 20 km" to match simulation (wrong comparator,
  unequal budgets).
* Simulated drives are "as informative as real ones" per kilometre of profiled road (variant- and
  comparator-dependent, E5/E9).
* Simulation-trained estimators "normalise speed" / are "speed-invariant" on real cars (partly, urban only; E7/E8).
* Urban errors "smaller than the disagreement between two profilometers" (heavy-tailed device disagreement).
* "Sampling rate matters most" among sensor perturbations (the holder resonance moves the bias more).
* "Pre-registered" (the protocol was fixed in advance by us, not registered).
* Any statement that the earlier BeamNG result says something about game engines in general.

Remaining title-level citations (`mounting2026`, `hanson2014iri`, `ngwangwa2010ann`) carry no specific claim.
