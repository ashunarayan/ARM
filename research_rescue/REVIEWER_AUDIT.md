# Adversarial reviewer audit of the rewritten paper

Paper: `paper/main.pdf` (10 pages) and `paper/supplementary.pdf` (6 pages),
"How Far Can Simulation Take Vehicle-Based IRI Estimation? A Route-Disjoint Study on Profilometer-Referenced Car Data".

Method: every sentence of the paper that states a result, a property of the data or a property of the method was
traced to the file that produces it (result CSV/JSON, script, config) and read as a hostile reviewer would. Two
rounds of fixes were applied; a third pass found only issues that need new data or a human decision. All numbers
in the paper are LaTeX macros from `make_numbers.py` (1699 macros, 0 missing); a scan of the source for literal
numbers found only design parameters (window lengths, thresholds, perturbation levels), a derived constant
(the Golden Car's wheel-hop wavelength, about 2 m) and two figures quoted from the earlier manuscript (1.650, 0.521).

## 1. Claims of the abstract and conclusion, and their evidence

| Claim | Evidence | Status |
|---|---|---|
| Our IRI code reproduces the P79's IRI ($r$ = 1.000, bias +0.018 m/km, 1,520 segments) | `results/iri_validation.json`; Fig. 2a | holds; labelled in the text as an *algorithm* check (same laser profiles) |
| The mesh correction lowers urban IRI by 28 % | `iri_validation.json` (legacy pipeline vs P79, urban: bias -1.10, MAE 1.10, so virtually every segment is lowered) | holds |
| Calibration on the test track and filtering hid diverging predictions | `results/beamng/S1_legacy_recipe_metrics.csv` (uncalibrated MAE 251), `S3_legacy_discard_rule_effect.csv` (up to 1,555 -> 1.94) | holds |
| LightGBM 0.42 m/km [0.39, 0.45], $\rho$ 0.95, on unseen routes | `results/lira/ladder_segment_metrics.csv` | holds (segment-level CI; see open issue O1) |
| MLP indistinguishable, CNN worse (+0.06, p < 0.001), speed-only 0.74 | same file, paired bootstrap with Holm | holds |
| Speed is confounded with road class | urban 43 km/h vs motorway 87 km/h; speed-IRI Spearman -0.50/-0.39 within urban routes; speed-only MAE 0.74 | holds |
| On PVS, speed predicts the quality labels better than vibration | `results/pvs/pvs_auc.csv` (bad vs regular: speed 0.75, RMS 0.23, earlier model 0.41) | holds |
| Simulation-only LightGBM reaches 0.44 m/km (+0.02 vs real, p = 0.001) | `results/lira/zeroshot_segment_metrics.csv`, `compare_zeroshot_vs_real.csv` | holds; wording says "without having been trained on any real vehicle data" and discloses that the sensor configuration was informed by unlabelled LiRA-CD streams; robust to correcting the sensor rates (0.46, post-hoc) but not to removing the sensor mixture (0.69, post-hoc), which the paper states |
| Real-only training needs about 20 km to match it | `results/lira/fewshot_raw.csv` (20 km: 0.46 vs sim-only 0.46; 10 km: 0.50) | holds as a point-estimate reading of the curve; draw ranges shown in Fig. 5 |
| BeamNG training does not transfer (1.36 m/km) | `zeroshot_segment_metrics.csv` | holds |
| Learned speed corrections hold only for the road spectra seen in training | `results/sim/speed_invariance.csv`, `speed_invariance_p79trained.csv` | holds in simulation only (stated as such) |
| No accurate estimator meets the unseen-vehicle criterion | `results/sim/unseen_vehicle_paired.csv`, `results/beamng/seen_vs_unseen_vehicle.csv` | holds in both simulators; only less accurate estimators pass |

## 2. Round 1: problems found in the first complete draft, and fixes

| # | Problem (as a reviewer would state it) | Fix |
|---|---|---|
| 1 | "Speed-only is better than every physics index except the fitted one": false, the alpha = 2 index is 0.73 vs 0.74 | reworded to "close to M2c and M2d" |
| 2 | Discard-rule numbers attributed to leave-one-map-out; they come from the uncalibrated predictions on the earlier split | text and Table IV state the split |
| 3 | "Averaging passes helps on urban roads": it helps on both classes | numbers for both classes (0.75 -> 0.62 urban, 0.20 -> 0.15 motorway) |
| 4 | "Without a single real label": labels of simulated units are IRI of *real* profiles | reworded: no real *vehicle* data; profiles of training routes are real |
| 5 | LiRA-CD sensor description (56-260 Hz, tilt up to 11 deg) did not match the data | new `evaluation/lira_sensor_stats.py`: nominal 52.6 Hz (66 %) or 333 Hz, 0.01 g in 81 % of passes, tilt median 10 deg, max 41 deg; discrepancy with the simulator's configuration disclosed (Sections IV, IX, S1); simulator not changed after results |
| 6 | Runge-Kutta agreement of the simulator asserted without a saved test | RK4 test added to `evaluation/sim_unit_test.py` (4.4e-9 after fixing a test-only initial-condition mismatch) |
| 7 | CPH6-HH exclusion rested on an unsaved diagnostic | new `evaluation/cph6hh_alignment.py` (best r = 0.13 over +/-3 km shifts and reversal; controls 1.000) |
| 8 | Method said neural-net predictions are seed-averaged; LiRA-CD/BeamNG metrics are means of per-seed metrics | method and S1 now state both conventions |
| 9 | Zero-/few-shot LightGBM used the first grid configuration without disclosure | disclosed in Section V |
| 10 | Half-car driven by the mean of both wheel-path profiles (no roll) was not disclosed | disclosed (Sections IV, IX) |
| 11 | Robustness baseline described as a "sensor mix"; it is the telematics configuration on held-out synthetic routes | caption and Fig. S1 corrected |
| 12 | Discussion claimed the vibration index is "competitive with the CNN" (0.67 vs 0.48) | removed |
| 13 | Discussion claimed the vehicle transfer function dominates; the ablations show the profile source matters most (0.71 vs 0.67 vs 0.63) | rewritten from the ablation numbers |
| 14 | Limitations claimed the sampling-rate effect is smaller than the transfer gap; it is larger (0.87 vs 0.77 in simulation vs a 0.02 gap) | rewritten: the mismatch could change the zero-shot results in either direction |
| 15 | Discussion attributed the motorway over-prediction to the simulator's speed exponent; level, IRI and speed dependence all differ | states the bias (+0.19, +0.12 m/km) and that the cause is not isolated |
| 16 | "Pre-registered" although the protocol was not registered with a third party | "fixed in advance"; RQ section says it was not registered externally (protocol file 18:24, first test result 18:43 on 2026-10-02) |
| 17 | IRI-validation figure silently clipped 42 ARAN points above 15 m/km | panel reports the off-scale count |
| 18 | Robustness legend and labels showed raw text (`^alpha`, `ug/rtHz`); LiRA legend said "no real labels" | regenerated |
| 19 | Text-mode `<` printed as an inverted exclamation mark in OT1 encoding; minus signs as hyphens | macros emit math-mode signs; T1 encoding |

## 3. Round 2: problems found after round 1, and fixes

| # | Problem | Fix |
|---|---|---|
| 20 | Are the four routes really disjoint (shared streets would leak)? | new `evaluation/route_overlap.py`: 7 of 1,678 segments within 15 m of another route (CPH1/CPH6 crossings); stated in Section VI |
| 21 | Segment-level CIs do not cover between-route variation | stated in Section VI; per-route results shown (Fig. 3b, Table S2) |
| 22 | "Physics index" may read as a physics-informed claim | renamed "vibration index" throughout the paper |
| 23 | "The 5 m smoothing removes the wavelengths to which the quarter car is most sensitive": imprecise | "attenuates wavelengths shorter than about 5 m, which include the Golden Car's wheel-hop sensitivity peak near 2 m" (k1 = 653, k2 = 63.3, mu = 0.15 -> 11 Hz at 22.2 m/s) |
| 24 | BeamNG raw-profile labels presented as the "valid" alternative | text states that neither BeamNG label is a valid IRI |
| 25 | "Two-parameter" vibration index has three parameters (a, b, alpha) | corrected |
| 26 | Partial Spearman analysis not described | Section VI describes it (rank residuals, within route) |
| 27 | Number of telematics units and road-class speeds not reported | added (at least 8 units; 43 vs 87 km/h) |
| 28 | Real-only baselines at small budgets: could a simpler model beat simulation? | the real-only vibration index does not match the simulation-only model even with all routes (0.67) |
| 29 | Seed variation promised but not reported | seed s.d. of MAE: MLP 0.005, CNN 0.030 m/km |
| 30 | Citation problems: TP 45 cited for passenger-car ranges; Thilak et al. compared with ROMDAS, not a profiler; mounting claim lacked its source | fixed; claim check of all 37 citations in `references/REFERENCE_AUDIT.md`, Section C |
| 31 | CNN may simply be under-tuned | limitation added (earlier architecture, hyper-parameters fixed in advance) |
| 32 | Skipped-pass description ("GPS only") was inaccurate for 2 of 11 passes | 9 GPS-only, 2 without speed, 2 without valid units; all from result files |

## 4. Round 3: remaining issues (cannot be fixed without new data or a human decision)

| # | Issue a reviewer will raise | Severity | What would resolve it |
|---|---|---|---|
| O1 | One car model, one telematics unit type, four routes in one region; urban and motorway differ systematically, so "unseen route" is close to "unseen road class within one city" | high | car data with reference profiles from another city or vehicle; none public that we know of besides LiRA-CD |
| O2 | Unseen-vehicle generalisation and smartphone mounting tested only in simulation | high | field drives with two or more vehicles/phones over profiled roads |
| O3 | Simulator's telematics configuration differs from the measured LiRA-CD rates (55-62 Hz vs 52.6/333 Hz) | resolved post-hoc | re-run done (`exp_lira.py zeroshot_sensor`): matched telematics half + smartphone-like half 0.46 vs 0.44 m/km (paired +0.016 [+0.008, +0.024]); a single matched telematics sensor 0.69. Reported in Results VII-E, Table IV (marked post-hoc), Limitations and S1. Residual concern: the transfer depends on the breadth of the sensor model, which a reviewer may call a design choice; it was fixed before any real-data result |
| O4 | The earlier study is unpublished; contributions (i)-(ii) are a case study of one pipeline | medium | framing choice; the generic lessons are stated in the discussion |
| O5 | Bajic et al. (2021) also predict roughness from LiRA car data; no numerical comparison | medium | read the full paper and compare protocols (their split is not stated in the abstract) |
| O6 | Three citations checked at title level only (mounting2026, hanson2014iri, ngwangwa2010ann) | low | read the papers |
| O7 | Pre-registration is self-declared (timestamps on uncommitted files) | low | commit `research_rescue/` and cite the commit, or deposit the protocol (e.g. OSF) for future work |
| O8 | 10 pages exceed typical IEEE conference limits | depends on venue | journal submission, or move Tables IV-V and Fig. 6 to the supplement |
| O9 | Few-shot "about 20 km" is a point-estimate reading with 5 draws | low | more draws |

## 5. Verdict of the audit

After two rounds the paper makes no claim that its result files contradict, discloses every protocol deviation
found, and states its scope (one car type, simulation-only vehicle tests). The remaining weaknesses (O1, O2) are
limits of the available data, not of the analysis. A reviewer at a transportation/measurement journal would most
likely ask for O3 and O5 and accept the scope with the limitations as written; a reviewer expecting a new
state-of-the-art estimator would find the contribution modest, because the best real-car model is gradient boosting
on hand-crafted features and the main result is a careful negative/positive mixture rather than a new method.
