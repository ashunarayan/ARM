# Research-rescue plan (as executed)

## Starting point
`BASELINE_STATE.md` (state of the rejected paper and its code) and the September-2026 audit, whose findings
F1-F7 were treated as hypotheses and re-checked (`audit/`).

## Research questions (fixed before running models)
* **RQ1 - label validity.** Is the IRI implementation correct, and does the legacy BeamNG label pipeline
  (curvature-adaptive "mesh correction") produce IRI? -> validation against an independent profilometer (P79,
  LiRA-CD) and application of the legacy correction to real roads.
* **RQ2 - evaluation validity.** How much of the rejected paper's performance survives a leakage-free protocol?
  -> legacy recipe re-implemented and evaluated with the legacy split vs. leave-one-map-out (BeamNG).
* **RQ3 - shortcuts.** How much apparent skill is explained by speed? -> speed-only baselines in BeamNG, LiRA-CD
  and PVS; models with/without speed inputs.
* **RQ4 - real-world accuracy and simple baselines.** On real cars with profilometer-referenced IRI (LiRA-CD,
  route-disjoint), how do physics indices, gradient boosting, MLP and the CNN compare?
* **RQ5 - value of simulation.** Does a model trained only on physically simulated responses to measured road
  profiles transfer to real cars, and how much real labelled data does simulation replace?
* **RQ6 - controlled properties.** Speed invariance, unseen-vehicle generalisation and sensor robustness, tested
  in a controlled parametric simulator with pre-registered criteria.

## Execution order
1. Snapshot + re-run audits (`BASELINE_STATE.md`, `audit/`).
2. Download LiRA-CD (CC BY 4.0) programmatically; IRI implementation validation (`evaluation/iri_unit_test.py`).
3. Freeze `evaluation/FINAL_EVALUATION_PROTOCOL.md` and `config/models.json` (before any test evaluation).
4. Clean BeamNG dataset + experiments S1/S2/S3 + legacy recipe (`experiments/beamng_build_dataset.py`, `exp_beamng.py`).
5. Parametric simulator + sensor model + unit tests (`common/vehsim.py`, `common/sensor.py`, `evaluation/sim_unit_test.py`).
6. Simulated datasets (`experiments/sim_generate.py`).
7. LiRA-CD dataset (`experiments/lira_build_dataset.py`) and experiments: ladder, simulator gap, zero-shot, few-shot
   (`experiments/exp_lira.py`).
8. Controlled simulation experiments (`experiments/exp_sim_controlled.py`).
9. PVS ordinal analysis (`experiments/exp_pvs.py`).
10. Reference audit (`references/`), figures/tables (`make_figures.py`, `make_tables.py`), final results JSON/CSV.
11. Paper rewrite around the evidence (`paper/`), adversarial reviewer audit (`REVIEWER_AUDIT.md`), iterate.

## Compute allocation (decided up front)
* Neural models: 5 seeds; few-shot CNN: 3 seeds at k in {1, 5, 20, all} km (compute); GBM/physics: full k grid.
* No hyper-parameter search beyond the 6-configuration budget in `config/models.json`.
* BeamNG re-collection with a fixed acquisition pipeline was **not** attempted (requires the interactive BeamNG
  application and GPU rendering on the user's machine; the parametric simulator replaces it for controlled tests).
