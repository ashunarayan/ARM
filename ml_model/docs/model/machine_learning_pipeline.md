# Machine Learning Pipeline Explanation

This document outlines the machine learning pipeline developed for the Road Quality Classification project, located in `ml_model\src\model\main.ipynb`. The goal of this pipeline is to classify road segments into one of four quality categories: **Good (0), Average (1), Bad (2), and Very Bad (3)**, using sensor data collected from mobile devices.

## 1. Data Ingestion
The pipeline begins by loading training and testing datasets from CSV files (`../../data/combined/multi_class_kaggle/train.csv` and `test.csv`).
*   **Input Features**: Accelerometer (`ax`, `ay`, `az`), Gyroscope (`wx`, `wy`, `wz`), and GPS `speed`.
*   **Target Label**: `roadQuality`.
*   **Data Structure**: Time-series data recorded at approximately 10Hz.

## 2. Exploratory Data Analysis (EDA)
*   **Class Imbalance Check**: The dataset was analyzed for class distribution. It was observed that class `1` (Average) is significantly underrepresented compared to others.
*   **Strategy**: To mitigate this, **Class Weights** were calculated and applied during model training to penalize misclassifications of minority classes more heavily.

## 3. Data Preprocessing & Feature Engineering
A custom windowing function `create_windows` was implemented to process the continuous time-series data into discrete samples for classification.

### Windowing Strategy
*   **Window Size**: 20 samples (representing 2 seconds of data).
*   **Step Size**: 10 samples (50% overlap between windows).
*   **Label Assignment**: The mode (most frequent label) of the time steps in a window is assigned as the window's label. Windows with majority unlabeled data (`-1`) are discarded.

### Dual Input Generation
The preprocessing pipeline generates two distinct types of inputs for a Hybrid Model:
1.  **Raw Sensor Data (CNN Input)**: 
    *   Shape: `(N_samples, 20, 7)`
    *   Contains the raw sequences of the 7 sensor channels.
2.  **Statistical Features (MLP Input)**:
    *   Shape: `(N_samples, 42)`
    *   For each of the 7 sensor channels, 6 statistical metrics are calculated:
        *   Mean
        *   Standard Deviation
        *   Root Mean Square (RMS)
        *   Range (Peak-to-Peak)
        *   Skewness
        *   Kurtosis

### Cleaning & Scaling
*   **NaN Handling**: Any NaNs generated (e.g., during skew/kurtosis calculation on flat signals) are filled with zeros.
*   **Normalization**: `StandardScaler` is applied to both inputs to normalize features (Mean=0, Std=1).
    *   A separate scalar is fitted for raw data and statistical features.
    *   Parameters are saved to `scaler_params.json` for consistent inference later.

## 4. Model Architecture: Hybrid CNN-MLP
A custom Keras model was built to leverage both temporal patterns in raw data and aggregate statistics.

### Branch 1: 1D CNN (Raw Data)
*   extracts local temporal features from the sensor readings.
*   **Layers**:
    *   `Conv1D` layers with `ReLU` activation.
    *   `Dropout` for regularization.
    *   `BatchNormalization` for stability.
    *   `MaxPooling1D` for downsampling.
    *   `GlobalAveragePooling1D` to flatten temporal features.

### Branch 2: MLP (Statistical Features)
*   Processes the 42 engineered statistical features.
*   **Layers**:
    *   `Dense` (Fully Connected) layers.
    *   `Dropout` and `BatchNormalization`.

### Combination & Output
*   **Concatenation**: The outputs of the CNN branch and MLP branch are concatenated into a single feature vector.
*   **Classification Head**: Final Dense layers lead to an output layer of size 4 (for the 4 classes).
*   **Optimizer**: Adam.
*   **Loss Function**: Sparse Categorical Crossentropy (implied/used for integer labels).

## 5. Training
*   **Callbacks**: 
    *   `EarlyStopping`: To prevent overfitting by stopping training when validation loss stops improving.
    *   `ModelCheckpoint`: Saves the model with the lowest validation loss as `best_road_model.h5`.
*   **Performance**: The model achieved approximately **84% accuracy** on the test set.
    *   Precision is very high for "Good" roads (~99%).
    *   Recall is strong for "Good" (94%) and "Bad" (85%) roads.
    *   "Average" roads remain challenging due to low data support, though a high recall (90%) was achieved at the cost of precision.
