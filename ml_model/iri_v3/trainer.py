"""
trainer.py — Training utilities, sample weighting, and TFLite export.

Extracted verbatim from model_4.ipynb (Cell 4).
Parameterised for the 2-D sample-weighting ablation (Run 5).
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.callbacks import (
    EarlyStopping, ReduceLROnPlateau, ModelCheckpoint,
)

from config import (
    OUTPUT_DIR, EPOCHS, BATCH_SIZE,
    LR_PATIENCE, LR_FACTOR, ES_PATIENCE,
)
from model import build_iri_model


# ---------------------------------------------------------------------------
# Sample Weighting  (identical to model_4)
# ---------------------------------------------------------------------------

def compute_2d_sample_weights(speeds, iris, num_speed_bins=10, num_iri_bins=10):
    """
    Computes Inverse Frequency Sample Weights based on a 2D (speed, IRI) grid
    to prevent spurious correlations between vehicle velocity and road roughness.
    """
    speed_bins = np.linspace(np.min(speeds), np.max(speeds), num_speed_bins + 1)
    iri_bins   = np.linspace(np.min(iris),   np.max(iris),   num_iri_bins   + 1)

    speed_idx = np.clip(np.digitize(speeds, speed_bins) - 1, 0, num_speed_bins - 1)
    iri_idx   = np.clip(np.digitize(iris,   iri_bins)   - 1, 0, num_iri_bins   - 1)

    H, _, _ = np.histogram2d(speeds, iris, bins=[speed_bins, iri_bins])
    weights  = np.zeros(len(speeds), dtype=np.float32)

    for i in range(len(speeds)):
        count = H[speed_idx[i], iri_idx[i]]
        if count > 0:
            weights[i] = 1.0 / count

    weights    = weights / np.mean(weights)
    weight_cap = np.percentile(weights, 99)
    weights    = np.clip(weights, 0, weight_cap)
    return weights / np.mean(weights)


# ---------------------------------------------------------------------------
# TFLite Export  (identical to model_4)
# ---------------------------------------------------------------------------

def export_to_tflite(trained_model, output_filename):
    """Exports a Keras model to TFLite (dynamic-range quantisation)."""
    print(f"\n[*] Exporting to TFLite: {output_filename} ...")
    converter = tf.lite.TFLiteConverter.from_keras_model(trained_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    with open(output_filename, 'wb') as f:
        f.write(tflite_model)
    print(f"[*] TFLite model saved. Size: {len(tflite_model) / 1024:.1f} KB")


# ---------------------------------------------------------------------------
# Main Training Pipeline
# ---------------------------------------------------------------------------

def train(
    run_id,
    X_train_raw, X_train_ctx, y_train,
    X_val_raw,   X_val_ctx,   y_val,
    use_asym_loss   = True,
    use_2d_sampling = True,
):
    """
    Full training pipeline for one ablation run.

    Returns the trained Keras model and its training history DataFrame.
    """
    run_output_dir = os.path.join(OUTPUT_DIR, f"run_{run_id:02d}")
    os.makedirs(run_output_dir, exist_ok=True)

    # ---- Random oversampling of high-severity samples (IRI > 10) ----------
    severe_idx   = np.where(y_train > 10.0)[0]
    X_train_raw  = np.concatenate([X_train_raw, X_train_raw[severe_idx]])
    X_train_ctx  = np.concatenate([X_train_ctx, X_train_ctx[severe_idx]])
    y_train      = np.concatenate([y_train,     y_train[severe_idx]])

    # ---- Ablation point: 2-D sample weighting vs. uniform -----------------
    if use_2d_sampling:
        train_speeds   = X_train_ctx[:, 0]  # speed_mean is feature 0
        sample_weights = compute_2d_sample_weights(train_speeds, y_train)
    else:
        sample_weights = np.ones(len(y_train), dtype=np.float32)
    # -----------------------------------------------------------------------

    # log1p target transformation (identical to model_4)
    y_train_log = np.log1p(y_train)
    y_val_log   = np.log1p(y_val)

    model = build_iri_model(use_asym_loss=use_asym_loss)

    best_model_path = os.path.join(run_output_dir, 'best_model.keras')
    callbacks = [
        EarlyStopping(
            monitor='val_loss', patience=ES_PATIENCE,
            restore_best_weights=True, verbose=1,
        ),
        ReduceLROnPlateau(
            monitor='val_loss', factor=LR_FACTOR,
            patience=LR_PATIENCE, verbose=1,
        ),
        ModelCheckpoint(
            best_model_path, monitor='val_loss',
            save_best_only=True, verbose=1,
        ),
    ]

    print(f"\n[*] Training Run {run_id} ...")
    history = model.fit(
        x=[X_train_raw, X_train_ctx],
        y=y_train_log,
        sample_weight=sample_weights,
        validation_data=([X_val_raw, X_val_ctx], y_val_log),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
    )

    hist_df = pd.DataFrame(history.history)
    hist_df.to_csv(
        os.path.join(run_output_dir, 'training_history.csv'), index=False
    )

    # TFLite export
    tflite_path = os.path.join(run_output_dir, 'model.tflite')
    export_to_tflite(model, tflite_path)

    return model, hist_df
