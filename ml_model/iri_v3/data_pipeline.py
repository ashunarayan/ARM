"""
data_pipeline.py — Spatial resampling, feature extraction, and dataset loading.

Extracted verbatim from model_4.ipynb (Cell 2), then parameterised so the
kinetic normalisation of az can be toggled via the `use_kinetic_norm` flag.
"""

import os
import time
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from joblib import Parallel, delayed

from config import (
    BASE_DATA_DIR, FINAL_SPATIAL_STEPS, MIN_SPEED_MS,
    AUGMENT_HZ, RAW_FEATURES, SPLITS,
    WINDOW_SIZE_M, STEP_SIZE_M,
)

# ---------------------------------------------------------------------------
# Context Feature Extraction  (identical to model_4)
# ---------------------------------------------------------------------------

def extract_context_features(raw_data_window, speed_array, distance_m):
    """
    Extracts 13 contextual features from the spatially resampled window.

    Parameters:
        raw_data_window (np.ndarray): Shape (400, 6) -> [ax, ay, az, wx, wy, wz]
        speed_array (np.ndarray): Spatially interpolated speed values.
        distance_m (float): Starting distance of the window.

    Returns:
        np.ndarray: Array of 13 statistical and pseudo-spectral features.
    """
    ax, ay, az, wx, wy, wz = [raw_data_window[:, i] for i in range(6)]
    N = len(az)

    speed_mean = np.mean(speed_array)
    speed_std  = np.std(speed_array)

    rms_az          = np.sqrt(np.mean(az**2))
    rms_ay          = np.sqrt(np.mean(ay**2))
    var_az          = np.var(az)
    crest_factor_az = np.max(np.abs(az)) / (rms_az + 1e-6)

    zero_crossings_az = len(np.where(np.diff(np.sign(az)))[0])
    mcr_az  = zero_crossings_az / N
    p2p_az  = np.max(az) - np.min(az)

    rms_wz       = np.sqrt(np.mean(wz**2))
    rms_wy       = np.sqrt(np.mean(wy**2))
    mean_abs_ax  = np.mean(np.abs(ax))

    # Pseudo-spectral features (converting spatial frequencies to temporal)
    fft_vals       = np.fft.rfft(az)
    psd            = np.abs(fft_vals)**2
    freqs_spatial  = np.fft.rfftfreq(N, d=0.25)

    if speed_mean > 0:
        freqs_temporal  = freqs_spatial * speed_mean
        band_1_4  = np.sum(psd[(freqs_temporal >= 1.0) & (freqs_temporal <= 4.0)])
        band_4_15 = np.sum(psd[(freqs_temporal >  4.0) & (freqs_temporal <= 15.0)])
        total_energy = np.sum(psd) + 1e-6
        energy_ratio_1_4  = band_1_4  / total_energy
        energy_ratio_4_15 = band_4_15 / total_energy
    else:
        energy_ratio_1_4, energy_ratio_4_15 = 0.0, 0.0

    return np.array([
        speed_mean, speed_std, rms_az, rms_ay, var_az, crest_factor_az,
        mcr_az, p2p_az, rms_wz, rms_wy, mean_abs_ax,
        energy_ratio_1_4, energy_ratio_4_15
    ])


# ---------------------------------------------------------------------------
# Per-Trip Processing  (identical to model_4, + kinetic_norm toggle)
# ---------------------------------------------------------------------------

def process_trip_data(df, trip_identifier, use_kinetic_norm=True):
    """
    Parses trip telemetry, filters slow speeds, and applies spatial windowing.
    
    `use_kinetic_norm` controls whether the physics-based speed normalisation
    is applied to the az channel (Run 4 ablation).
    """
    X_raw_list, X_ctx_list, y_list = [], [], []

    df = df[df['speed_ms'] >= MIN_SPEED_MS].copy().sort_values('sample_number')
    if len(df) < 50:
        return [], [], []

    df['time_s']             = df['sample_number'] * 0.01
    df['dt']                 = df['time_s'].diff().fillna(0.01)
    df['dx']                 = df['speed_ms'] * df['dt']
    df['cumulative_distance']= df['dx'].cumsum()

    max_dist = df['cumulative_distance'].max()

    for start_dist in np.arange(0, max_dist - WINDOW_SIZE_M, STEP_SIZE_M):
        end_dist = start_dist + WINDOW_SIZE_M
        patch = df[
            (df['cumulative_distance'] >= start_dist) &
            (df['cumulative_distance'] <  end_dist)
        ]

        if len(patch) < 20:
            continue

        target_iri = patch['IRI'].mean()
        start_time, end_time = patch['time_s'].min(), patch['time_s'].max()

        # Temporal jitter / augmentation
        target_hz     = np.random.choice(AUGMENT_HZ)
        poll_interval = 1.0 / target_hz
        t_polls       = np.arange(start_time, end_time, poll_interval)
        if len(t_polls) < 5:
            continue
        t_polls += np.random.uniform(0, poll_interval * 0.2, size=len(t_polls))

        augmented_features = []
        for feat in RAW_FEATURES:
            os_sensor = interp1d(
                patch['time_s'], patch[feat],
                kind='previous', fill_value='extrapolate'
            )
            augmented_features.append(os_sensor(t_polls))

        os_speed = interp1d(patch['time_s'], patch['speed_ms'],
                            kind='linear', fill_value='extrapolate')
        augmented_speed = os_speed(t_polls)

        os_dist = interp1d(patch['time_s'], patch['cumulative_distance'],
                           kind='linear', fill_value='extrapolate')
        augmented_dists = os_dist(t_polls)

        # Spatial domain resampling to fixed grid
        fixed_spatial_grid  = np.linspace(start_dist, end_dist, FINAL_SPATIAL_STEPS)
        fixed_patch_features = []

        for i in range(len(RAW_FEATURES)):
            spatial_fix = interp1d(
                augmented_dists, augmented_features[i],
                kind='linear', bounds_error=False,
                fill_value=(augmented_features[i][0], augmented_features[i][-1])
            )
            fixed_patch_features.append(spatial_fix(fixed_spatial_grid))

        spatial_speed = interp1d(
            augmented_dists, augmented_speed,
            kind='linear', bounds_error=False,
            fill_value=(augmented_speed[0], augmented_speed[-1])
        )(fixed_spatial_grid)

        X_raw_filtered = np.column_stack(fixed_patch_features)

        # --------------- Ablation point: kinetic normalisation ---------------
        if use_kinetic_norm:
            az_idx  = RAW_FEATURES.index('az')
            v_safe  = np.maximum(spatial_speed, 5.0)
            X_raw_filtered[:, az_idx] = X_raw_filtered[:, az_idx] * ((22.22 / v_safe) ** 2)
        # ---------------------------------------------------------------------

        X_ctx = extract_context_features(X_raw_filtered, spatial_speed, start_dist)

        X_raw_list.append(X_raw_filtered)
        X_ctx_list.append(X_ctx)
        y_list.append(target_iri)

    return X_raw_list, X_ctx_list, y_list


def _worker_process_trip(car, route, trip, use_kinetic_norm):
    """Joblib worker: process one trip and return split-labelled arrays."""
    trip_key = f"{route}_{trip}"

    split = 'train'
    if route in SPLITS['train']:
        split = 'train'
    elif route == 'automation_test_track':
        if   trip == 'trip_1':                   split = 'val'
        elif trip in ['trip_2', 'trip_3']:        split = 'test'
        else:                                     return None
    else:
        return None

    csv_path = os.path.join(BASE_DATA_DIR, car, route, trip, 'readings_2.csv')
    if not os.path.exists(csv_path):
        return None

    df = pd.read_csv(csv_path)
    x_r, x_c, y_val = process_trip_data(df, trip_key, use_kinetic_norm)

    if len(y_val) == 0:
        return None
    return {'split': split, 'raw': x_r, 'ctx': x_c, 'y': y_val}


def build_datasets(use_kinetic_norm=True):
    """
    Compiles the dataset using parallel processing across CPU cores.
    Mirrors model_4.build_datasets(), with the kinetic_norm toggle.
    """
    datasets = {
        'train': {'raw': [], 'ctx': [], 'y': []},
        'val':   {'raw': [], 'ctx': [], 'y': []},
        'test':  {'raw': [], 'ctx': [], 'y': []},
    }

    tasks = []
    if os.path.exists(BASE_DATA_DIR):
        for car in sorted(os.listdir(BASE_DATA_DIR)):
            car_p = os.path.join(BASE_DATA_DIR, car)
            if not os.path.isdir(car_p) or car == 'desktop.ini':
                continue
            for route in sorted(os.listdir(car_p)):
                route_p = os.path.join(car_p, route)
                if not os.path.isdir(route_p) or route == 'desktop.ini':
                    continue
                for trip in sorted(os.listdir(route_p)):
                    if os.path.isdir(os.path.join(route_p, trip)):
                        tasks.append((car, route, trip))

    print(f"[*] Dispatching {len(tasks)} trips to worker pool...")
    t0 = time.time()

    results = Parallel(n_jobs=-1, backend='loky')(
        delayed(_worker_process_trip)(car, route, trip, use_kinetic_norm)
        for car, route, trip in tasks
    )

    for res in results:
        if res:
            s = res['split']
            datasets[s]['raw'].extend(res['raw'])
            datasets[s]['ctx'].extend(res['ctx'])
            datasets[s]['y'].extend(res['y'])

    for split in ['train', 'val', 'test']:
        datasets[split]['raw'] = np.array(datasets[split]['raw'], dtype=np.float32)
        datasets[split]['ctx'] = np.array(datasets[split]['ctx'], dtype=np.float32)
        datasets[split]['y']   = np.array(datasets[split]['y'],   dtype=np.float32)
        print(
            f"{split.upper()} SET -> "
            f"Raw: {datasets[split]['raw'].shape}, "
            f"Ctx: {datasets[split]['ctx'].shape}"
        )

    print(f"[*] Processing completed in {time.time() - t0:.2f}s")
    return datasets
