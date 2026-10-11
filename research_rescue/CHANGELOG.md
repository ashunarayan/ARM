# CHANGELOG (research rescue)

Chronological log of implementation decisions and fixes. Entries marked [protocol] concern the frozen
evaluation protocol; none of them were made in response to test-set results.

## 2026-10-02
- Created `research_rescue/`; recorded `BASELINE_STATE.md` before any change. Original code/paper untouched.
- LiRA-CD downloaded via the public figshare API (CC BY 4.0). Reference subset complete; car subset parallel download.
- IRI implementation (`common/iri.py`) validated against the P79 profilometer (`evaluation/iri_unit_test.py`).
  Found that LiRA-CD's CPH6-HH profile and IRI files cannot be aligned (no shift/reversal gives r > 0.2), while the
  other 7 file pairs agree to r = 1.000; an a-priori consistency rule (10 m r >= 0.95) flags the pair; downstream
  labels use the profile-derived IRI (which carries GPS).
- Re-ran the September audit scripts unchanged (`audit/run_audits.sh`).
- Discovered (and verified in TF 2.10) that the legacy asymmetric loss reduces to a scalar before Keras applies
  sample weights, so the paper's "2-D inverse-frequency sampling" did not re-weight samples in Run 1
  (`results/legacy_weighting_check.txt`). The PyTorch re-implementation reproduces this behaviour by default.
- [protocol] Frozen `evaluation/FINAL_EVALUATION_PROTOCOL.md` and `config/models.json` before any test evaluation.
- Simulator: replaced a polynomial (SOS) realisation that deviated up to 19 % from the state-space solution by a
  modal first-order-hold realisation (3.9e-13 vs. direct recursion; 1.8e-3 vs. continuous-time RK45).
- `evaluation/sim_unit_test.py`: fixed two test-implementation errors (eigen-frequency pairing; band of the ramp
  check) and widened the plausibility bound on body/pitch modes from 2.2 Hz to 3.0 Hz because the pitch frequency
  ~ f_s * L / (2 r_y) reaches ~2.4-2.5 Hz inside the documented parameter ranges. Unit-test bounds are engineering
  sanity limits, not evaluation thresholds.
- LiRA-CD download: the first sequential `curl` downloader survived `TaskStop` (orphaned child process) and kept
  appending to `CPH1_HH.hdf5` while a resumed download wrote the same file, corrupting it (+9.5 MB). Detected by size
  and MD5 mismatch; the orphan was killed and the file re-downloaded and MD5-verified. All 47 LiRA-CD files now match
  the figshare MD5s (`data/raw/download_lira.py` is the single canonical downloader).
- LiRA builder: 11 passes contain no accelerometer/speed data (GPS only) and are skipped and counted
  (`data/processed/lira/build_status.json`). CPH1 is a ring road: the original monotone-chainage filter discarded
  every fix after a chainage wrap, so 12 CPH1-VH passes produced no units; GPS tracks are now split into runs of
  plausible progression and units extracted per run (bug found from unit counts; no labels or results involved).
- Controlled robustness experiment: the first version drew new random vehicles/speeds/sensors for every perturbation
  level (level-to-level noise ~0.1 m/km). It now uses common random numbers (identical passes across levels, only the
  perturbation changes) and 72 passes instead of 32. The first version is kept as
  `results/sim/robustness_v1_independent_draws.csv`.
- `exp_sim_controlled.py` speed part also writes per-speed curves; models are cached per training set within a run.
- Compute allocation for LiRA zero-shot CNNs fixed before any zero-shot result: 3 seeds, simulation sets {ISO-only,
  P79+ISO}; physics index and LightGBM are run on all five simulation sets (incl. the two ablation sets).
- Secondary experiment added after the ISO-trained speed sweep (reported regardless of outcome):
  `exp_sim_controlled.py speed_p79` trains on simulated drives over measured P79 profiles (leave-one-route-out) and
  re-applies the pre-registered speed-invariance criterion to the P79 sweep.
- Few-shot CNN fine-tuning schedule (40 epochs, all layers, lr 3e-4) is kept exactly as pre-registered even though it
  overfits 1 km subsets; no post-hoc tuning of the schedule.
- Paper numbers are generated as LaTeX macros (`make_numbers.py` -> `paper/numbers.tex`) from result files.

## 2026-10-02 (paper writing, audit and verification pass)

- Every quoted number re-traced to a result file. Statements that were not backed by a saved result were either
  turned into saved, re-runnable checks or removed:
  - `evaluation/sim_unit_test.py` now contains the continuous-time check (classical RK4, 10 sub-steps per sample). The
    earlier ad-hoc RK45 comparison (1.8e-3) was never saved; its deviation came from starting the discrete and the
    continuous system from different states (u[0] != 0). With matched initial conditions the deviation is 4.4e-9.
    `simulate_pass` already removes the initial offset, so no experiment was affected.
  - `evaluation/cph6hh_alignment.py`: CPH6-HH reported IRI vs its own profile, best r = 0.13 over +/-3 km shifts and
    reversal (controls: r = 1.000 at zero shift). Previously only an interactive diagnostic.
  - `evaluation/lira_sensor_stats.py`: LiRA-CD sensor statistics. **Correction**: the preliminary inspection that set
    the simulator's telematics configuration (55-62 Hz, tilt s.d. 6 deg; config comment "AutoPi rates 56-260 Hz, tilt
    up to ~11 deg") was inaccurate. Nominal rates are 52.6 Hz (66 % of passes) or 333 Hz, quantisation 0.01 g in 81 %
    of passes (else 0.0039 g), tilt median 10 deg, max 41 deg; GPS 0.9-3.4 Hz; CAN speed 50 Hz. The simulator was NOT
    changed (zero-shot results already existed); the discrepancy is disclosed in the paper and tested separately (below).
  - The "11 GPS-only passes" statement was inaccurate: 9 passes are GPS-only, 2 have no speed signal; 2 further passes
    yield no valid unit.
  - `evaluation/route_overlap.py`: the four LiRA-CD routes share no road section (7 of 1,678 segments within 15 m of
    another route, at CPH1/CPH6 crossings).
- Corrected method descriptions found during the audit: neural-net metrics on LiRA-CD/BeamNG are means of per-seed
  metrics (controlled simulation: metrics of the seed-averaged prediction); zero-/few-shot LightGBM uses the first
  grid configuration; the half-car is driven by the mean of both wheel-path profiles; the robustness baseline is the
  telematics configuration on held-out synthetic routes.
- Figures: IRI-validation panel (c) reports the 42 off-scale ARAN points (they were clipped silently); legends use
  math text; LiRA legend no longer says "no real labels" (labels of simulated units are IRI of real profiles).
- Tables: LaTeX escaping of `^ < > # ~` and NaN; tables shrink only when too wide; supplement tables S2-S8 added.
- Macros: math-mode signs (text-mode `<` prints as an inverted exclamation mark in OT1); unsigned `...Abs` variants.
- Bibliography: two-author entries without the serial comma; `paper/make_bib_cited.py` prints only cited entries in
  order of first citation and fails on unknown keys. Claim check of all 37 citations: `references/REFERENCE_AUDIT.md` C.
- Wording: "pre-registered" -> "fixed in advance" (the protocol was not registered with a third party; file times:
  protocol 18:24, first test result 18:43); "physics index" -> "vibration index".
- POST-HOC sensitivity analysis (added after all primary results, reported separately, primary results unchanged):
  `sim_generate.py measuredsensor` + `exp_lira.py zeroshot_sensor` re-run the zero-shot P79-profile experiment with a
  telematics sensor matched to the measured LiRA-CD statistics (paired comparison on the same test units).
- `run_all_experiments.py` covers all steps (sensor stats, alignment search, route overlap, BeamNG vehicle test,
  zero-shot comparisons, P79-trained speed sweep, macros, cited bibliography, paper and supplement).
- Post-hoc sensitivity, first result: a single telematics sensor matched to the measured LiRA-CD statistics
  (`p79-measuredsensor`) gives zero-shot LightGBM MAE 0.69 vs 0.44 m/km for the primary sensor mixture (mostly
  over-prediction on motorways). Because this variant changed two things at once (matched rates AND no
  smartphone-like half), a second post-hoc variant `p79-measuredmix` (matched telematics half + the primary
  smartphone-like half) was run to separate them. All three are reported; the primary configuration is unchanged.
- Post-hoc sensitivity, final result (`results/lira/zeroshot_sensor_*`): zero-shot LightGBM MAE 0.44 (primary
  mixture), 0.46 (matched telematics half + primary smartphone-like half; paired +0.016 [+0.008, +0.024]),
  0.69 (single matched telematics sensor). Correcting the rate mismatch barely changes the primary result; the
  transfer depends on the breadth (randomisation) of the sensor model. Reported in Results VII-E, Table IV
  (marked post-hoc), Limitations and Supplement S1; no primary number changed.
- Paper tightened back to 10 pages (Figs. 4-6 narrower, shorter "in brief" paragraph); RQ section now states the
  hypotheses H1-H3 that came from the September audit and that RQ4-RQ5 had no directional hypothesis.

## 2026-10-03 (revision v2, response to the independent review `review/first.md`)

- Froze `evaluation/PROTOCOL_V2.md` before any v2 experiment (only `experiments/v2/verify_review_claims.py`, which
  re-reads existing results, was run before). Classes: C1 (v1 confirmatory), R (pre-specified re-analysis of the
  already-seen routes), E (exploratory diagnostic), S (new controlled simulation). Added before running: V7/V8 enter
  the sensor factorial as a random half of their passes (seed 7) to match V1/V2 in size.
- `REVISION_PLAN_V2.md`: every review concern with evidence, validity, severity, fix and status.
- New simulator variants V7 (telematics-like + holder resonance) and V8 (phone-like, rigid):
  `sim_generate.py telecompliant phonerigid` (seeds 41001, 41002).
- New analyses (all in `experiments/v2/`, outputs in `results/v2/`): verify_review_claims, simreal_variants (R3/E1/E2),
  value_of_simulation (R4), inference_blocks (R6, ACF, variance components), speed_real (R5), real_baselines_v2
  (R2 unit-disjoint, R7 Bajic anchor, R8 passes needed), aran_rematch (R9), physics_inversion (R10, M7), spectra (E3),
  band_gain (E4), vehicle_sweep (S1).
- Implementation notes found while running (none depends on an outcome):
  - (segment, task, pass_id) is not unique in `units.csv` (12 duplicates: a ring-road pass can cover a segment in two
    progression runs). v2 aligns v1 pass predictions positionally (`common_v2.v1_pass_predictions`, label-checked).
  - `inference_blocks.py`: a column named `le` collided with the pandas method; renamed (crash, no wrong result).
  - `spectra.py`: (a) units shorter than one Welch window have NaN spectra and are now excluded from cell means
    (first run printed NaN summaries); (b) DEVIATION: the pre-specified aliasing check within TMU#10 is infeasible
    (TMU#10 logged 52.6 Hz only on M13 and 333 Hz only on CPH1/M3; no common segment). Replaced by TMU#12 on M3 (also
    no common segment x speed cell) and by an all-unit comparison on common cells, which is confounded with device and
    mounting differences; reported as such.
- v1 errors corrected in the paper text: comparator of "about 20 km" (it was the p79+iso set), "pre-registered"
  caption, "sampling rate matters most" (the holder resonance moves the bias more), the CNN deficit (one route), the
  breadth mechanism (contradicted by the variant factorial), "urban errors smaller than device disagreement" (the ARAN
  disagreement is driven by a 5 % heavy tail; removed).
- Bibliography: added Skar & Levenberg (2024) and Agebjar et al. (FUSION 2025), DOIs verified with Crossref.

## 2026-10-03 (revision v2, continued: addenda, story revision, documents)

- Protocol addenda written before running each analysis, after some v2 results were known (class E, reported in full,
  never used to choose anything; `evaluation/PROTOCOL_V2.md` Section 8):
  - E5 `value_of_simulation_variants.py`: equal-budget arms for V1-V8 (the V0-only conclusion depended on V0's
    accidental level). Result: equal-budget value is variant-dependent.
  - E6 `paired_vs_real.py`: draw-by-draw pairing of every simulation arm with real-only training (same sampler and
    draws); per-route version `paired_vs_real_by_route.csv`.
  - E7 `speed_scaling_sim.py`: simulated vibration scales with speed more steeply than the real car's (0.92-1.40 vs
    0.60/0.85).
  - E8 `speed_paired.py`: paired elasticity differences (5 km blocks); the urban-only nature of the speed result.
  - E9 `value_real_index.py`: real-only vibration index as a small-sample comparator; at 1 km, simulation over the
    same profiles is not better than it.
  - E10 `ranking_untrained.py` (during the final self-review): an untrained RMS/v^0.5 ranks segments within routes as
    well as any trained estimator (0.82 vs 0.83); the paper's headline moved from "ranking transfers" to the level.
- `band_gain.py by_class`: 10-15 Hz deficit by road class (larger on motorways for 9/9 variants).
- Fixes found while finishing:
  - `summarise_v2.py`: within-route correlations of constant predictors (M0, M0b) were floating-point noise (0.06,
    -0.01); now undefined. Table I shows "--".
  - `make_tables_v2.py`: per-route segment counts in a supplement caption had been typed by hand and were wrong; now
    generated from the data. Table captions generated, no hand-typed numbers left.
  - `make_tables.py` / `tables/table5_generalisation.tex` / `exp_sim_controlled.py` docstrings: "pre-registered" ->
    "fixed in advance" (missed in the first round).
  - Layout: overfull tables (value, controlled simulation), supplement float order (`placeins`), mid-column gaps
    (`\raggedbottom`, tightened text), figure legends (vehicle sweep).
- Figures: `v2_value` redesigned (all nine variants, both real-only comparators); `v2_variants` panel (a) shows the
  untrained ranking reference; `v2_vehicles` legend.
- Paper: results, discussion, supplement rewritten; abstract, introduction and conclusion revised around the level;
  claims narrowed per `CLAIM_AUDIT_V2.md`; cross-references between main paper and supplement via `xr-hyper`.
  References: Xing et al. 2025 re-described (includes a real-vehicle test), Skar & Levenberg 2024 re-described from
  its abstract and code; `REFERENCE_AUDIT.md` section D.
- Reproducibility: `environment_lock.txt` (pip list --format=freeze of `torch_gpu`), `run_all_experiments.py` extended
  with the 24 v2 steps (LaTeX now compiles supplement and main in turn), `make_final_results_v2.py` writes
  `results/v2/final_results_v2.{json,csv}` with the provenance of every headline number.
- Documents: `REVISION_PLAN_V2.md` (final statuses), `CLAIM_AUDIT_V2.md`, `REVIEWER_AUDIT_V2.md`,
  `FINAL_REPORT_V2.md`, `README.md`.
- Removed from the active paper: `paper/sections/rq.tex`, `paper/sections/protocol.tex` (identical copies remain in
  `paper/v1_archive/sections/`).

## 2026-10-10 / 2026-10-11 (revision v3, response to `INDEPENDENT_REVIEW_V3.md`)
- Checkpoint of the reviewed v2 state in `checkpoints/v2_2026-10-03/` (172 files, `MANIFEST.sha256`; README of the
  checkpoint in `CHECKPOINT.md`). Nothing committed to git (authors' decision).
- Verified the review's statements read-only before deciding (`IMPLEMENTATION_AUDIT_V3.md` §1), classified every
  recommendation A-E (§2).
- [protocol] Frozen `evaluation/PROTOCOL_V3.md` (2026-10-10 22:01 IST, SHA-256 994cd027...a415ccc6) before any v3
  analysis: items V3-1 to V3-11 with hypotheses H1, H3, H3b. Deviations in `evaluation/PROTOCOL_V3_DEVIATIONS.md`.
- New scripts `experiments/v3/*.py` (pooled_vs_real, calib_uncertainty, band_limited, level_and_bands, rank_paired,
  speed_robustness, nosim_index, pass_density, common_v3); outputs in `results/v3/`; logs in `logs/v3/`.
- V3-1 joint training reproduces the reviewer's c4 values identically (960 fold-draws); H1 holds. V3-3 reproduces the
  zero-shot MAEs exactly; H3 and H3b hold.
- V3-8 bug fix in `experiments/v2/physics_inversion.py`: road-spectrum segments are built from the real units'
  segment starts per route-direction (was: multiples of 100 m, which missed M13-VH). Reran `summarise_v2.py`,
  `make_numbers_v2.py` (38 M7 macros changed, nothing else), `make_tables_v2.py`.
- `make_tables_v2.py` captions: M7 subset notes removed; Table S10 "different reference survey and processing";
  Table S13 survey dates corrected from the dataset readme. `make_figures_v2.py` restored to the checkpoint version
  (a v3 figure had been prototyped in it) and rerun.
- New generators `make_numbers_v3.py` (paper/numbers_v3.tex, results/v3/paper_numbers_v3.json),
  `make_tables_v3.py` (tables/v3_*.tex, tables/v3s_*.tex), `make_figures_v3.py` (figures/v3_*),
  `make_final_results_v3.py` (results/v3/final_results_v3.*), `evaluation/verify_v3.py` (25 independent checks,
  results/v3/verification_v3.json). `run_all_experiments.py` gained the v3 steps.
- References: Nitsche 2014, Ngwangwa 2014, Wu 2023, Jeong & Jo 2024, Peng 2018, Chebotar 2019 added by DOI
  (`references/build_bib.py`); claim checks in `references/REFERENCE_AUDIT.md` §E.
- Paper rewritten from abstract to conclusion around the v3 findings (joint training, two sources of the level error,
  band-limited retraining, pass density, qualified ranking claim, metric labels, k-km definition); Sec. V-F, Table IV
  and Figs. 5-6 moved to the supplement; main paper 10 pages, supplement 19 pages.
- Corrections found during the final verification: "two to fourteen months" -> "two to fifteen months" (CPH6 drives
  14.8 months after its survey); the method no longer says the joint arm was unreported before (the first version
  reported it); Table S26 caption no longer says the CV control "over-adjusts"; "the variants whose vibration matched
  the car worst" -> "the variants with the largest vibration deficit at 10-15 Hz" (by the overall RMS ratio V4 matches
  worst); Nitsche's "without varying speed" attributed to Bajic et al. in the text.

## 2026-10-11 (final corrections, response to the final verification audit `review/final_audit/audit.md`)

No experiment was rerun, no protocol, split, metric or result changed. Checkpoint of the audited state:
`checkpoints/v3_2026-10-11/` (170 files, `MANIFEST.sha256`). The audit report itself is unchanged.

- Ranking claim (audit B1). Discussion said the untrained RMS/v^0.5 comes within 0.05 "of every trained estimator we
  tested"; false for M2c (-0.099 on CPH1), LightGBM without speed inputs (-0.176 on M13) and the speed-only model
  (-0.723 on M3). Narrowed to real-trained LightGBM, MLP, CNN, M7 and simulation-trained LightGBM V0-V8 (largest
  difference 0.044), with the three exceptions named. The per-route values for V2-V8, MLP, CNN, M7 and the exceptions
  existed in `results/v2/variants_zeroshot.csv` and `summary_real_estimators.csv` but were not printed; new read-only
  script `experiments/v3/rank_scope.py` -> `results/v3/rank_scope.csv` (asserts agreement with `rank_paired.csv`),
  new bottom panel of Table S5 (point estimates), new macros `rkScopeAbsMax`, `rkScopeVarAbsMax`, `rkIdxGapMax`,
  `rkNoSpeedGapMax`, `rkSpeedOnlyGapMax`. Edited: discussion.tex, results.tex (Sec. V-B), supplement S1 (iv) and the
  S4 text.
- LightGBM configuration (B2). Method said the configuration is chosen by inner leave-one-route-out validation "when
  real training routes are available"; the code does so only for LightGBM trained on whole real training routes (M1,
  M3, unit-disjoint check). Sentence now states that every other LightGBM (simulation-trained, real-only k-km
  comparator, joint training) uses the first configuration. Implementation unchanged.
- Code availability (B3). Intro said code, protocols, configurations and predictions "are provided with the paper";
  nothing is public (`research_rescue/` is not tracked in git, no archive). Now: "We will release ... with the
  published version of the paper." Method and supplement S1 now state that the protocols were frozen as dated files in
  the working copy, not registered publicly; supplement S8 says the files are not yet public.
- Class level (B4). Table II caption said the class level is the mean over the segments of a road class; the values
  are the mean of the two route levels. Caption fixed in `make_tables_v3.py` (also the Table S24 caption), Method
  defines the class level, Fig. 2b caption says the same. No value changed.
- Speed (B5). Sec. V-E's closing sentence ("Simulation thus removes part of the over-correction ...") contradicted the
  speed-CV robustness row reported two sentences earlier; now says the urban advantage holds in the main design and
  with the unit and speed-SD controls but not with the speed-CV control, so it is not established. Discussion speed
  paragraph carries the same caveat (CV control flips the difference; with the speed-SD control the real-trained
  urban elasticity's interval includes zero). Interval labels: Sec. V-E states that single elasticities use 1 km
  blocks and paired differences / robustness rows 5 km blocks; Method states that intervals use 5 km blocks except the
  single-estimator speed elasticities and the spectra (1 km).
- Related work (audit E5). Ngwangwa et al. 2014 checked in the accepted manuscript (University of Pretoria repository):
  training responses simulated by a full model of the Land Rover over slightly modified measured profiles, network
  tested on that vehicle's measured responses; text now says so. Nitsche et al. 2014: the abstract (AIT repository)
  confirms simulated-response training, probe-vehicle validation and the wLP target, but not the measured profile, the
  profilometer reference or the speed condition, which are now attributed to Bajic et al. (whose full text states
  them). `references/REFERENCE_AUDIT.md` section F.
- Venue (audit E4). No target venue is specified anywhere in the repository; venue-dependent formatting left as is.
  The corrections lengthen the main paper from 10 to 11 pages (references run half a column onto page 11); the
  supplement reflowed from 19 to 18 pages.
- Pipeline: `run_all_experiments.py` steps `v3_rank_scope` and `final_verify`; new `evaluation/verify_final.py`
  (14 checks -> `results/v3/verification_final.json`); supplement S8 command list includes `v3_rank_scope`.
- Display: values that round to zero print as +0.000 in the new Table S5 panel.
