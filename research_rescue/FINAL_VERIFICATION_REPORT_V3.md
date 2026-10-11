# Final verification report, revision v3 (2026-10-11)

Response to `INDEPENDENT_REVIEW_V3.md`. The review was treated as a set of hypotheses: each statement was checked
against the repository before acting (`IMPLEMENTATION_AUDIT_V3.md` §1), every recommendation was classified A-E and
given a decision (§2), and the justified analyses were specified in `evaluation/PROTOCOL_V3.md`, frozen on 2026-10-10
before any of them ran. This report states what was verified, how, and what remains open.

## 1. Deliverables (all present and non-empty, checked 2026-10-11 08:23 IST)

| # | Deliverable | Location |
|---|---|---|
| 1 | Compiled revised main paper (10 pages, IEEE conference format) | `paper/main.pdf` |
| 2 | LaTeX source | `paper/main.tex`, `paper/sections/*.tex`, `paper/fig_pipeline.tex`, macros `paper/numbers.tex`, `numbers_v2.tex`, `numbers_v3.tex`, bibliography `paper/references_cited.tex` |
| 3 | Supplementary material (19 pages) and source | `paper/supplementary.pdf`, `paper/supplementary.tex` |
| 4 | Machine-readable results | `results/v3/*.csv`, `results/v3/pooled_segpred.npz`, `results/v3/paper_numbers_v3.json`, `results/v3/final_results_v3.{csv,json}` (headline numbers with provenance), `results/v2/` (M7 fix) |
| 5 | Figure and table code and outputs | `make_figures_v3.py` -> `figures/v3_{variants,spectra,value}.{pdf,png}`; `make_tables_v3.py` -> `tables/v3_*.tex`, `tables/v3s_*.tex`; v2 generators rerun after the M7 fix |
| 6 | Revision protocol and deviations | `evaluation/PROTOCOL_V3.md` (SHA-256 994cd027...a415ccc6, unchanged), `evaluation/PROTOCOL_V3_DEVIATIONS.md` |
| 7 | Implementation audit | `IMPLEMENTATION_AUDIT_V3.md` |
| 8 | Final verification report | this file; machine-readable checks in `results/v3/verification_v3.json` |
| 9 | Reproduction instructions | `README.md` (section "Reproduce", third round), `run_all_experiments.py` (v3 steps), Supplement S8 |
| - | Also | `CLAIM_AUDIT_V3.md`, `references/REFERENCE_AUDIT.md` §E, `CHANGELOG.md`, checkpoint `checkpoints/v2_2026-10-03/` |

## 2. Scientific validity

* **Leakage.** The joint-training script asserts that no simulated unit of the test route enters training and that
  every paired block comes from the training routes; the shared sampler (`default_rng(1000 d + 7)`) makes all arms
  paired by draw; the test-route interval script asserts that it reproduces the stored real-only results exactly
  (1e-9) before using them; cached zero-shot predictions are asserted equal to the stored held-out predictions.
* **Pre-specification.** All v3 analyses were specified in `PROTOCOL_V3.md` before they ran. Because the test routes
  and some reviewer checks were known, every v3 analysis is labelled R or E, never confirmatory, in the paper and the
  supplement. Three hypotheses were stated in advance; all three hold (H1, H3, H3b), and the margins are reported
  (H3's urban ratio is 49 % against a 50 % threshold).
* **Completeness.** Every variant, draw and k is reported (Tables S16-S19, S24). Unfavourable results are in the paper:
  joint training is up to 0.03 m/km worse than a level offset for six variants at 5 km; it still depends on the
  variant at 1-2 km; at 20 km it is worse on 5 of 36 variant-route cells; the low-band estimator is less accurate and
  biased by road class; the speed results are not robust to the speed-CV control.
* **Inference.** Paired differences use 5 km-block bootstraps over test segments; intervals are described as
  conditional on the trained models and the 20 calibration draws, and as describing these four routes only.

## 3. Numerical consistency (`evaluation/verify_v3.py`, 25 checks, 0 failed)

* Macro files: names unique across v1/v2/v3; no unresolved value; every number macro used in the paper and its tables
  is defined; both PDFs contain no `??`, their logs no undefined references or overfull boxes.
* Re-derivations independent of `make_numbers_v3.py`: the joint-training ranges at 5 and 20 km, H1, the
  band-limited spread ratio, the pass-density claim and the ranking bound match the printed macros.
* Cross-checks between two computations: the centres of the test-route intervals (segment-level, draw-averaged)
  equal the mean per-draw pooled MAE differences to 1e-16.
* Reproduction of the reviewer's checks: the joint-training arm is identical to the reviewer's c4 values for all
  960 overlapping fold-draws; the full-feature band-limited retraining reproduces the v2 zero-shot MAEs exactly.
* Integrity: `PROTOCOL_V3.md` has its frozen hash; the v2 checkpoint matches its manifest (172 files).
* The M7 fix changed exactly the 38 M7 macros of `numbers_v2.tex` and the M7 rows of `summary_real_estimators.csv`;
  no other v2 result file changed.

## 4. Answers to the review's scientific questions

1. **Value of simulation versus combination method.** With 5 km of profiled road and its paired drives (about 475
   segment-passes), simulation over all profiled roads beats training on those drives alone for every variant whether
   the drives set a level offset (0.42-0.56 vs 0.68 m/km pooled) or enter joint training (0.45-0.47); all test-route
   intervals exclude zero. The variant dependence that v2 reported at 10-20 km belongs to the level offset: with joint
   training every variant stays better than real-only up to 20 km (by 0.01-0.03 m/km) and the variants span only
   0.02 m/km from 5 km on. A level offset is the most accurate combination at 5 km for the six variants whose level
   error is nearly common to both road classes; joint training is better for the three with a class-dependent error.
   One pass per segment suffices for both combinations at 5 km.
2. **Sensor/vehicle mismatch: correlation, model-level intervention, physical causation.** Correlation: the bias
   follows the high-band amplitude deficit (Spearman 0.97 at 10-15 Hz, 0.88 overall RMS, 0.80 at 5-10 Hz) across
   nine non-independent variants. Model-level intervention: removing every feature with content above 10 Hz shrinks the
   spread of the sensor variants' level to a third, while dropping the 10-15 Hz band alone changes nothing, so the
   variant differences enter through the broadband features. The vehicle population is a second, independent source
   (V4: +0.39 m/km with V0's sensors). Physical causation is not established; candidate causes are listed.
3. **Generalisation scope.** One car model, one telematics-unit type, four routes in one region, road class confounded
   with route; all intervals describe these routes. Other vehicles and phones were examined only in simulation
   (Supplement S7). New paired data, ideally collected after freezing the simulator, are required.
4. **Related work and novelty.** Nitsche 2014 (closest design: simulation-trained regressors validated on a probe
   vehicle, for the weighted longitudinal profile, without varying speed), Ngwangwa 2014, Wu 2023 and Jeong & Jo 2024
   are cited; the gap statement is narrowed to continuous IRI from a production car on held-out roads of public data,
   with a decomposition of what transfers, which simulator choices set the level, and the paired data needed for
   several combination methods.
5. **Metric labelling.** Within-route and pooled MAE are defined in Sec. IV and every MAE is labelled; "k km" is
   defined with its pass density (9.7 passes per segment, 475 segment-passes at 5 km, 47 km of driving over 4.9 km
   of road) and the pass-density experiment shows how much of that is needed.

## 5. Claims, related work, document quality

* **Claims.** `CLAIM_AUDIT_V3.md` checks every substantive claim of the final text; all are SUPPORTED as worded. Five
  wording problems were found and fixed during the audit (affine map "in between"; joint arm "not reported before";
  "two to fourteen months"; "matched the car worst"; CV control "over-adjusts"). The phrases the review asked to remove
  remain only as a quotation in Supplement S1.
* **Related work.** New references were added by DOI from Crossref metadata; claims were checked against abstracts,
  the LiRA-CD data article (full text) and Bajic et al. (full text). Nitsche 2014 and Ngwangwa 2014 rest on a
  secondary description plus their titles. Shangguan et al. 2025 was not cited because its data source could not be
  established (`references/REFERENCE_AUDIT.md` §E).
* **Document quality.** Main paper 10 pages (same as v2) after moving Sec. V-F, Table IV and two figures to the
  supplement; supplement 19 pages. All pages were rendered and inspected: no overlapping labels, no overfull boxes,
  floats near their first reference. Figure 4b uses a zoomed axis; the four off-scale real-only values are in the
  caption.

## 6. Reproducibility

`run_all_experiments.py` contains every v3 step in dependency order, ending with `v3_verify`; README lists the
equivalent individual commands, seeds and run times (joint-training arm about 28 min with four processes, pass
density 19 min, everything else minutes). All numbers in the paper are macros generated from the result files.

## 7. Open items for the authors

* Commit `research_rescue/` with tags at the protocol-freeze points (not done: commits need the authors' permission).
* Read the primary articles cited at title level or through a secondary description (`mounting2026`,
  `hanson2014iri`, `ngwangwa2010ann`, `ngwangwa2014exp`, `nitsche2014wlp`), and check whether Shangguan et al. 2025
  uses LiRA data.
* Confirm the target venue's page limit; the next cuts would be Sec. V-E or part of Sec. V-A.
* The decisive next study is confirmatory: new paired data from another car type and city, with the simulator and
  analysis frozen beforehand.
