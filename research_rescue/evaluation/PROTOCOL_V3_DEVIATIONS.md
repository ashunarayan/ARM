# Deviations from `PROTOCOL_V3.md` (section 4 of the protocol)

`PROTOCOL_V3.md` is kept byte-identical to its frozen version (SHA-256
994cd02729a8bf3b4ec3040bedc2b83bc7647227772b56f87eca7831a415ccc6, checked by `evaluation/verify_v3.py`), so the
deviations its section 4 asks to record are listed here. Dated 2026-10-11. Each deviation is also stated in
Supplement S1 of the paper where it affects a reported number.

| # | Item | What the protocol says | What was done | When decided | Effect on reported results |
|---|---|---|---|---|---|
| 1 | V3-9 | three no-simulator arms (alpha_car affine; alpha = 0.5 with offset and with affine) | additionally the three-parameter index fitted to V0 simulated units with a level offset (`simidx_level`), ported with the reviewer's script | before the run (part of the ported script) | none: a reference row that reproduces a v2 result (Table S15: 0.52 m/km at 5 km); no claim uses it |
| 2 | V3-4 | associations with the zero-shot bias and the mean log level | additionally with the motorway-minus-urban level difference (`target = spread` in `results/v3/band_associations.csv`) | before the run | none: kept in the result file, not reported in the paper |
| 3 | V3-1 / L1 | the review asked for an addendum to `PROTOCOL_V2.md` section 8 | the arm was specified as item V3-1 of a new protocol frozen before any v3 analysis | before the run | none |

Not deviations, recorded for transparency:

* **Implementation corrections before `make_numbers_v3.py` was first run.** V3-11 was first coded as the mean of the
  two routes' relative errors; it was changed to the protocol's definition (MAE over the class's segments divided by
  their mean IRI). The spread ratios of V3-3 were first coded from macro values rounded to two decimals (which would
  have printed the urban ratio as 47 % instead of 49 %); they are computed from the unrounded spreads, and the
  hypothesis check H3 uses unrounded values in both `make_numbers_v3.py` and `verify_v3.py`.
* **Presentation only.** Equal-ended ranges ("20--20") are printed as a single value.
* **Reproduction checks.** V3-1: the 960 fold-draw results that overlap the reviewer's check c4 are identical; the
  protocol's tolerance (0.002 m/km on the rounded c4b summary) is met with a largest difference of 0.0005 (rounding).
  V3-3: the full-feature retraining reproduces the zero-shot MAEs and the MAEs after a 5 km offset of
  `summary_variants.csv` / `variants_calibration.csv` exactly.
* **Outcomes of the pre-registered hypotheses.** H1 holds (for V0-V8 and with V10). H3 holds (mean, urban and motorway
  spreads 32 %, 49 % and 34 % of the full-feature spreads; largest change from dropping 10-15 Hz 2 %). H3b holds
  (V4 +0.22 against +0.02 to +0.10).
