"""
run_ablation.py — Main entry point for the IRI v3 sequential ablation study.

Usage:
    python run_ablation.py [--rebuild-data]

Flags:
    --rebuild-data   Force re-processing of raw trip CSVs even if a cached
                     dataset already exists.  By default the script will use
                     the pre-built .npz from iri_v2/output if available.

Ablation sequence (each run cascades from the previous):
    Run 1: Full Model                           (PICA + AsymLoss + KinNorm + 2DSamp)
    Run 2: Remove PICA                          (        AsymLoss + KinNorm + 2DSamp)
    Run 3: Remove Asymmetric Loss               (                   KinNorm + 2DSamp)
    Run 4: Remove Kinetic Normalisation                           (           2DSamp)
    Run 5: Remove 2-D Sampling                  (baseline: all ablated)
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import tensorflow as tf

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from config import (
    ABLATION_RUNS, OUTPUT_DIR, SOURCE_DATA_NPZ,
    BASE_DATA_DIR,
)
from data_pipeline import build_datasets
from trainer import train
from evaluate import evaluate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_or_build_dataset(use_kinetic_norm, rebuild=False):
    """
    Load the pre-built .npz produced by model_4.ipynb (fastest path) or
    re-run the full spatial-resampling pipeline.

    NOTE: The kinetic-norm toggle only affects Run 4 & 5, where a rebuild
    is mandatory because the normalisation is baked into the raw arrays.
    The first three runs all use kinetic_norm=True and can share the same
    cached arrays.
    """
    cache_path = os.path.join(OUTPUT_DIR, "ablation_data.npz")

    # Decide whether we can reuse the existing cache
    if (
        not rebuild
        and use_kinetic_norm
        and os.path.exists(SOURCE_DATA_NPZ)
    ):
        print(f"[*] Loading pre-built dataset from: {SOURCE_DATA_NPZ}")
        with np.load(SOURCE_DATA_NPZ) as d:
            data = {
                'train': {
                    'raw': d['x_train_raw'], 'ctx': d['x_train_ctx'], 'y': d['y_train']
                },
                'val': {
                    'raw': d['x_val_raw'], 'ctx': d['x_val_ctx'], 'y': d['y_val']
                },
                'test': {
                    'raw': d['x_test_raw'], 'ctx': d['x_test_ctx'], 'y': d['y_test']
                },
            }
        return data

    # Check if our own cached (possibly without kinetic norm) exists
    norm_suffix = "with_kn" if use_kinetic_norm else "without_kn"
    run_cache   = os.path.join(OUTPUT_DIR, f"ablation_data_{norm_suffix}.npz")

    if not rebuild and os.path.exists(run_cache):
        print(f"[*] Loading cached dataset ({norm_suffix}) from: {run_cache}")
        with np.load(run_cache) as d:
            data = {
                'train': {'raw': d['x_train_raw'], 'ctx': d['x_train_ctx'], 'y': d['y_train']},
                'val':   {'raw': d['x_val_raw'],   'ctx': d['x_val_ctx'],   'y': d['y_val']},
                'test':  {'raw': d['x_test_raw'],  'ctx': d['x_test_ctx'],  'y': d['y_test']},
            }
        return data

    # Full rebuild
    if not os.path.exists(BASE_DATA_DIR):
        print(
            f"\n[!] ERROR: BASE_DATA_DIR not found: {BASE_DATA_DIR}\n"
            "    Please update config.py or provide SOURCE_DATA_NPZ."
        )
        sys.exit(1)

    print(f"[*] Building dataset (kinetic_norm={use_kinetic_norm}) from raw CSVs ...")
    data = build_datasets(use_kinetic_norm=use_kinetic_norm)

    np.savez_compressed(
        run_cache,
        x_train_raw=data['train']['raw'], x_train_ctx=data['train']['ctx'],
        y_train=data['train']['y'],
        x_val_raw=data['val']['raw'],     x_val_ctx=data['val']['ctx'],
        y_val=data['val']['y'],
        x_test_raw=data['test']['raw'],   x_test_ctx=data['test']['ctx'],
        y_test=data['test']['y'],
    )
    print(f"[*] Dataset cached to: {run_cache}")
    return data


def _print_markdown_table(results_list):
    """Print a formatted Markdown table to stdout."""
    header = "| Model State | MAE | RMSE | R2 | Pearson r |"
    sep    = "|---|---|---|---|---|"
    print("\n" + "=" * 70)
    print("  ABLATION STUDY — FINAL RESULTS")
    print("=" * 70)
    print(header)
    print(sep)
    for r in results_list:
        print(
            f"| {r['label']} "
            f"| {r['metrics']['MAE']:.4f} "
            f"| {r['metrics']['RMSE']:.4f} "
            f"| {r['metrics']['R2']:.4f} "
            f"| {r['metrics']['Pearson_r']:.4f} |"
        )
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="IRI v3 Sequential Ablation Study"
    )
    parser.add_argument(
        "--rebuild-data", action="store_true",
        help="Force re-build of training data from raw CSVs."
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\n" + "=" * 70)
    print("  IRI v3 — SEQUENTIAL ABLATION STUDY")
    print("  TensorFlow:", tf.__version__)
    print("=" * 70 + "\n")

    # Track which dataset variant is currently loaded to avoid redundant I/O
    _cached_data_kn = None    # kinetic_norm=True  data
    _cached_data_no_kn = None # kinetic_norm=False data

    all_results = []
    total_start = time.time()

    for cfg in ABLATION_RUNS:
        run_id  = cfg["run_id"]
        label   = cfg["label"]
        use_pica         = cfg["use_pica"]
        use_asym_loss    = cfg["use_asym_loss"]
        use_kinetic_norm = cfg["use_kinetic_norm"]
        use_2d_sampling  = cfg["use_2d_sampling"]

        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"  PICA={use_pica}  |  AsymLoss={use_asym_loss}  |  "
              f"KinNorm={use_kinetic_norm}  |  2DSamp={use_2d_sampling}")
        print(f"{'='*70}")

        run_start = time.time()

        # -- Load the appropriate dataset variant ----------------------------
        if use_kinetic_norm:
            if _cached_data_kn is None:
                _cached_data_kn = _load_or_build_dataset(
                    use_kinetic_norm=True, rebuild=args.rebuild_data
                )
            data = _cached_data_kn
        else:
            if _cached_data_no_kn is None:
                _cached_data_no_kn = _load_or_build_dataset(
                    use_kinetic_norm=False, rebuild=args.rebuild_data
                )
            data = _cached_data_no_kn

        X_train_raw = data['train']['raw']
        X_train_ctx = data['train']['ctx']
        y_train     = data['train']['y']
        X_val_raw   = data['val']['raw']
        X_val_ctx   = data['val']['ctx']
        y_val       = data['val']['y']
        X_test_raw  = data['test']['raw']
        X_test_ctx  = data['test']['ctx']
        y_test      = data['test']['y']

        # -- Train ----------------------------------------------------------
        model, _ = train(
            run_id=run_id,
            X_train_raw=X_train_raw, X_train_ctx=X_train_ctx, y_train=y_train,
            X_val_raw=X_val_raw,     X_val_ctx=X_val_ctx,     y_val=y_val,
            use_asym_loss=use_asym_loss,
            use_2d_sampling=use_2d_sampling,
        )

        # -- Evaluate -------------------------------------------------------
        metrics = evaluate(
            run_id=run_id,
            model=model,
            X_val_raw=X_val_raw,   X_val_ctx=X_val_ctx,   y_val=y_val,
            X_test_raw=X_test_raw, X_test_ctx=X_test_ctx, y_test=y_test,
            use_pica=use_pica,
        )

        # -- Persist metrics ------------------------------------------------
        run_output_dir = os.path.join(OUTPUT_DIR, f"run_{run_id:02d}")
        os.makedirs(run_output_dir, exist_ok=True)

        # JSON
        metrics_payload = {
            "run_id":           run_id,
            "label":            label,
            "use_pica":         use_pica,
            "use_asym_loss":    use_asym_loss,
            "use_kinetic_norm": use_kinetic_norm,
            "use_2d_sampling":  use_2d_sampling,
            **metrics,
        }
        json_path = os.path.join(run_output_dir, "test_metrics.json")
        with open(json_path, "w") as f:
            json.dump(metrics_payload, f, indent=2)

        # CSV
        pd.DataFrame([metrics_payload]).to_csv(
            os.path.join(run_output_dir, "test_metrics.csv"), index=False
        )

        elapsed = time.time() - run_start
        print(f"[*] Run {run_id} completed in {elapsed:.1f}s")

        all_results.append({"label": label, "metrics": metrics})

        # Free Keras session memory between runs
        del model
        tf.keras.backend.clear_session()

    # -- Summary Markdown table ---------------------------------------------
    _print_markdown_table(all_results)

    # -- Aggregate CSV across all runs --------------------------------------
    agg_rows = []
    for r in all_results:
        agg_rows.append({"Model State": r["label"], **r["metrics"]})
    pd.DataFrame(agg_rows).to_csv(
        os.path.join(OUTPUT_DIR, "ablation_summary.csv"), index=False
    )
    print(f"[*] Aggregate results saved to: {os.path.join(OUTPUT_DIR, 'ablation_summary.csv')}")
    print(f"[*] Total wall-clock time: {(time.time() - total_start) / 60:.1f} min\n")


if __name__ == "__main__":
    main()
