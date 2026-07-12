"""
config.py — Global configuration and ablation definitions for the IRI v3 ablation study.

Ablation sequence (each run CASCADES from the previous):
  Run 1: Full Model      — Exact replica of model_4.ipynb
  Run 2: Remove PICA     — Disable Post-Training Isotonic Calibration
  Run 3: Remove AsymLoss — Revert to standard Huber loss
  Run 4: Remove KinNorm  — Remove physics-based speed normalisation of az
  Run 5: Remove 2D Samp  — Remove 2D frequency sample weighting (uniform weights)
"""

import os

# ---------------------------------------------------------------------------
# Paths  (update BASE_DATA_DIR to match your local filesystem)
# ---------------------------------------------------------------------------
BASE_DATA_DIR = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model_work\data\simulation\data\IRI_new_experiments"

# Source pre-built dataset produced by model_4.ipynb (avoids re-processing)
SOURCE_DATA_NPZ = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model\iri_v2\output\iri_v2_data.npz"

# Root of this ablation study
V3_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(V3_ROOT, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Spatial / windowing constants (identical to model_4)
# ---------------------------------------------------------------------------
WINDOW_SIZE_M     = 100.0
STEP_SIZE_M       = 10.0
FINAL_SPATIAL_STEPS = 400          # 0.25 m per spatial step
MIN_SPEED_MS      = 1.0
AUGMENT_HZ        = [10, 15, 20, 25, 30, 50]
RAW_FEATURES      = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
SPLITS = {
    'train': ['east_coast_usa', 'west_coast_usa'],
    'val':   ['automation_test_track_trip_1'],
    'test':  ['automation_test_track_trip_2', 'automation_test_track_trip_3'],
}

# ---------------------------------------------------------------------------
# Training hyper-parameters (identical to model_4)
# ---------------------------------------------------------------------------
EPOCHS     = 150
BATCH_SIZE = 64
LR_INITIAL = 1e-3
ES_PATIENCE  = 15
LR_PATIENCE  = 5
LR_FACTOR    = 0.5

# ---------------------------------------------------------------------------
# Ablation run definitions
# Each dict is a *delta* from the previous run (cascade model).
# Flags that remain True mean the feature is ACTIVE.
# ---------------------------------------------------------------------------
ABLATION_RUNS = [
    {
        "run_id": 1,
        "label":  "Run 1 — Full Model",
        "use_pica":        True,   # Post-Training Isotonic Calibration
        "use_asym_loss":   True,   # Custom Asymmetric Huber loss
        "use_kinetic_norm":True,   # Physics-based az speed normalisation
        "use_2d_sampling": True,   # 2-D frequency sample weighting
    },
    {
        "run_id": 2,
        "label":  "Run 2 — w/o PICA",
        "use_pica":        False,
        "use_asym_loss":   True,
        "use_kinetic_norm":True,
        "use_2d_sampling": True,
    },
    {
        "run_id": 3,
        "label":  "Run 3 — w/o PICA + w/o AsymLoss",
        "use_pica":        False,
        "use_asym_loss":   False,
        "use_kinetic_norm":True,
        "use_2d_sampling": True,
    },
    {
        "run_id": 4,
        "label":  "Run 4 — w/o PICA + w/o AsymLoss + w/o KinNorm",
        "use_pica":        False,
        "use_asym_loss":   False,
        "use_kinetic_norm":False,
        "use_2d_sampling": True,
    },
    {
        "run_id": 5,
        "label":  "Run 5 — w/o PICA + w/o AsymLoss + w/o KinNorm + w/o 2DSamp",
        "use_pica":        False,
        "use_asym_loss":   False,
        "use_kinetic_norm":False,
        "use_2d_sampling": False,
    },
]
