# Review V3 checks (read-only)

Supporting analyses for `research_rescue/INDEPENDENT_REVIEW_V3.md`. Every script only reads existing data, results
and code paths of `research_rescue/`; outputs are written to `outputs/` in this folder. Nothing outside this folder
was created or modified. Environment: conda `torch_gpu` (see `research_rescue/README.md`). Run from any directory:
`python -I <script> <path to research_rescue> [...]`.

| Script | Question | Sanity check against the paper | Runtime |
|---|---|---|---|
| `c1_band_vs_bias.py <rr>/results/v2` | Does the zero-shot bias track the 10-15 Hz ratio specifically or broadband gain? | Spearman 0.967 / 0.217 / 0.250 (paper 0.97 / 0.22 / 0.25) | seconds |
| `c1b_levels.py <rr>/results/v2` | Per-route log levels; band association in log terms | V0 levels from `variants_zeroshot.csv` | seconds |
| `c2_minimal_calibration.py <rr>` | Is the simulator's value reducible to a slope? (no-simulator index arms on the paper's draws) | V0 + level 0.425, real-only 0.678, real index 0.722, sim index + level 0.516 | ~20 s |
| `c3_rank_paired.py <rr>` | Paired within-route Spearman, trained vs untrained RMS/v^0.5, 5 km / 1 km block bootstrap | point Spearman values of Table S4 | ~10 min |
| `c4_pooled_sim_real.py <rr> <out.csv> V1,V5,V0,V3` | v1 pre-specified pooled sim+real LightGBM arm on the paper's 20 draws | (new arm) | ~9 min |
| `c4b_compare.py <rr> outputs/c4_pooled_sim_real.csv` | Pairs the pooled arm with the paper's real-only, level and affine arms | real-only 0.678 / 0.523 / 0.461 | seconds |
| `c5_m7_subset.py <rr>` | Which M13 segments M7 is evaluated on, and whether the subset matters | M7 M13 MAE 0.169 | seconds |
| `c6_speed_robustness.py <rr>` | Fixed-road speed elasticities with unit fixed effects and dynamics controls | 0.602 / 0.847 / +0.117 (paper 0.60 / 0.85 / +0.12) | ~1 min |
| `c7_macros.py <rr>/paper <macro,list>` | Macro resolution; undefined number macros | abstract values | seconds |
| `c8_band_limited.py <rr> <out.csv>` | Band-limited (< 10 Hz) zero-shot intervention for V0-V8 | "full" set reproduces Table II MAEs exactly | ~4 min |
