# Scripts of the final verification audit (2026-10-11)

Copies of the read-only scripts behind `../audit.md`, kept as a record. They were written for a session scratchpad:
paths to the repository are absolute (`d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue`), and `a06`/`a07` read
`a02_segpred.pkl` / `a02_table.csv`, which `a02_saved_preds.py` writes next to itself. Run with the `torch_gpu`
environment, e.g. `python -I a02_saved_preds.py`. `a04_out.txt` is the output of the retraining script.

| Script | What it checks |
|---|---|
| `a01_macros.py` | resolves every macro used in the main paper; duplicate definitions; control characters |
| `a02_saved_preds.py` | Table I, zero-shot variants, class levels, per-route ranking, 5 km-block intervals, residual ACF, from saved predictions |
| `a03_calib.py` | real-only k = 5/20 retrained; level offset and joint training at 5/20 km; test-route intervals |
| `a04_retrain.py` | M3 with inner selection, V0 zero-shot, joint training V0/V5, band-limited retraining, pass density with an independent RNG |
| `a05_crossref.py` | every DOI of the bibliography against Crossref (network) |
| `a06_small.py` | class-level definition, 10-15 Hz ranking, telematics units, label check, speed elasticities |
| `a07_sensitivity.py` | real-only comparator under all six LightGBM configurations (argument `a`); per-route and secondary traces |

The checks that the corrected paper depends on are re-implemented in `evaluation/verify_final.py`, which uses
relative paths and runs in the pipeline (`run_all_experiments.py --only final_verify`).
