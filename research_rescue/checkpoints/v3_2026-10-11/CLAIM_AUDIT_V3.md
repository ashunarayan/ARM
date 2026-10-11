# Claim audit of the revised paper (revision v3, 2026-10-11)

Every substantive claim of `paper/main.pdf` (abstract, introduction, results, discussion, limitations, conclusion)
and the corrected-statement list of the supplement was checked against the result files after the final compile.
Numbers are LaTeX macros (`paper/numbers.tex`, `numbers_v2.tex`, `numbers_v3.tex`) generated from `results/`, so
the audit checks the *wording* around them. Evidence classes: C1 confirmatory, R re-analysis, E exploratory,
S simulation (`evaluation/PROTOCOL_V3.md`). Verdicts: **SUPPORTED**, **PARTIALLY** (supported with a qualification
the text carries), **OVERSTATED**, **UNSUPPORTED**. "Action" records changes made during this audit.
Independent re-derivations of the key numbers: `evaluation/verify_v3.py` (25 checks, all passed;
`results/v3/verification_v3.json`).

## Abstract

| # | Claim | Evidence (file / macro) | Verdict | Action |
|---|---|---|---|---|
| A1 | Real-trained gradient boosting: within-route MAE 0.39 m/km | `results/v2/summary_real_estimators.csv` (vrGbmMaeWithin) | SUPPORTED (C1) | - |
| A2 | Simulation-trained model ranks within routes about as well under each of nine models, but so does, within 0.05 in Spearman on every route, an untrained RMS/v^0.5 | `summary_variants.csv` (vvRho 0.82-0.84 vs 0.83); `results/v3/rank_paired.csv` (max per-route difference 0.044 for real-, V0-, V1-trained LightGBM; rpAbsMax is the rounded-up bound) | SUPPORTED (E) | **changed** from v2 "ranks as well"; the bound is stated for the three estimators tested |
| A3 | Zero-shot bias -0.09 to +0.43 m/km; depends on the simulated sensor path, through the features carrying vibration above 10 Hz, and on the simulated vehicle population | vvBias*; `band_limited.csv` (spread of mean level 0.25 -> 0.08 without features above 10 Hz; dropping only 10-15 Hz changes <= 2 %); V4 (+0.39 m/km vs V0 with the same sensors) | SUPPORTED (E); "through the features" states the model-level nature of the intervention | **changed** from v2 "only because ... holder resonance" and "follows a 10-15 Hz deficit" |
| A4 | With 5 km of profiled road and its paired drives, level offset (0.42-0.56) or joint training (0.45-0.47) beat training on those drives alone (0.68) for every variant | pcCalMaeFive*, pcCalWinsFive (13-20/20), poMaeFive*, poWinsFiveRange (20/20); `calib_uncertainty.csv`: all 18 test-route intervals exclude zero | SUPPORTED (R/E) | MAE labelled pooled |
| A5 | ... even with one pass per segment | `pass_density.csv`: m = 1, both arms better than real-only in every draw for every variant (largest margin -0.041) | SUPPORTED (E) | new |
| A6 | With 20 km, joint training stayed better for every variant | poDiffTwenty -0.03..-0.01, 16-20/20 draws; all 9 test-route intervals below zero | SUPPORTED (R/E); not on every route (5/36 cells), stated in Sec. V-D | - |
| A7 | Real drives alone beat the level offset for the three variants with the largest vibration deficit at 10-15 Hz | V1, V3, V5 (10-15 Hz ratio 2.27-2.41, the three largest); 0/20 draws at 20 km; intervals +0.08..+0.12 | SUPPORTED (E) | **fixed** during the audit: "whose vibration matched the car worst" was ambiguous (V4 has the largest overall-RMS deficit) |
| A8 | Simulated vibration grows faster with speed than the real car's | `speed_scaling_sim.csv` (0.92-1.40 vs 0.60/0.85) | SUPPORTED (E) | - |
| A9 | For this car, simulation over profiled roads replaced most paired drives; other vehicles need new paired data | A4-A6; real-only needs 20-40 km for 0.44-0.46 (Table III) | SUPPORTED (scoped to one car) | - |

## Introduction and related work

| # | Claim | Evidence | Verdict | Action |
|---|---|---|---|---|
| I1 | Simulation-trained estimators validated in simulation [7,8] and tested on real vehicles for WLP [9], profile reconstruction [10], roughness classes [11]; calibrated models invert vibration [12,13] or set an IRI-vibration relation by simulation [14] | `references/REFERENCE_AUDIT.md` §D-E (abstracts; Bajic et al. full text for [9], [10]) | SUPPORTED; [9] and [10] via secondary description | new citations |
| I2 | Gap: evidence for continuous IRI from a production car on held-out roads of public data, of which parts transfer, which simulator choices set the level, how much paired data | none of [7-14], [27], [28] does all of this (REFERENCE_AUDIT) | SUPPORTED as narrowed | **narrowed** per review D3 |
| I3 | "Three parts" paragraph (ranking within 0.05; level depends on sensor path and vehicle population; 5 km fixes it for both combinations; 20 km joint vs offset; speed) | as A2-A8 | SUPPORTED | rewritten |
| I4 | Contributions (ii) "associate ... and test which inputs carry it"; (iii) names the three combination methods, intervals, pass density | Secs. V-B to V-D | SUPPORTED | reworded per review |
| R1 | Nitsche et al. validated simulation-trained regressors on a probe vehicle for WLP, "as Bajic et al. note, without the effect of varying speed" | Bajic et al. (arXiv 2107.01199) full text, quoted in REFERENCE_AUDIT §E | SUPPORTED (secondary) | attribution made explicit |
| R2 | Wu et al. calibrate a full-car model by impact tests and derive a linear IRI-RMS relation by simulation, validated on roads | abstract | SUPPORTED | new |
| R3 | Jeong and Jo validated a deep IRI estimator on 29 vehicles against an inertial profiler | abstract | SUPPORTED | new |

## Data and method

| # | Claim | Evidence | Verdict | Action |
|---|---|---|---|---|
| D1 | Telematics unit fixed to the frame in the middle console close to the front axle | LiRA-CD data article (PMC10375556) | SUPPORTED | new (v2 called it unknown) |
| D2 | P79 surveyed CPH1, M3, M13 in Sept 2020, CPH6 in June 2020; car passes on these routes Nov 2020-Aug 2021, two to fifteen months later | dataset readmes (1.8-14.8 months) | SUPPORTED | **fixed** "fourteen" -> "fifteen" |
| D3 | k = 5 means 475 segment-passes on average (301-640), about 47 km of driving over 4.9 km of road; 9.7 passes per segment | kd* macros from `value_of_simulation.csv` | SUPPORTED | new definition |
| D4 | Joint training is the "simulation + real" design of the first protocol, reported in the first version for one simulation set and omitted in the second | v1 paper (`paper/v1_archive/sections/method.tex` l. 32, results l. 105); `PROTOCOL_V2.md` | SUPPORTED | **fixed**: first v3 draft said it had not been reported |
| D5 | Evidence classes: everything beyond C1 specified in two later protocols frozen before their analyses; reviewers computed some | protocols, review checks | SUPPORTED | - |

## Results

| # | Claim | Evidence | Verdict | Action |
|---|---|---|---|---|
| V1 | M7 ranks as well but has a larger error (+0.074 [+0.039, +0.105]); output calibration made it worse | `summary_real_estimators.csv` after the V3-8 fix | SUPPORTED (R) | numbers updated by the fix |
| V2 | LightGBM MAE is 19 % / 12 % of the class mean IRI | `relative_errors.csv` (class MAE / class mean IRI, protocol definition) | SUPPORTED (E) | new |
| V3 | Real-trained LightGBM ranks urban routes better (+0.042, +0.044) and motorways slightly worse (-0.020, -0.023) than RMS/v^0.5; V0 differs by -0.015..+0.038 | `rank_paired.csv` (all real-trained intervals exclude zero) | SUPPORTED (E) | new |
| V4 | V0 matches the level only on average: urban +0.006, motorway +0.145 (~16 %) | `level_decomposition.csv` | SUPPORTED (R) | new |
| V5 | The vehicle population moves the bias as much as the holder resonance (+0.39 vs -0.35/-0.36 m/km) | `summary_variants.csv` (V4 - V0; factorial effects) | SUPPORTED (E) | new |
| V6 | Bias orders most closely like the 10-15 Hz deficit but also 5-10 Hz and overall RMS; R^2 0.78 vs 0.71; post hoc, variants not independent; V4 departs | `band_associations.csv`; `band_gain.csv` (V4 1.93 vs V0 1.86) | SUPPORTED (E), qualified in the text | **changed** from v2 |
| V7 | Band-limited retraining: spread 0.25 -> 0.08 (32 %; urban 49 %, motorway 34 %); bias spread 0.52 -> 0.14; dropping 10-15 Hz <= 2 %; low-band estimator less accurate with class-dependent error; V4 outside; intervention on inputs, not the car | `band_limited.csv` | SUPPORTED (E; H3, H3b pre-registered and hold) | new |
| V8 | Excess above 10 Hz not an aliasing artefact (52.6 minus 333 Hz: -0.24 in log10, device-confounded); physical source not identified; candidates listed | `spectra_*` (v2); data article | SUPPORTED (E) | sign convention made explicit |
| V9 | Equal profile budget: no general substitute; 20 km difference -0.02..+0.24, largest for V1, V3, V5; offset closes V4's gap | `paired_vs_real.csv` | SUPPORTED (R/E) | shortened |
| V10 | All-profiles paragraph (5 km both combinations; intervals; divergence at 10-20 km; per-route 31/36; variant spread 0.02 vs 0.14/0.17; 1 km 0.44-0.56) | `pooled_summary.csv`, `pooled_by_route.csv`, `calib_uncertainty.csv` | SUPPORTED (R/E) | new |
| V11 | Which combination is better depends on the kind of level error: class difference 0.09-0.30, Spearman 0.88 with the MAE after an offset; joint minus offset -0.096..-0.062 (V1, V3, V5) and +0.002..+0.032 (others) | `level_decomposition.csv`, `pooled_summary.csv` | SUPPORTED (R/E; association over 9 variants) | new |
| V12 | Affine map less accurate than the better of offset and joint training for 9 of 9 variants at 5 and 20 km | `pooled_summary.csv` (poAffWorse*) | SUPPORTED | **fixed**: first draft said "lies in between", contradicted by the data |
| V13 | One pass per segment: offset 0.43-0.55, joint 0.44-0.49, better than real-only in every draw; real-only 0.68 -> 0.93 | `pass_density*.csv` | SUPPORTED (E) | new |
| V14 | Not just a slope: label-free index 0.78 / 0.76 m/km at 5 / 20 km | `nosim_index.csv` | SUPPORTED (E) | new |
| V15 | Speed: robust to unit FE and the speed SD except the real-trained urban elasticity (-0.06 [-0.16, +0.02]); paired urban difference +0.12 [+0.09, +0.16]; CV control turns it negative (-0.07 [-0.21, +0.01]); speed and speed variability not fully separable on urban roads | `speed_robustness.csv` | SUPPORTED (E) | new; unfavourable parts reported |

## Discussion, limitations, conclusion

| # | Claim | Evidence | Verdict | Action |
|---|---|---|---|---|
| X1 | Recipe: simulate over profiled roads, combine with a few km of paired drives, which in our data did not need more than one pass per segment | V13 (tested at 5 km only) | SUPPORTED, scoped "in our data" | - |
| X2 | At 5 km a level offset was the most accurate combination for the six variants whose level error differed least between classes, and fell behind real drives from 10 km for the other three | `pooled_summary.csv` (d_cal >= 0 for those six at 5 km; affine worse); pcCalHiDefWinsTen 3-5 | SUPPORTED (R/E) | made specific to 5 km |
| X3 | Joint training better than real-only on average for every variant and every k, though not on every route and draw; the safer choice when fidelity is unknown | V10, H1 | SUPPORTED; "safer" is a recommendation drawn from nine variants of one car | - |
| X4 | Correction: neither the breadth of the sensor model nor the holder resonance alone explains V0's level | V4, V5 | SUPPORTED | rewritten |
| X5 | 5 km-block intervals 1.9-2.7 times as wide as segment-level; route-level intervals include zero for most comparisons | `inference_blocks.csv` | SUPPORTED (R) | shortened |
| X6 | Limitations: one car, confounded class/route, post hoc analyses, three combination methods with one learner, linear half-car, M7 not a reproduction, surveys 2-15 months earlier | design facts | SUPPORTED | new "Combination methods" item |
| C1 | Conclusion mirrors A2-A9 and recommends joint training unless spectra and class levels agree | as above | SUPPORTED | rewritten |

## Supplement S1, corrected statements of the second version

Each of (i)-(viii) was checked against the v2 text (`checkpoints/v2_2026-10-03/paper/`) and the evidence above:
"only because" (abstract v2), "follows a deficit ... at 10-15 Hz" (abstract v2), "with 10 km or more" (abstract v2),
"ranks ... as well" (abstract v2), mixed metrics (abstract v2), M7 subset (`physics_inversion.py`), "different
profiler" (Table S8 v2), "mounting ... unknown" (Sec. V-C v2) and the survey dates (Table S11 v2). SUPPORTED.

## Phrases the review asked to remove or qualify (L5, L17)

`grep -n "only because\|only through a sensor\|with 10\\,km or more\|ranks segments within routes as well"` over
`paper/`: the only hit is the quotation in Supplement S1 (i). Every remaining "10--15\,Hz" either names the band of a
feature, describes which variants have the largest deficit, or reports the association next to all other bands.
