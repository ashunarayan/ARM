# ML Model Setup

## Instructions

1. Copy your trained TensorFlow Lite model file here:
   - Source: `ml_model/src/model/model.tflite`
   - Destination: `mobile-app/assets/ml-model/model.tflite`

2. The model should be named exactly: `model.tflite`

## Model Specifications

- **Type**: Hybrid CNN
- **Input**: 2-second sliding window (20 readings @ 10Hz)
- **Features per reading**: 7 (ax, ay, az, wx, wy, wz, speed)
- **Output**: Single integer classification (0-3)
  - 0 = very bad
  - 1 = bad
  - 2 = good
  - 3 = very good
