# Reviewer audit of the revised paper (final adversarial self-review, revision v2, 2026-10-03)

Written as a new reviewer reading `paper/main.pdf` and `paper/supplementary.pdf` cold, then checking each answer
against the result files. Problems found during this review were fixed before it was finalised; they are listed
under "Fixed during this review" in each answer. Numbers are those printed in the paper (macros from `results/v2/`).

## 1. What is the paper's ONE contribution?

Real-car, route-disjoint evidence about **what a simulator built on measured road profiles transfers to a production
car's IRI estimator, and how much paired data it still needs**: across nine sensor and vehicle models the simulated
vibration-to-IRI mapping is usable up to a level offset for six of them, but its level is not reliable (zero-shot bias
-0.09 to +0.43 m/km) and follows a 10-15 Hz deficit of simulated vibration; with a level offset from 5 km of paired
drives, simulation over all profiled roads beats training on those 5 km for every variant (13-20 of 20 paired draws,
on every held-out route), while with >= 10 km real drives alone beat the three worst-matched variants.

Everything else (benchmark, baselines, speed analysis, earlier-pipeline post-mortem) supports or bounds this.

*Fixed during this review:* the first v2 draft headlined "the ranking transfers". A check added during this review
(E10, `ranking_untrained.py`) showed that an **untrained** RMS/v^0.5 ranks segments within routes as well as every
trained estimator (Spearman 0.82, partial 0.81, vs 0.83 / 0.81). Ranking is therefore not evidence of transfer; the
abstract, introduction, Sec. V-B, Fig. 2a, Discussion and Conclusion were rewritten around the level/mapping instead.

## 2. What evidence establishes it?

* V0 vs real-trained (class C1, the only confirmatory comparison): within-route MAE 0.42 vs 0.39; pooled difference
  +0.019 [-0.003, +0.040] m/km (5 km blocks) - Table I.
* Nine measured-profile variants (class E): bias -0.09..+0.43, MAE 0.41..0.69, within-route rho 0.82..0.84 - Table II,
  Fig. 2; 2x2 sensor factorial (holder resonance -0.35/-0.36 m/km on the bias).
* Spectra on the same segments and speed bands (E3/E4): bias orders like the 10-15 Hz amplitude deficit (Spearman 0.97,
  9 variants), deficit larger on motorways for 9/9 variants - Fig. 3, Tables S15-S16.
* Calibration and equal budget on 20 matched draws (R3/R4, E5, E6, E9): Table III, Fig. 4, Table S14,
  `paired_vs_real*.csv`.

Weakness a reviewer will name: apart from V0, all of this is post hoc on routes whose results were known. The paper
says so in the Evidence-classes paragraph and the Limitations.

## 3. Could speed explain the result?

* Not the level differences between variants: all variants are evaluated on the same real passes with the same speed
  features; only the simulated training data differ.
* Not the ranking result (now a secondary point): partial Spearman given segment speed is 0.80-0.82 for every
  variant, 0.81 real, 0.81 for the untrained statistic; speed alone ranks at 0.39.
* Speed is a *second simulator mismatch* (E7): simulated vibration RMS rises with speed with elasticity 0.92-1.40 vs
  0.60 (urban) / 0.85 (motorway) for the real car. It is similar for all variants, so it cannot explain their
  different levels, but it contributes to the overall zero-shot error and it removes any basis for claiming that the
  simulator models the car's speed response. The paper's speed claims were weakened accordingly (Sec. V-E: simulation
  removes part of the urban over-correction of real-trained models, paired +0.09 [+0.06, +0.12]; none on motorways).

## 4. Could sensor mismatch explain the result?

Sensor mismatch *is* the explanation the paper offers for the level, with the evidence in Q2. What sensor mismatch
cannot explain away is the calibration result: it holds for every variant, including those with the largest mismatch
(V1, V3, V5 at 5 km: 0.53-0.56 vs 0.68 m/km real-only). The cause of the 10-15 Hz excess of the real car (mounting,
unsprung dynamics, tyre enveloping, roll, averaging the two wheel paths) is not identified, and the paper says so. The
aliasing explanation was checked and is not supported (333 Hz passes have more 10-15 Hz power, device-confounded).

## 5. Could vehicle identity explain the result?

* Real-trained models share telematics units with the test routes (route-disjoint, not vehicle-disjoint). Unit-disjoint
  retraining gives the same MAE as size-matched random subsets on the three interpretable folds (Table S7); the unit
  variance component is 7 % of log error (Table S6). Vehicle overlap does not measurably favour the real-trained model.
* Simulation never sees the real car, so its results cannot be explained by vehicle identity.
* Generalisation to *other* vehicles is not testable with one car model; the controlled sweep (class S) shows an
  unseen-vehicle penalty of +16 % at 30 simulated vehicles and <= 10 % only from 100 vehicles under the segment (not the
  route) bootstrap. Reported as simulation-only.

## 6. Could route selection explain the result?

Four routes, two per road class; class and route are confounded. Mitigations in the paper: per-route results
(Table S4), within-route metrics as primary, the calibration advantage checked per held-out route (it holds on all four
routes for all nine variants at 5 km: mean differences -0.37 to -0.04 m/km), route-level intervals (Table S5). No
claim about other routes is made. A reviewer can still argue that motorway vs urban behaviour (e.g. the class-dependent
bias) is a two-route observation - correct, and stated.

## 7. Is the comparison fair?

* Real-trained LightGBM gets inner-CV configuration selection; simulation-trained LightGBM uses the first fixed
  configuration - this favours the real model, i.e. works against the paper's conclusion.
* Real-only training on k km: LightGBM may be a poor small-sample learner, so a three-parameter vibration index was
  added as a second real-only comparator (E9). Against it, simulation over the same 1 km of profiles is *not* better
  (3-10 of 20 draws), and the paper reports this; simulation + level beats both comparators at <= 5 km.
* The "simulation + level" arm uses all profiled training roads while real-only uses k km: an equal *paired-drive*
  budget, not an equal *profile* budget. The equal-profile-budget comparison is reported separately (Fig. 4a) and is
  variant-dependent. Both framings are stated.
* No test-route data enter training, calibration or model selection (verified in code: calibration draws come from
  training routes only, `sample_blocks(U, tr, ...)`).

## 8. Is the sample size sufficient?

For internal comparisons on these routes: 1,678 segments, 40 independent-ish 5 km blocks, 20 draws per k - adequate to
resolve differences of ~0.05 m/km at the 5 km-block level, not ~0.02 (V0 vs real is unresolved). For generalisation:
no - one car model, four routes, nine non-independent simulator variants for the spectral association, 30 vehicles in
the controlled sweep. The paper does not claim generalisation.

## 9. Is the statistical inference valid?

Improved but not perfect, and the paper now says where it is not:
* Paired differences use a 5 km-block cluster bootstrap (40 clusters); segment-level intervals were 1.9-2.7x too narrow.
* Residual correlation remains at 5 km (0.13 for LightGBM), mostly from route-level offsets; route-level t intervals
  (3 df) include zero for most comparisons. *Fixed during this review:* the Discussion now states that the
  "supported" differences describe these four routes, not a population of routes; and the MLP wording was corrected
  ("worse on all four routes" although negligible: its route-level interval [0.000, 0.008] excludes zero).
* Calibration ranges are over draws of the calibration blocks; they do not include test-set uncertainty (stated in
  Sec. V-D). Intervals are conditional on the trained models (stated in Sec. IV).
* *Fixed during this review:* constant predictors (M0, M0b) had spurious within-route correlations from floating-point
  noise (0.06 / -0.01); they are now reported as undefined.
* No multiple-comparison correction is applied to the many variant contrasts; they are presented as descriptive (E).

## 10. Is the simulation mechanism demonstrated?

No, and the paper does not claim it. The 2x2 factorial shows *which simulated component* sets V0's level (the holder
resonance), the spectral comparison locates the mismatch in frequency, and the empirical transmissibility of the real
car peaks at 12.5 Hz, but the physical cause is not identified and the variants are not independent experiments.

## 11. Is the value-of-simulation claim fair?

After this revision, yes, with its scope stated: (a) the equal-profile-budget result is variant- and
comparator-dependent and is reported as such; (b) the strong claim is about simulation + level offset vs real-only
training at equal paired-drive budget, which holds for every variant at <= 5 km against both real-only comparators and
on every route, and fails for three variants at >= 10 km. The first v1 claim ("about 20 km") is withdrawn. Remaining
weakness: all of this is one car; the amount of savings will differ for other cars.

## 12. Are the baselines strong?

Reasonably: no-vibration baselines (constant, map-only road class, speed only), physics-based (fitted vibration index,
calibrated quarter-car spectral inversion M7 "in the spirit of" Skar & Levenberg, which ranks as well as the learned
models), learned (LightGBM, MLP, 1D-CNN), simulation-trained variants, an untrained ranking statistic, and two
real-only small-sample comparators. Not included: an exact reproduction of Skar & Levenberg (vehicle parameters not
available; their open code contains only the Golden Car), Kalman-filter inversion (Agebjar et al.), and tuned deep
models. A reviewer could ask for a time-domain inversion baseline; we cannot reproduce it faithfully.

## 13. Is the literature positioning accurate?

Rewritten and checked against abstracts/code (`references/REFERENCE_AUDIT.md`, Section D). *Fixed during this review:*
Xing et al. 2025 had been grouped with simulation-only validation although it includes a real-vehicle test (roughness
classes); Skar & Levenberg is now described from its abstract (quarter-car model, PID controller, nonlinear error
minimisation, ten electric cars, laser profilometer) and the "parameters not published" statement was narrowed to
"not available to us; the open code contains only Golden-Car parameters". Three citations remain title-level and should
be read by a human before submission (mounting2026, hanson2014iri, ngwangwa2010ann).

## 14. Is the central claim broader than the evidence?

The abstract and conclusion are scoped to one car and state the dependence on the simulated vibration path. The
remaining stretch is the practical recommendation (simulate over profiled roads, calibrate with a few km, check
spectra): it is phrased as "suggests" and the spectral check is flagged as post hoc and needing confirmation. The
phrase "for six of nine variants the mapping is usable up to a level offset" rests on 5 km-calibrated MAE 0.42-0.45
vs 0.42 for real training on all routes - fair on these routes.

## 15. What is the easiest reason for a reviewer to reject this paper?

**External validity and evidence class.** One car model on four routes, and every result beyond the V0 comparison was
obtained after the test routes had been used (and after an earlier review pointed at the sensor model). A reviewer can
say the paper is a careful post-mortem plus diagnostics, not a confirmed method. The second easiest: the mechanism
behind the level error is not identified. Neither can be fixed without new paired data (another car/sensor/city),
ideally collected after freezing the simulator and the calibration protocol - listed in `FINAL_REPORT_V2.md`, section I.

## Problems found and fixed during this final review (summary)

| Problem | Fix |
|---|---|
| "Ranking transfers" headline uninformative (untrained statistic ranks as well) | E10 analysis; story rewritten around level/mapping; Fig. 2a reference line |
| Constant baselines showed spurious within-route rho | correlation undefined when predictions are constant (`summarise_v2.py`) |
| Per-route segment counts in a supplement caption were typed by hand and wrong | generated from data (`make_tables_v2.py`) |
| Real-only comparator possibly weak at 1-2 km | E9 vibration-index comparator on the same draws |
| Calibration advantage might come from one route | per-route paired comparison (`paired_vs_real_by_route.csv`) |
| Inference: residual 5 km correlation, route-level intervals | stated in the Discussion |
| MLP "indistinguishable" | "negligible, but worse on all four routes" |
| Xing et al. and Skar & Levenberg descriptions | corrected against abstracts and code |
| "Pre-registered" still in a v1 table generator | fixed |
| "Gap closes mainly because..." and "unrelated to distance" (vehicle sweep) | reworded to match the numbers |
