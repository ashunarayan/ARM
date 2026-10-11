
## A. Verdict: READY AFTER MINOR CORRECTIONS

I found no numerical error, no leakage and no build defect. Every headline number I recalculated with my own code matched. A few sentences misstate the evidence or the protocol, and one promise in the paper ("code … provided") isn't true yet. None of these changes a conclusion, but all should be fixed before you submit.

**What I did:**

- Wrote my own scripts, importing nothing from the project, to recompute metrics from the saved predictions.
- Retrained the key models from the processed feature arrays.
- Rebuilt both PDFs from source and compared them with the shipped ones.
- Checked all 29 DOIs against Crossref.
- Compared the reviewed v2 checkpoint with the current files.

## B. Critical errors, unsupported claims, validity issues

**Critical errors: none found.**

Issues to fix, most important first:

1. **A false general claim in the Discussion.** [discussion.tex:5](research_rescue/paper/sections/discussion.tex#L5) says the untrained RMS/v^0.5 "comes within 0.05 of every trained estimator we tested on every route". That is false:

   - the trained vibration index M2c differs by −0.099 on CPH1;
   - LightGBM without speed inputs differs by −0.176 on M13;
   - the speed-only model differs by −0.72.

   It is true for real-trained LightGBM, the MLP, the CNN, and simulation-trained LightGBM under all nine variants (largest gap 0.038). Your own `rank_paired.py` only tested the real model, V0 and V1. I checked V2–V8, so the abstract and intro wording holds. `CLAIM_AUDIT_V3.md` has no row for this Discussion sentence, which is how it slipped through.
2. **The Method section misdescribes how LightGBM settings were chosen.** [method.tex:14](research_rescue/paper/sections/method.tex#L14) says one of the six configurations is picked by inner leave-one-route-out validation "when real training routes are available". In the code, only the fully real-trained M3 is tuned. The k-km real-only comparator and joint training use configuration 1.

   - I tested whether this matters. Real-only with each of the six configurations scores 0.678–0.722 m/km at 5 km and 0.461–0.465 at 20 km. Inner selection gives 0.683 and 0.461. Configuration 1 is best or tied.
   - So the 20 km joint-training advantage is not an artefact of an under-tuned baseline. Only the sentence is wrong.
3. **"Code, protocols, configurations and all predictions are provided with the paper"** ([intro.tex:28](research_rescue/paper/sections/intro.tex#L28)) is not true yet. `git ls-files research_rescue` returns 0 files, and there is no archive or link.

   - The protocol hash matches its recorded value, and every v3 result is timestamped after the freeze.
   - But "frozen before the analyses" rests only on file timestamps, which no one else can check.
4. **The Table II caption defines "level" differently from what was computed.** The caption says the level is the mean log ratio "over the segments of a road class". The printed values are the mean of the two route levels.

   - The largest difference is 0.017, for V4 motorway: +0.29 printed, +0.31 if pooled over segments. No conclusion changes.
   - The caption is generated, so fix it in `make_tables_v3.py`.
5. **The speed conclusion is stated without its caveat.** Sec. V-E reports two weaknesses: with the speed-CV control the urban paired difference flips to −0.07 [−0.21, +0.01], and with the speed-SD control the real-trained urban elasticity loses its interval. Yet [results.tex:111](research_rescue/paper/sections/results.tex#L111) and [discussion.tex:17](research_rescue/paper/sections/discussion.tex#L17) state the mechanism flatly.

   - The single-estimator elasticity intervals in V-E (e.g. +0.66 [0.60, 0.71], −0.06 [−0.11, −0.01]) use 1 km blocks, while the Method names 5 km blocks. Only the supplement says so; label them in the main text.

## C. Issue table

| Issue                                                 | Evidence inspected                               | Verification performed                                                                                              | Status                                                                          | Required action                  |
| ----------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------- |
| Headline metrics (abstract, Table I)                  | ladder and variant predictions,`units.csv`     | Own recompute plus own 5 km-block bootstrap                                                                         | VERIFIED                                                                        | none                             |
| Route leakage                                         | split code, block sampler, simulation metadata   | Retrained from scratch; no test-route simulated units; only 7 of 1,678 segments lie within 15 m of another route    | VERIFIED, none found                                                            | none                             |
| LightGBM settings choice                              | `models.py`, `models.json`, `exp_lira.py`  | M3 retrained with inner route-out selection: exact match; comparator sensitivity run                                | Code sound, text wrong                                                          | fix method.tex:14                |
| Level offset (calibration)                            | `simreal_variants.py`, zero-shot caches        | Caches equal the stored held-out predictions; 5 and 20 km recomputed for all variants                               | VERIFIED                                                                        | none                             |
| Joint-training arm dropped in v2 (review V3, D1)      | `pooled_vs_real.py`, saved segment predictions | V0 and V5 at 5 km retrained, exact; all variants recomputed                                                         | RESOLVED                                                                        | none                             |
| Test-route intervals (P2.6)                           | `calib_uncertainty.py`                         | Own bootstrap matches all 36 intervals within ±0.002                                                               | RESOLVED                                                                        | none                             |
| V4 / band mechanism (D2)                              | `band_limited.py`, `band_gain.csv`           | 27 retrained models match exactly; V1, V3, V5 confirmed as the largest 10–15 Hz deficits                           | RESOLVED (inputs-level evidence only; physical cause not identified, as stated) | none                             |
| Metric labels, k-km definition (D4)                   | text,`value_of_simulation.csv`                 | 475 segment-passes, 9.7 passes/segment, 4.9 km; within-route vs pooled labels                                       | RESOLVED                                                                        | Table II caption                 |
| Ranking claim (P1.5)                                  | `rank_paired.py`                               | Own per-route ρ for 25 estimators                                                                                  | Resolved in abstract, intro and results; WRONG in Discussion                    | fix discussion.tex:5             |
| Speed robustness (P2.3)                               | `speed_real.py`, `speed_robustness.csv`      | Point elasticities recomputed (−0.153, −0.062, +0.092, urban +0.117); robustness rows only traced                 | PARTIAL                                                                         | add caveat; label 1 km intervals |
| M7 segment-grid bug (P2.4)                            | M7 segment file, checkpoint comparison           | All 1,678 segments, ρ 0.825, MAE 0.494; only the 38 M7 macros changed since v2                                     | RESOLVED                                                                        | none                             |
| Pass density (P3.1)                                   | `pass_density.py`                              | Re-run with an independent random subsample: same conclusion, 20/20 draws                                           | RESOLVED, robust                                                                | none                             |
| Missing literature (D3)                               | bibliography, Crossref                           | 29 DOIs match title, venue, volume and pages (Wu et al. vol. 25 printed in 2024; cited as 2023)                     | Resolved bibliographically; Nitsche 2014 and Ngwangwa 2014 content UNVERIFIED   | read both papers                 |
| Version control and freeze                            | git, protocol hash                               | Hash matches; 0 tracked files                                                                                       | UNRESOLVED                                                                      | commit, tag, archive             |
| Silent protocol changes since review                  | checkpoint manifest                              | Only M7 files changed                                                                                               | VERIFIED, none                                                                  | none                             |
| Final build                                           | sources and PDFs                                 | Clean rebuild gives identical text and byte size; no`??`, undefined references or overfull boxes; pages inspected | VERIFIED                                                                        | none                             |
| Fit to venue                                          | PDF                                              | 10 pp main + 19 pp supplement; abstract ≈266 words                                                                 | UNVERIFIED                                                                      | check the venue's limits         |
| Upstream pipeline (map matching, features, simulator) | —                                               | Not re-run                                                                                                          | UNVERIFIED by this audit                                                        | none                             |

## D. What was independently recalculated

**Recalculated with my own code:**

- **From the saved predictions:**
  - Every Table I row: MAE, bias, ρ, partial ρ.
  - V0 vs real: +0.019 [−0.003, +0.040], exact. The segment-level interval is [+0.008, +0.030], which confirms that segment resampling would have declared the real-trained model better.
  - MLP, CNN, M2c, M1 and M0b intervals, within ±0.002.
  - Residual autocorrelation 0.44 / 0.11; relative errors 19 % / 12 %; class levels; ranking bound.
  - Per-route counts: 31 of 36 variant-route cells, and 3–5 of 20 draws at 10 km.
- **Retrained from the processed features:**
  - M3 with inner selection, zero-shot V0–V8, real-only at 5 and 20 km (per draw, to 2e-16), joint training V0 and V5 at 5 km, and the band-limited spreads (0.25 → 0.08, i.e. 32 %; bias spread 0.52 → 0.14). All exact.
  - Pass density with an independent random subsample: same conclusion.
- **Value-of-simulation numbers, recomputed from predictions or caches (the 5 km real-only model retrained):**
  - 5 km: level offset 0.420–0.562 and joint training 0.449–0.473 m/km, against real-only 0.678.
  - 20 km: joint minus real-only −0.030 to −0.014 (16–20 of 20 draws); level offset for V1, V3 and V5 better in 0 of 20 draws.
- **Data facts:** 1,678 segments, 16,293 segment-passes, 91 passes, 8 identified telematics units, 40 blocks of 5 km, and the label check r = 1.000 over 1,520 segments.

**Traced to result files but not recalculated:**

- the spectra and power ratios in Fig. 3a, and the band correlations 0.97 / 0.88 / 0.80;
- the simulated speed scaling (0.92–1.40) and the speed-robustness rows;
- the equal-budget arms for V1–V8;
- the no-simulator index (0.78 / 0.76);
- the vehicle sweep (+70 % / +16 %);
- the ARAN comparison;
- the unit-disjoint check (numbers read from file, not re-run);
- MLP and CNN (not retrained);
- the M7 inversion (not re-run);
- the whole upstream pipeline from raw LiRA-CD files.

## E. Five things to know before submitting

1. **The experiments are real and the numbers are right.** Every headline number traces to artifacts, and every one I recalculated or retrained matches, mostly to machine precision. The paper's evidence for its central story holds: ranking within a route is easy, the level is what fails, and simulation plus 5 km of paired drives beats those 5 km alone for all nine variants.
2. **Fix five sentences and one caption:** discussion.tex:5, method.tex:14, the Table II caption, results.tex:111, discussion.tex:17, plus the "(1 km blocks)" labels in V-E. Each is a short wording edit. Regenerate the tables and macros through the generators, not by hand.
3. **Make the release claim true.** Publish an archive or repository with a DOI before submission, or reword intro.tex:28. Commit and tag `research_rescue/` so that "frozen before" can be checked by someone else.
4. **Check the venue's limits.** At 10 pages plus a 19-page supplement and a ~266-word abstract, this exceeds typical IEEE conference limits (often 6–8 pages and ≤250 words).
5. **Know where reviewers can still push.**
   - Only the V0 comparison is confirmatory: one car model, four routes.
   - The 20 km joint-training advantage is small (0.014–0.030 m/km) and reverses on M3 for 4 variants.
   - Your "closest in design" positioning rests on Nitsche 2014 and Ngwangwa 2014, which nobody has read beyond secondary descriptions. Read them.

The audit scripts are in my session scratchpad. I can copy them to `research_rescue/review/final_audit/` so the checks stay re-runnable, or publish this report as a page you can share.

## A. Verdict: READY AFTER MINOR CORRECTIONS

I found no numerical error, no leakage and no build defect. Every headline number I recalculated with my own code matched. A few sentences misstate the evidence or the protocol, and one promise in the paper ("code … provided") isn't true yet. None of these changes a conclusion, but all should be fixed before you submit.

**What I did:**

- Wrote my own scripts, importing nothing from the project, to recompute metrics from the saved predictions.
- Retrained the key models from the processed feature arrays.
- Rebuilt both PDFs from source and compared them with the shipped ones.
- Checked all 29 DOIs against Crossref.
- Compared the reviewed v2 checkpoint with the current files.

## B. Critical errors, unsupported claims, validity issues

**Critical errors: none found.**

Issues to fix, most important first:

1. **A false general claim in the Discussion.** [discussion.tex:5](research_rescue/paper/sections/discussion.tex#L5) says the untrained RMS/v^0.5 "comes within 0.05 of every trained estimator we tested on every route". That is false:

   - the trained vibration index M2c differs by −0.099 on CPH1;
   - LightGBM without speed inputs differs by −0.176 on M13;
   - the speed-only model differs by −0.72.

   It is true for real-trained LightGBM, the MLP, the CNN, and simulation-trained LightGBM under all nine variants (largest gap 0.038). Your own `rank_paired.py` only tested the real model, V0 and V1. I checked V2–V8, so the abstract and intro wording holds. `CLAIM_AUDIT_V3.md` has no row for this Discussion sentence, which is how it slipped through.
2. **The Method section misdescribes how LightGBM settings were chosen.** [method.tex:14](research_rescue/paper/sections/method.tex#L14) says one of the six configurations is picked by inner leave-one-route-out validation "when real training routes are available". In the code, only the fully real-trained M3 is tuned. The k-km real-only comparator and joint training use configuration 1.

   - I tested whether this matters. Real-only with each of the six configurations scores 0.678–0.722 m/km at 5 km and 0.461–0.465 at 20 km. Inner selection gives 0.683 and 0.461. Configuration 1 is best or tied.
   - So the 20 km joint-training advantage is not an artefact of an under-tuned baseline. Only the sentence is wrong.
3. **"Code, protocols, configurations and all predictions are provided with the paper"** ([intro.tex:28](research_rescue/paper/sections/intro.tex#L28)) is not true yet. `git ls-files research_rescue` returns 0 files, and there is no archive or link.

   - The protocol hash matches its recorded value, and every v3 result is timestamped after the freeze.
   - But "frozen before the analyses" rests only on file timestamps, which no one else can check.
4. **The Table II caption defines "level" differently from what was computed.** The caption says the level is the mean log ratio "over the segments of a road class". The printed values are the mean of the two route levels.

   - The largest difference is 0.017, for V4 motorway: +0.29 printed, +0.31 if pooled over segments. No conclusion changes.
   - The caption is generated, so fix it in `make_tables_v3.py`.
5. **The speed conclusion is stated without its caveat.** Sec. V-E reports two weaknesses: with the speed-CV control the urban paired difference flips to −0.07 [−0.21, +0.01], and with the speed-SD control the real-trained urban elasticity loses its interval. Yet [results.tex:111](research_rescue/paper/sections/results.tex#L111) and [discussion.tex:17](research_rescue/paper/sections/discussion.tex#L17) state the mechanism flatly.

   - The single-estimator elasticity intervals in V-E (e.g. +0.66 [0.60, 0.71], −0.06 [−0.11, −0.01]) use 1 km blocks, while the Method names 5 km blocks. Only the supplement says so; label them in the main text.

## C. Issue table

| Issue                                                 | Evidence inspected                               | Verification performed                                                                                              | Status                                                                          | Required action                  |
| ----------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------- |
| Headline metrics (abstract, Table I)                  | ladder and variant predictions,`units.csv`     | Own recompute plus own 5 km-block bootstrap                                                                         | VERIFIED                                                                        | none                             |
| Route leakage                                         | split code, block sampler, simulation metadata   | Retrained from scratch; no test-route simulated units; only 7 of 1,678 segments lie within 15 m of another route    | VERIFIED, none found                                                            | none                             |
| LightGBM settings choice                              | `models.py`, `models.json`, `exp_lira.py`  | M3 retrained with inner route-out selection: exact match; comparator sensitivity run                                | Code sound, text wrong                                                          | fix method.tex:14                |
| Level offset (calibration)                            | `simreal_variants.py`, zero-shot caches        | Caches equal the stored held-out predictions; 5 and 20 km recomputed for all variants                               | VERIFIED                                                                        | none                             |
| Joint-training arm dropped in v2 (review V3, D1)      | `pooled_vs_real.py`, saved segment predictions | V0 and V5 at 5 km retrained, exact; all variants recomputed                                                         | RESOLVED                                                                        | none                             |
| Test-route intervals (P2.6)                           | `calib_uncertainty.py`                         | Own bootstrap matches all 36 intervals within ±0.002                                                               | RESOLVED                                                                        | none                             |
| V4 / band mechanism (D2)                              | `band_limited.py`, `band_gain.csv`           | 27 retrained models match exactly; V1, V3, V5 confirmed as the largest 10–15 Hz deficits                           | RESOLVED (inputs-level evidence only; physical cause not identified, as stated) | none                             |
| Metric labels, k-km definition (D4)                   | text,`value_of_simulation.csv`                 | 475 segment-passes, 9.7 passes/segment, 4.9 km; within-route vs pooled labels                                       | RESOLVED                                                                        | Table II caption                 |
| Ranking claim (P1.5)                                  | `rank_paired.py`                               | Own per-route ρ for 25 estimators                                                                                  | Resolved in abstract, intro and results; WRONG in Discussion                    | fix discussion.tex:5             |
| Speed robustness (P2.3)                               | `speed_real.py`, `speed_robustness.csv`      | Point elasticities recomputed (−0.153, −0.062, +0.092, urban +0.117); robustness rows only traced                 | PARTIAL                                                                         | add caveat; label 1 km intervals |
| M7 segment-grid bug (P2.4)                            | M7 segment file, checkpoint comparison           | All 1,678 segments, ρ 0.825, MAE 0.494; only the 38 M7 macros changed since v2                                     | RESOLVED                                                                        | none                             |
| Pass density (P3.1)                                   | `pass_density.py`                              | Re-run with an independent random subsample: same conclusion, 20/20 draws                                           | RESOLVED, robust                                                                | none                             |
| Missing literature (D3)                               | bibliography, Crossref                           | 29 DOIs match title, venue, volume and pages (Wu et al. vol. 25 printed in 2024; cited as 2023)                     | Resolved bibliographically; Nitsche 2014 and Ngwangwa 2014 content UNVERIFIED   | read both papers                 |
| Version control and freeze                            | git, protocol hash                               | Hash matches; 0 tracked files                                                                                       | UNRESOLVED                                                                      | commit, tag, archive             |
| Silent protocol changes since review                  | checkpoint manifest                              | Only M7 files changed                                                                                               | VERIFIED, none                                                                  | none                             |
| Final build                                           | sources and PDFs                                 | Clean rebuild gives identical text and byte size; no`??`, undefined references or overfull boxes; pages inspected | VERIFIED                                                                        | none                             |
| Fit to venue                                          | PDF                                              | 10 pp main + 19 pp supplement; abstract ≈266 words                                                                 | UNVERIFIED                                                                      | check the venue's limits         |
| Upstream pipeline (map matching, features, simulator) | —                                               | Not re-run                                                                                                          | UNVERIFIED by this audit                                                        | none                             |

## D. What was independently recalculated

**Recalculated with my own code:**

- **From the saved predictions:**
  - Every Table I row: MAE, bias, ρ, partial ρ.
  - V0 vs real: +0.019 [−0.003, +0.040], exact. The segment-level interval is [+0.008, +0.030], which confirms that segment resampling would have declared the real-trained model better.
  - MLP, CNN, M2c, M1 and M0b intervals, within ±0.002.
  - Residual autocorrelation 0.44 / 0.11; relative errors 19 % / 12 %; class levels; ranking bound.
  - Per-route counts: 31 of 36 variant-route cells, and 3–5 of 20 draws at 10 km.
- **Retrained from the processed features:**
  - M3 with inner selection, zero-shot V0–V8, real-only at 5 and 20 km (per draw, to 2e-16), joint training V0 and V5 at 5 km, and the band-limited spreads (0.25 → 0.08, i.e. 32 %; bias spread 0.52 → 0.14). All exact.
  - Pass density with an independent random subsample: same conclusion.
- **Value-of-simulation numbers, recomputed from predictions or caches (the 5 km real-only model retrained):**
  - 5 km: level offset 0.420–0.562 and joint training 0.449–0.473 m/km, against real-only 0.678.
  - 20 km: joint minus real-only −0.030 to −0.014 (16–20 of 20 draws); level offset for V1, V3 and V5 better in 0 of 20 draws.
- **Data facts:** 1,678 segments, 16,293 segment-passes, 91 passes, 8 identified telematics units, 40 blocks of 5 km, and the label check r = 1.000 over 1,520 segments.

**Traced to result files but not recalculated:**

- the spectra and power ratios in Fig. 3a, and the band correlations 0.97 / 0.88 / 0.80;
- the simulated speed scaling (0.92–1.40) and the speed-robustness rows;
- the equal-budget arms for V1–V8;
- the no-simulator index (0.78 / 0.76);
- the vehicle sweep (+70 % / +16 %);
- the ARAN comparison;
- the unit-disjoint check (numbers read from file, not re-run);
- MLP and CNN (not retrained);
- the M7 inversion (not re-run);
- the whole upstream pipeline from raw LiRA-CD files.

## E. Five things to know before submitting

1. **The experiments are real and the numbers are right.** Every headline number traces to artifacts, and every one I recalculated or retrained matches, mostly to machine precision. The paper's evidence for its central story holds: ranking within a route is easy, the level is what fails, and simulation plus 5 km of paired drives beats those 5 km alone for all nine variants.
2. **Fix five sentences and one caption:** discussion.tex:5, method.tex:14, the Table II caption, results.tex:111, discussion.tex:17, plus the "(1 km blocks)" labels in V-E. Each is a short wording edit. Regenerate the tables and macros through the generators, not by hand.
3. **Make the release claim true.** Publish an archive or repository with a DOI before submission, or reword intro.tex:28. Commit and tag `research_rescue/` so that "frozen before" can be checked by someone else.
4. **Check the venue's limits.** At 10 pages plus a 19-page supplement and a ~266-word abstract, this exceeds typical IEEE conference limits (often 6–8 pages and ≤250 words).
5. **Know where reviewers can still push.**
   - Only the V0 comparison is confirmatory: one car model, four routes.
   - The 20 km joint-training advantage is small (0.014–0.030 m/km) and reverses on M3 for 4 variants.
   - Your "closest in design" positioning rests on Nitsche 2014 and Ngwangwa 2014, which nobody has read beyond secondary descriptions. Read them.
