"""
evaluate.py — Test-set evaluation and Post-Training Isotonic Calibration (PICA).

Extracted verbatim from model_4.ipynb (Cells 5 & 6).
Parameterised so the calibration step can be skipped (Run 2 ablation).
"""

import json
import os
import numpy as np
from scipy.stats import pearsonr
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config import OUTPUT_DIR


# ---------------------------------------------------------------------------
# Core Metric Calculation
# ---------------------------------------------------------------------------

def compute_metrics(y_true, y_pred):
    """
    Returns a dict with MAE, RMSE, R2, and Pearson r.

    Predictions beyond 40 m/km are treated as garbage and discarded
    (mirrors the filtering logic in model_4 Cell 6).
    """
    mask   = y_pred < 40.0
    n_yeeted = np.sum(~mask)
    if n_yeeted > 0:
        print(f"\n[!] Discarding {n_yeeted} predictions >= 40 m/km.")

    y_true_f = y_true[mask]
    y_pred_f = y_pred[mask]

    mae  = mean_absolute_error(y_true_f, y_pred_f)
    rmse = float(np.sqrt(mean_squared_error(y_true_f, y_pred_f)))
    r2   = r2_score(y_true_f, y_pred_f)
    pr, _= pearsonr(y_true_f, y_pred_f)

    return {
        "MAE":       float(mae),
        "RMSE":      float(rmse),
        "R2":        float(r2),
        "Pearson_r": float(pr),
    }


# ---------------------------------------------------------------------------
# PICA  (Post-Training Isotonic Calibration)
# ---------------------------------------------------------------------------

def run_pica(model, X_val_raw, X_val_ctx, y_val, run_output_dir):
    """
    Fits an IsotonicRegression calibrator on the validation set, serialises it
    as a JSON lookup table, and returns it.
    """
    val_preds_log = model.predict([X_val_raw, X_val_ctx]).flatten()
    val_preds     = np.expm1(val_preds_log)

    iso_reg = IsotonicRegression(out_of_bounds='clip')
    iso_reg.fit(val_preds, y_val)

    lut = {
        "x_raw":        iso_reg.X_thresholds_.tolist(),
        "y_calibrated": iso_reg.y_thresholds_.tolist(),
    }
    lut_path = os.path.join(run_output_dir, "calibration_lut.json")
    with open(lut_path, "w") as f:
        json.dump(lut, f)

    cal_val_preds = iso_reg.predict(val_preds)
    val_mae       = mean_absolute_error(y_val, cal_val_preds)
    print(f"[*] PICA fitted. Val MAE after calibration: {val_mae:.3f}")

    return iso_reg


# ---------------------------------------------------------------------------
# Full Evaluation Pipeline
# ---------------------------------------------------------------------------

def evaluate(
    run_id,
    model,
    X_val_raw, X_val_ctx, y_val,
    X_test_raw, X_test_ctx, y_test,
    use_pica=True,
):
    """
    Evaluates the model on the test set.

    If `use_pica=True` the isotonic calibrator is applied after obtaining
    raw predictions; otherwise raw predictions are used directly.

    Returns a dict of final metrics.
    """
    run_output_dir = os.path.join(OUTPUT_DIR, f"run_{run_id:02d}")
    os.makedirs(run_output_dir, exist_ok=True)

    print(f"\n[*] Evaluating Run {run_id} ...")

    # Raw predictions (log space → original IRI space)
    test_preds_log = model.predict([X_test_raw, X_test_ctx]).flatten()
    test_preds_raw = np.expm1(test_preds_log)

    if use_pica:
        print("[*] Applying Post-Training Isotonic Calibration (PICA) ...")
        iso_reg     = run_pica(model, X_val_raw, X_val_ctx, y_val, run_output_dir)
        test_preds  = iso_reg.predict(test_preds_raw)
    else:
        print("[*] PICA disabled — using raw predictions.")
        test_preds  = test_preds_raw

    metrics = compute_metrics(y_test, test_preds)

    # Print publication-style block
    print(
        "\n==============================\n"
        "      PUBLICATION METRICS      \n"
        "=============================="
    )
    print(f"Mean Absolute Error:     {metrics['MAE']:.4f} m/km")
    print(f"Root Mean Squared Error: {metrics['RMSE']:.4f} m/km")
    print(f"R-squared (R2 Score):    {metrics['R2']:.4f}")
    print(f"Pearson Correlation (r): {metrics['Pearson_r']:.4f}")

    return metrics
