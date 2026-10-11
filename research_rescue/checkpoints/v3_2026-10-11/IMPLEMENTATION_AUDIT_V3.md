# Implementation audit, revision v3 (response to `INDEPENDENT_REVIEW_V3.md`)

Ledger of every recommendation in the review: whether it was independently verified, the decision, its status and
the resulting change to the paper. Classes: **A** verified and necessary; **B** verified and valuable; **C** plausible
but unverified (investigated before deciding); **D** redundant or low value; **E** incorrect or unsound.
Protocol: `evaluation/PROTOCOL_V3.md` (frozen 2026-10-10 22:01 IST, SHA-256 994cd027...a415ccc6, unchanged since; checked
by `evaluation/verify_v3.py`), written after the verification below and before any v3 experiment. Deviations:
`evaluation/PROTOCOL_V3_DEVIATIONS.md`. Checkpoint of the reviewed version: `checkpoints/v2_2026-10-03/` (172 files,
`MANIFEST.sha256` verified 2026-10-11).

Status values: *done* / *done (modified)* / *deferred* / *rejected* / *not done*.

## 1. Verification performed before deciding (read-only)

| Review statement | How it was checked | Result |
|---|---|---|
| v1 protocol pre-specified "simulation-pretrained + real fine-tuned"; v1 implemented a pooled LightGBM arm; v2 dropped it | `FINAL_EVALUATION_PROTOCOL.md` §1 l. 49-51; `exp_lira.py` l. 289-290; v2 paper and `PROTOCOL_V2.md` | Verified. v1 also had a CNN fine-tuning arm (brittle at small k); both were dropped in v2 without comment. The v1 paper reported the pooled arm (Fig. "few-shot", 5 draws, V10 set). |
| Affine arm beats real-only at 10 km for V1/V3/V5 | `results/v2/paired_vs_real.csv` | Verified: -0.027 (11/20), -0.048 (14/20), -0.024 (11/20). |
| V4 uses V0's sensor mixture, bias +0.40 | `sim_generate.py` l. 111, 170 (`drive(..., sensor_kind="mix")`); `summary_variants.csv` | Verified. |
| Band correlations: 5-10 Hz Spearman 0.80; overall RMS R^2 0.78 vs 0.71 for 10-15 Hz | recomputed from `band_gain.csv`, `summary_variants.csv` | Verified (0.800 / 0.812; 0.780 vs 0.714). |
| V4 ratios 1.93 (10-15 Hz), 1.23 (RMS), 2.09 (2-5 Hz) vs V0 1.86 / 1.12 / 1.80 | `band_gain.csv` | Verified. |
| "5 km" = 4.9 km of road, 475 segment-passes (301-640), ~9.7 passes per segment | `value_of_simulation.csv` (`km_real`, `n_real_units`) | Verified (4.91 km; 475 [301, 640]; 9.66). |
| V0 motorway log level +0.145 (~16 %), real -0.013 / +0.016 | `variants_zeroshot.csv` `level_*` | Verified. |
| Within-route MAE after a 5 km offset 0.395-0.519 (V0 0.400, V2 0.395, V7 0.405) | `variants_calibration.csv` | Verified. |
| M7 evaluates 119 of 228 M13 segments | `physics_inversion.py` l. 73 (grid at multiples of 100 m); `units.csv` (M13-VH starts at ...60 m); `physics_inversion_segments.csv` (238 rows = 2 x 119) | Verified. |
| LiRA-CD mounting: AutoPi "fixed to the frame in the middle of the GM car close to the front axle" | LiRA-CD data article (Europe PMC PMC10375556 full text; re-read 2026-10-11) | Verified; Fig. 5 caption: "inside the middle console". |
| P79 surveys 10-09-2020 (CPH1, M3, M13) and 04-06-2020 (CPH6); car data 2020-2021 | `data/raw/lira_cd/reference/readme.txt`, `car/readme.txt` | Verified. Car drives on our routes 03-11-2020 to 27-08-2021 (1.8-14.8 months after the survey of the same route). **The v2 ARAN caption had wrong dates** (CPH6 P79, M3/M13 ARAN). |
| The P79's maker is not named in LiRA-CD, so "different profiler" (Table S8 in v2) is unverified | data article; reference readme | Verified: no maker named. |
| Review checks reproduce published numbers (c1-c8) | read scripts and outputs; reproduced in v3 | Reproduced: c4 identical for all 960 overlapping fold-draw values; c8 full-feature MAEs identical; c2, c3, c6 identical to three decimals. |

## 2. Ledger

| ID | Recommendation (review section) | Verified? | Class | Decision | Status | Outcome / change to the paper |
|---|---|---|---|---|---|---|
| D1 / P1.1 / L1-L3 | Restore the v1 pooled sim+real arm for all variants, paired with all comparators, per route | yes (§1) | A | implement as V3-1 (class R) for V0-V8, V10, k = 1-20, 20 draws | done (modified: in a new frozen protocol V3 instead of an addendum to PROTOCOL_V2 §8) | `experiments/v3/pooled_vs_real.py` -> `results/v3/pooled_vs_real.csv` (4,000 rows). Pre-registered H1 holds. Table II, Table III, Fig. 2c, Fig. 4b, Table S17, Sec. V-D. |
| D1 / L4 | Rewrite value-of-simulation claims | yes (after V3-1) | A | rewrite | done | Abstract, introduction, Sec. V-D, Discussion recipe, Limitations ("Combination methods"), Conclusion. No sentence says real drives beat any variant at 10 km or more without naming the level offset. |
| D2a / P1.2 / L5 | "Only because of the holder resonance" contradicted by V4; name the vehicle population | yes | A | reword; report V4 | done | Sec. V-B (V4 raises the bias by +0.39 m/km), Sec. V-C (V4 off the band association and outside the band-limited range), Discussion correction, Supplement S1 corrected statement (i). `grep "only because\|only through a sensor"` finds only the quotation in S1. |
| D2b / P1.2 / L5 | Report all band correlations | yes | A | V3-4 | done | Sec. V-C (Spearman 0.97, 0.88, 0.80, 0.25, 0.22; R^2 0.78 vs 0.71), Fig. 3b text, Table S23. |
| D2c / P2.1 / L6 | Band-limited intervention | reproduced | B | V3-3 (class E), with class-level spreads and accuracy cost | done | H3 and H3b hold. Sec. V-C, Fig. 3c, Table S24. Reported cost: the low-band estimator has a common class-dependent level error and worse MAE after an offset. |
| D2 / P2.2 / L7 | Level decomposition | yes | A | V3-5 | done | Table II log levels by class; Spearman 0.88 between the class-level difference and the MAE after an offset; used in Sec. V-D to explain which combination is better. |
| D3 / P1.3 / L12 | Cite Nitsche 2014, Ngwangwa 2014, Wu 2023, Jeong & Jo 2024; narrow the gap sentence | yes (Crossref, abstracts, Bajic et al. full text) | A | add | done | Intro paragraph 2, Related Work; `references/REFERENCE_AUDIT.md` §E. Nitsche and Ngwangwa 2014 rest on a secondary description (Bajic et al.) and the title; flagged for a human to read. |
| D3 (Shangguan 2025) | Check whether it uses LiRA-CD | not established | C | cite only if it uses LiRA-CD | done (not cited) | Crossref has no abstract; its references include Bajic et al. but not the LiRA-CD article. Reason in REFERENCE_AUDIT §E. |
| D4a / P1.4 / L8 | Label every MAE as within-route or pooled | yes | A | implement | done | Method defines both; abstract labels each MAE; Table III gives both; within-route values with three decimals. |
| D4b / L8 | Define k km with pass density | yes | A | implement | done | Method (9.7 passes per segment, 475 [301-640] segment-passes, 47 km of driving over 4.9 km at k = 5); Table III "passes" column. |
| D4c / L7 | Log level per class in Table II | yes | A | V3-5 | done | Table II columns "level urban/motorway". |
| D5 | Frame structural limitations | yes | A | Limitations + Conclusion | done | Limitations: external validity, evidence class, combination methods, simulator, other. |
| P1.5 / L9 / E7.1 | Paired within-route Delta-rho; reword "ranks as well" | reproduced (c3) | A | V3-6 | done | Abstract/intro/V-B/Discussion: "within 0.05 on every route"; real-trained better on urban (+0.042, +0.044), slightly worse on motorways (-0.020, -0.023). Table S5. |
| P2.3 / L10 / E5 | Speed robustness rows | reproduced (c6) | B | V3-7 | done | Sec. V-E, Table S26. Not fully robust: with the log speed SD as a covariate the real-trained urban elasticity is -0.06 [-0.16, +0.02]; with the speed CV the urban paired difference turns negative (-0.07 [-0.21, +0.01]). Both reported. |
| P2.4 / L11 | Fix the M7 segment grid | yes | A | V3-8 | done | 228 M13 segments (MAE 0.169 -> 0.168); M7 paired difference +0.081 -> +0.074 [+0.039, +0.105]; Table I, S4, S12; v2 macros regenerated (38 M7 macros changed, nothing else). |
| P2.5 / L14 | No-simulator comparator | reproduced (c2) | B | V3-9 | done | Sec. V-D: 0.78 m/km at 5 km, 0.76 at 20 km; Table S17 last row. |
| P2.6 / L15 | Test-route uncertainty | design checked | B | V3-2 with per-segment, draw-averaged error differences | done (modified) | Table S18; Sec. V-D. Interval centres equal the per-draw pooled differences to 1e-16 (verify_v3). |
| P3.1 | Calibration pass budget | - | B | V3-10 | done | One pass per segment (49 segment-passes) leaves both simulation combinations nearly unchanged; real-only 0.68 -> 0.93 m/km. Abstract, Sec. V-D, Table S19. |
| P3.2 | Amplitude dependence of the ratio above 10 Hz | not run | D | candidate causes listed instead | rejected | Sec. V-C lists candidate causes; physical source stated as unidentified. |
| P3.3 | Platoon data | not run | D | - | deferred | - |
| P3.4 / E1 | Relative errors per class | yes | B | V3-11 | done | Sec. V-A sentence (19 % urban, 12 % motorway), Table S6. |
| P3.5 / H | Length: shorten; move Sec. V-F | - | B | move V-F (Table IV, Fig. 6) and the speed figure to the supplement | done | Main paper 10 pages (as v2); supplement 19 pages. V-F folded into one Limitations sentence + Supplement S7. |
| P3.6 | Dynamics-randomisation / SimOpt framing | refs verified | D | one sentence | done | Related Work (Peng 2018, Chebotar 2019, Tobin 2017). |
| P3.7 | Commit with tags at freeze points | - | - | authors' decision | not done | No commits were made (standing instruction). Integrity is supported by the checkpoint manifest and the protocol hash. |
| E3 | Cite the LiRA-CD mounting statement; extend candidate causes | yes | A | implement | done | Data section and Sec. V-C. |
| E1 (optional) | Speed inputs and class level | yes | D | - | not done | - |
| E2 | Scale b cannot see between-class errors | yes | A | covered by V3-5 | done | Table II class levels. |
| E7.3 | Coarse M13 intervals | yes | B | caption note | done | Table S5 caption ("M13 has only 6 blocks"). |
| E8 | Vehicle sweep is secondary | - | B | move | done | Supplement S7. |
| F (Table S8 in v2) | "different reference survey and processing" | yes | A | caption | done | Table S10 caption. |
| F (LiRA-CD) | Mounting and survey dates | yes | A | Data section; ARAN caption | done | Data section; Table S13 caption corrected. "Two to fourteen months" (first v3 draft) corrected to "two to fifteen" in the final check. |
| J.6 | Three decimals for close within-route values | yes | B | implement | done | Table III, Tables S5, S17-S19. |
| H (figures) | Fig. 2c joint markers; Fig. 3b labels / V4; Fig. 4b joint curves and "pooled MAE" axis | yes | B | implement | done | `make_figures_v3.py` -> `figures/v3_variants`, `v3_spectra`, `v3_value`; Fig. 4b has its own zoomed axis, off-scale values in the caption. |
| H (tables) | Table I M7; Table II log levels; Table III joint + within + k km; Table S14 affine 10 km + joint | yes | A | implement | done | `make_tables_v3.py` -> `tables/v3_variants.tex`, `v3_value.tex`, `v3s_*.tex`. |
| Not recommended (G) | new architectures, more variants, mixed models, MC corrections, Skar reproduction, new data | - | - | agreed | not done | - |

## 3. Outcomes of the protocol items (`results/v3/`, macros `paper/numbers_v3.tex`)

| Item | Result | Hypothesis / wording rule |
|---|---|---|
| V3-1 joint training | Better than real-only LightGBM for every variant at every k (mean difference negative, 16-20 of 20 draws); 5 km: 0.45-0.47 m/km pooled (real-only 0.68); 20 km: -0.03 to -0.01 m/km. Spread over V0-V8: 0.02 (5 and 20 km) vs 0.14 / 0.17 for the level offset; 1 km: 0.44-0.56. Per route at 20 km: better in 31 of 36 variant-route cells, worse in 5 (4 on M3, 1 on CPH6) by at most 0.016 m/km. Joint minus level offset at 5 km: -0.096 to -0.062 (V1, V3, V5), +0.002 to +0.032 (other six). Affine map worse than the better of the two for 9/9 variants at 5 and 20 km. | H1 holds for V0-V8 and with V10; all 9 variants meet the "beats" rule at all five k. |
| V3-2 test-route intervals | 5 km: all 18 intervals exclude zero (level offset -0.26 to -0.12; joint -0.23 to -0.21). 20 km: joint all 9 below zero; level offset above zero for V1, V3, V5 (+0.08 to +0.12), including zero for V6 and V8, below zero for V0, V2, V4, V7. | descriptive of these routes, conditional on the 20 draws |
| V3-3 band-limited | Spread of the mean log level over the 8 sensor variants 0.25 -> 0.08 (32 %; urban 49 %, motorway 34 %); bias spread 0.52 -> 0.14 m/km; dropping only 10-15 Hz changes every spread by <= 2 %. V4 +0.22 vs +0.02..+0.10. Cost: urban under-, motorway over-prediction for every sensor variant; MAE after a 5 km offset 0.48-0.57 vs 0.42-0.56. | H3 and H3b hold (urban ratio 49 %, close to the 50 % threshold) |
| V3-4 band associations | Spearman with bias: 10-15 Hz 0.97, RMS 0.88, 5-10 Hz 0.80, 2-5 Hz 0.25, 0.5-2 Hz 0.22; R^2 0.71 vs 0.78 (RMS). | all reported |
| V3-5 level decomposition | V0: urban +0.006, motorway +0.145 (~16 %); class difference 0.09-0.30 over V0-V8, Spearman 0.88 with the MAE after a 5 km offset. | - |
| V3-6 ranking | All per-route differences within 0.05 (max 0.044); real-trained: +0.042, +0.044 urban, -0.020, -0.023 motorway (all intervals exclude zero); mean +0.011 [+0.004, +0.020]. | wording "within 0.05 on every route" |
| V3-7 speed robustness | Unit FE: no material change. Log speed SD: real urban -0.06 [-0.16, +0.02] (was -0.10 [-0.17, -0.05]); paired urban difference +0.12 [+0.09, +0.16] unchanged. Speed CV (tied to 1/v, r = -0.86): urban difference -0.07 [-0.21, +0.01]. | reported with the pre-specified caveat |
| V3-8 M7 fix | 119 -> 228 M13 segments; MAE 0.169 -> 0.168; pooled M7 0.494 (all 1,678 segments). | before/after both reported (S1) |
| V3-9 no-simulator index | label-free alpha_car 0.59-0.72 (alpha_sim 1.19-1.26); affine index 1.09 / 0.78 / 0.76 m/km at 1 / 5 / 20 km. | - |
| V3-10 pass density | m = 1, 2, 5 at 5 km: real-only 0.93 / 0.75 / 0.69; level offset 0.43-0.55 / 0.42-0.55 / 0.42-0.55; joint 0.44-0.49 / 0.44-0.48 / 0.45-0.48; with m = 1 both simulation arms beat real-only in every draw for every variant. | - |
| V3-11 relative errors | real-trained LightGBM 19 % urban, 12 % motorway; V0 zero-shot 19 % / 17 %. | - |

**Unfavourable or unexpected findings, all reported in the paper or supplement:** joint training is slightly less
accurate than a level offset for the six best-matched variants (by up to 0.03 m/km at 5 km); joint training still
depends on the variant at 1-2 km; at 20 km it is not better on every route (5 of 36 cells worse, mostly M3); the
low-band estimator is less accurate and introduces a class-dependent level error; the real-trained urban elasticity
loses its interval under the speed-SD control and the urban paired difference changes sign under the CV control;
H3's urban ratio (49 %) is close to its threshold.

**Process corrections made before any v3 number was reported:** (i) the spread ratios in `make_numbers_v3.py` were
first computed from macro strings rounded to two decimals (e.g. urban 0.08/0.17 = 47 % instead of 49 %); fixed to use
unrounded values. (ii) V3-11 was first coded as the mean of per-route relative errors; changed to the protocol's
definition (class MAE / class mean IRI) before its output was viewed. (iii) The affine-map sentence of the first draft
("lies in between") was contradicted by the data and replaced by the measured statement (worse than the better of
the two for 9/9 variants). (iv) The method section first said the joint arm had not been reported before; the first
version did report it (one simulation set, five draws), corrected.
