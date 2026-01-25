# Road Quality Classification Model

This directory contains the complete machine learning workflow for classifying road quality using mobile device sensor data (Accelerometer, Gyroscope, GPS Speed). The model differentiates between **Good (0), Average (1), Bad (2), and Very Bad (3)** road conditions.

## Project Structure

* **`data/`**: Stores raw and processed datasets.
* **`docs/`**: Detailed documentation for specific pipeline stages.
  * `combining/`: Data cleaning, labeling logic, and merging strategies.
  * `model/`: ML model architecture and training pipeline details.
* **`src/`**: Source code/notebooks.
  * `combination/`: Scripts for merging and labeling raw data.
  * `model/`: Model training and evaluation (generates `.tflite` and `scaler_params.json`).
  * `testing_on_reallife_locations/`: Scripts to test the model with real-world data collection.

---

## Data Pipeline & Preparation

Before training, raw data from multiple collections (PVS dataset) is harmonized and labeled.

**Key Steps:**

1. **Dataset Source**:
   * PVS Dataset (Kaggle)
   * Pothole Sensor Data (Kaggle)
   * *See `docs/combining/steps_to_download_data.txt` for links.*
2. **Centering Sensors**: "Left" and "Right" dashboard sensors are averaged to simulate a central mounting point.
3. **Unit Conversion**: Gyroscope readings are converted from **Degrees/sec** to **Radians/sec** to match standard Android/iOS outputs.
4. **Downsampling**: High-frequency data (100Hz) is downsampled to **10Hz** to mimic typical mobile app collection rates.
5. **Labeling Logic**: Complex boolean masks assign one of 4 classes based on road features (e.g., presence of pavment, unpaved surfaces, speed bumps, cobblestones).
   * *See `docs/combining/multi_class_kaggle.md` for specific equations.*

---

## Machine Learning Model

The core of this project is a **Hybrid CNN-MLP** model that processes both raw time-series data and aggregate statistical features simultaneously.

### Architecture

1. **Input 1: Raw Sensor Data (1D CNN)**
   * Captures temporal patterns over a 2-second window (20 samples).
   * Shape: `(20, 7)` -> `[ax, ay, az, wx, wy, wz, speed]`
2. **Input 2: Statistical Features (MLP)**
   * Captures global characteristics of the window (Mean, Std, RMS, Skewness, Kurtosis, etc.).
   * Shape: `(42)` features.

### Training

* **Imbalance Handling**: Class weights often applied to handle the scarcity of "Average" (1) labels.
* **Output**: Softmax probability distribution over 4 classes.
* *See `docs/model/machine_learning_pipeline.md` for full training details.*

---

## App Integration Guide: Using `model.tflite`

To successfully use the trained `model.tflite` in a mobile application, you **MUST** replicate the preprocessing steps exactly as they were performed during training.

### Critical Pre-requisites

1. **Sampling Rate**:

   * Your app must collect sensor data at **10 Hz**.
   * If higher, downsample; if lower, results may be unreliable.
2. **Windowing**:

   * Collect a buffer of **20 sequential readings** (2 seconds).
   * Calculate statistical features for this window.
3. **Handling NaNs**:

   * Statistical calculations (like Skewness/Kurtosis) on flat data can produce NaNs. These must be replaced with `0.0` before inference.
4. **Data Scaling (Most Important)**:

   * The model does **NOT** accept raw sensor values directly.
   * You must normalize both the Raw Data and Statistical Features using the **exact means and standard deviations** calculated during training.
   * These parameters are stored in `src/model/scaler_params.json`.
   * **Formula**: `input_normalized = (input_raw - training_mean) / training_std`

### Inference Steps (Python Example)

Refer to `src/testing_on_reallife_locations/test.ipynb` for a working implementation.

```python
# 1. Load Scaler Params
with open("scaler_params.json", "r") as f:
    params = json.load(f)

# 2. Preprocess Individual Window (Example)
# raw_window shape: (1, 20, 7)
# stats_window shape: (1, 42)

# Apply Scaling
norm_raw = (raw_window - params["raw_scaler"]["mean"]) / params["raw_scaler"]["std"]
norm_stats = (stats_window - params["stats_scaler"]["mean"]) / params["stats_scaler"]["std"]

# 3. Predict
# Note: Input order might vary, check input_details index!
# Commonly: [Index 0: Stats, Index 1: Raw] or vice versa.
interpreter.set_tensor(input_details[0]['index'], norm_stats.astype(np.float32))
interpreter.set_tensor(input_details[1]['index'], norm_raw.astype(np.float32))
interpreter.invoke()
```

**Output Mapping**:

* 0: Good
* 1: Average
* 2: Bad
* 3: Very Bad
