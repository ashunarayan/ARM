#!/usr/bin/env bash
# Re-runs the September-2026 audit against the legacy (rejected-paper) pipeline.
# Uses the legacy TF environment because the audited models are Keras files.
PY="${PY_LEGACY:-/c/Users/nishk/anaconda3/envs/tf/python.exe}"
cd "$(dirname "$0")"
mkdir -p outputs
for s in audit_raw audit_overlap_jitter audit_labels audit_imu_label audit_eval audit_filter audit_pvs audit_misc; do
  echo "=== $s"
  CUDA_VISIBLE_DEVICES=-1 TF_CPP_MIN_LOG_LEVEL=3 "$PY" "$s.py" > "outputs/$s.txt" 2>&1
  echo "exit=$? -> outputs/$s.txt"
done
