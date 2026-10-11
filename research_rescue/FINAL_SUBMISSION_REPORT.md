# Final corrections and verification (2026-10-11)

Response to the final verification audit (`review/final_audit/audit.md`, verdict "ready after minor corrections").
This round made only the corrections the audit required. No experiment was rerun, and no split, metric, protocol or
existing result changed. The audit report is unchanged (SHA-256 identical to its checkpoint copy).

## 1. Starting state

* Worked on the audited version: `paper/main.pdf` and `supplementary.pdf` compiled 2026-10-11 08:25, the same files
  the audit rebuilt and inspected (no source was edited between the audit and this round).
* Checkpoint before any change: `checkpoints/v3_2026-10-11/` (170 files: paper sources and PDFs, tables, figures,
  `results/v3/`, `experiments/v3/`, generators, v3 documents, audit report; `MANIFEST.sha256` verified).
* Version control: `research_rescue/` is not tracked in git, and no commit was made (the authors' standing
  instruction is not to commit without being asked). The record of changes is the checkpoint, `CHANGELOG.md`
  (2026-10-11 entry) and the file list in section 3.

## 2. Audit issues and their resolution

| # | Audit issue | Resolution | Evidence | Status |
|---|---|---|---|---|
| B1 | Discussion: untrained RMS/v^0.5 "within 0.05 of every trained estimator we tested" (false for M2c, LightGBM without speed inputs and the speed-only model) | Narrowed to real-trained LightGBM, MLP, CNN, M7 and simulation-trained LightGBM under every variant; the three exceptions are named with their largest gaps (0.10, 0.18, 0.72). Results V-B adds the other variants, MLP, CNN and M7 as point estimates (largest gap over V0-V8 0.038). Supplement S1 (iv) and the S4 text aligned. The per-route values existed in result files but were not printed; they are now Table S5 (bottom panel), from the new read-only script `experiments/v3/rank_scope.py`. | `results/v3/rank_scope.csv`; agrees with `rank_paired.csv` to 1e-6 (asserted) and with a re-derivation from the saved predictions to 2e-16 (`verify_final.py`) | Resolved |
| B2 | Method: LightGBM configuration "chosen by inner leave-one-route-out validation when real training routes are available" | Now states the implementation: inner selection only for LightGBM trained on whole real training routes (M1, M3, unit-disjoint check); every other LightGBM, including the simulation-trained models, the k-km real-only comparator and joint training, uses the first configuration. | Code: `exp_lira.part_ladder`, `real_baselines_v2.gbm_inner` (inner selection); `value_of_simulation.py`, `pooled_vs_real.py`, `simreal_variants.py`, Bajic anchor (first configuration). The audit showed that the choice does not change the comparisons (first configuration best or tied). | Resolved |
| B3 | Intro: code, protocols, configurations and predictions "are provided with the paper" (nothing is public) | Now: "We will release the code, protocols, configurations and all predictions with the published version of the paper." Method and supplement S1 add that the protocols were frozen as dated files in the working copy, not registered publicly, so their timing cannot be verified independently; supplement S8 says the files are not yet public. No release was created (section 5). | - | Resolved (statement accurate); release itself open |
| B4 | Table II caption: class level "over the segments of a road class", values are the mean of the two route levels | Caption fixed in `make_tables_v3.py` (same fix in the Table S24 caption); Method defines the class level as the mean of its two route levels; Fig. 2b caption says the same. Tables regenerated. | `level_decomposition.csv` and `band_limited.py` average the two route levels; no value changed | Resolved |
| B5 | Speed: Sec. V-E's closing sentence and the Discussion state the urban result without its caveat; 1 km-block intervals unlabelled | V-E now says the urban advantage of simulation-trained LightGBM holds in the main design and with the telematics-unit and speed-SD controls but not with the speed-CV control, so it is not established. The Discussion speed paragraph says that with the CV control the difference changes sign and that with the speed-SD control the real-trained urban elasticity's interval includes zero. V-E labels single elasticities (1 km blocks) and paired differences / robustness rows (5 km). The Method says intervals use 5 km blocks except single-estimator speed elasticities and spectra (1 km). | `speed_real.py` (1 km), `speed_paired.py`, `speed_robustness.py`, `speed_scaling_sim.py` (5 km); `results/v3/speed_robustness.csv` | Resolved |
| E5 / C-13 | Nitsche 2014 and Ngwangwa 2014 described from secondary sources only | Ngwangwa 2014: accepted manuscript read (University of Pretoria repository). The network was trained on responses of a full Land Rover model over slightly modified measured profiles and tested on that vehicle's measured responses; Related Work now says so. Nitsche 2014: abstract read (AIT repository). It confirms simulated-response training, probe-vehicle validation and the wLP target, but not the measured profile, the profilometer reference or the speed condition; those three details are now attributed to Bajic et al., whose full text states them. | `references/REFERENCE_AUDIT.md` section F | Ngwangwa resolved; Nitsche partly (full text not read) |
| E4 / C-17 | Venue requirements unverified | No target venue is specified in the repository or the conversation (only candidate venue types in `FINAL_REPORT.md` §I). Venue-dependent formatting left unchanged; nothing cut. | - | Unverified (needs the venue) |
| C-14 | No version control / public freeze | See B3 and section 1. | - | Open (authors' decision) |
| C-18 | Upstream pipeline (map matching, features, simulation) not re-run by the audit | Outside the corrections; unchanged. | - | Unverified, as in the audit |

## 3. Files modified

Paper sources: `paper/sections/discussion.tex`, `results.tex`, `method.tex`, `intro.tex`, `related.tex`,
`paper/supplementary.tex`; generated: `paper/numbers_v3.tex` (5 macros added), `tables/v3_variants.tex`,
`tables/v3s_band_limited.tex` (captions), `tables/v3s_rank.tex` (caption and bottom panel); compiled
`paper/main.pdf`, `paper/supplementary.pdf`.
Generators and pipeline: `make_numbers_v3.py`, `make_tables_v3.py`, `run_all_experiments.py` (steps `v3_rank_scope`,
`final_verify`).
New: `experiments/v3/rank_scope.py`, `results/v3/rank_scope.csv`, `evaluation/verify_final.py`,
`results/v3/verification_final.json`, `review/final_audit/scripts/` (the audit's scripts, kept as a record).
Regenerated: `results/v3/paper_numbers_v3.json`, `results/v3/verification_v3.json`.
Documents: `CHANGELOG.md`, `README.md`, `references/REFERENCE_AUDIT.md`, this report.
Not changed: every result file of `results/v2/` and every other file of `results/v3/`, all figures, all experiment
scripts other than the new one, `numbers.tex`, `numbers_v2.tex`, the protocols, the bibliography.

## 4. Build and consistency checks

| Check | Result |
|---|---|
| Pipeline `run_all_experiments.py --force --only v3_rank_scope v3_numbers v3_tables bib_cited paper v3_verify final_verify` | all steps ok |
| `evaluation/verify_v3.py` (25 existing checks) | 25 passed |
| `evaluation/verify_final.py` (14 new checks: ranking scope re-derived from saved predictions; new macros; no existing macro changed; superseded wording absent and corrected wording present in main, supplement and tables; PDFs newer than every input; clean logs; no `??`; protocol hash; checkpoint manifests; audit report unchanged) | 14 passed |
| Clean-room rebuild (copy of `paper/`, `tables/`, `figures/`; supplement, main, supplement, main) | text and byte size identical to the shipped PDFs; no undefined reference, overfull box or missing figure |
| Macro values versus the audited checkpoint (`numbers.tex`, `numbers_v2.tex`, `numbers_v3.tex`) | no value changed; added `rkScopeAbsMax` 0.044, `rkScopeVarAbsMax` 0.038, `rkIdxGapMax` 0.10, `rkNoSpeedGapMax` 0.18, `rkSpeedOnlyGapMax` 0.72 |
| Numbers in the PDF text versus the checkpoint PDFs (multiset of numeric tokens) | main paper: none removed; added only the four new values printed in the text plus labels ("1 km", "5 km", "M7", "V0-V8") and the page number 11. Supplement: only the old page number 19 removed; added the new Table S5 panel |
| Search for every corrected claim across main paper, supplement and all tables | no contradictory wording left |
| Visual inspection | main pages 9-11 and supplement page 6 (Table S5) at readable resolution; all supplement pages as a contact sheet; no layout defect |
| Page counts | main 11 pages (was 10: the added text pushes half a column of references onto page 11); supplement 18 (was 19: float reflow) |

## 5. Code-availability statement

Accurate now. The paper states that code, protocols, configurations and predictions will be released with the
published version, and that the protocols were not registered publicly. No public release was created in this round.
Publishing the code and predictions is an irreversible, outward-facing step that needs the authors' decision on the
host (e.g. an archive with a DOI), the licence (LiRA-CD is CC BY 4.0, so derived predictions need attribution) and
the co-author's agreement. When a release exists, replace the intro sentence with its DOI or URL.

## 6. Unresolved items

1. Target venue not specified, so page limit, abstract length (about 266 words) and anonymity rules are unchecked.
   The main paper is 11 pages.
2. No public release yet (section 5), and `research_rescue/` is not under version control.
3. Nitsche et al. 2014 full text not read; three details rest on Bajic et al. and are attributed to them. `mounting2026`,
   `hanson2014iri` and `ngwangwa2010ann` remain title-level citations from earlier rounds.
4. The upstream data and simulation pipeline was not re-executed by the audit (unchanged).

## 7. Scientific results

Preserved. No experiment, split, metric, calibration or inference procedure changed, and no existing number changed
(checked macro by macro and in the PDF text). The only new numbers are point estimates read from existing result
files (per-route within-route Spearman differences). They narrow a sentence that overstated the evidence and print
the evidence for a claim the abstract already made (that the ranking bound holds for every simulator variant).
Negative findings and limitations are unchanged; the speed result is now reported with its caveat in every place
it is interpreted.
