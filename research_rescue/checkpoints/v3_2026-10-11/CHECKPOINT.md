# Checkpoint: revision v3 as audited in `review/final_audit/audit.md`

Snapshot taken 2026-10-11, before any change made in response to the final verification audit. It is the state of
`research_rescue/` that the audit inspected (paper compiled 2026-10-11 08:25). Nothing in this folder is used by the
pipeline; it exists so that the audited version can be compared with the corrected submission version.

Contents (copies, not links): `paper/` (LaTeX sources, macros `numbers.tex` / `numbers_v2.tex` / `numbers_v3.tex`,
compiled `main.pdf` and `supplementary.pdf`; `v1_archive/` omitted), `tables/`, `figures/`, `results/v3/`,
`experiments/v3/`, the v2/v3 generator scripts (`make_*_v2.py`, `make_*_v3.py`, `run_all_experiments.py`),
`evaluation/PROTOCOL_V3.md`, `PROTOCOL_V3_DEVIATIONS.md`, `verify_v3.py`, the v3 documents and the audit report
(`review/final_audit/`). `MANIFEST.sha256` lists the SHA-256 of every file (check with `sha256sum -c MANIFEST.sha256`
from this folder).
