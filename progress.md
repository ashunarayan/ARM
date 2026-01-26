# Project Progress Report: Crowd-Sourced Road Quality Monitoring System

**Date:** January 26, 2026
**Version:** 1.0.0
**Status:** In Progress (High Fidelity, Production-Ready Architecture)

---

## 1. Executive Summary

This project aims to build a scalable, crowd-sourced system for real-time road quality assessment using mobile device sensors (Accelerometer, Gyroscope, GPS). The core innovation combines **TinyML (On-device inference)** via a dedicated mobile app with a robust **Backend (Node.js/Socket.IO)** for aggregating and broadcasting road conditions to a community of users.

**Current State:**

- **Mobile App**: Production-ready architecture with Mapbox, sensor fusion (10Hz), and ML pipeline structure.
- **Machine Learning**: Hybrid CNN-MLP model fully trained, validated, and exported (`.tflite`).
- **Backend**: Complete scalable architecture with real-time WebSocket communication, geohashed segmentation, and map matching.

---

## 2. Mobile Application Progress

**Path:** `mobile-app/`
**Tech Stack:** React Native (Expo), TypeScript, TensorFlow Lite, Mapbox.

### Completed Features

* **Production-Ready Architecture:** Implemented a clean "Service Layer" pattern separating UI, Business Logic, and Infrastructure.
* **Mapbox Integration:**
  * Interactive map with user location tracking.
  * Dynamic road quality markers.
  * Auto-centering and smooth camera animations.
* **Sensor Pipeline:**
  * **Data Collection:** Captures Accelerometer & Gyroscope data at **10Hz**.
  * **Windowing Service:** Buffers readings into 2-second windows (20 samples) for ML inference.
  * **Unit Standardization:** Converts gyroscope data (degrees/sec → radians/sec) to match training data.
* **ML Integration Layer:**
  * Built a robust `ml.ts` orchestrator.
  * Implemented handling for `scaler_params.json` to normalize real-time data exactly as the model expects.
  * **Mock Inference Mode:** Fully functional testing pipeline.

### Pending / In Progress

* **TFJS Model Loading:** The `model.tflite` is present, but the final conversion to **TensorFlow.js graph model** (`model.json` + weights) is pending.
* **Real Inference Switch:** Switching from "Mock Mode" to actual on-device inference using the converted model.

---

## 3. Machine Learning & Data Science Progress

**Path:** `ml_model/`
**Tech Stack:** Python, TensorFlow/Keras, XGBoost, Pandas.

### Completed Features

* **Data Pipeline:**
  * **Sources:** PVS Dataset & Kaggle Pothole data.
  * **Preprocessing:** Centering sensors, downsampling to 10Hz, handling missing data.
  * **Labeling Logic:** Complex boolean masking to categorize roads into 4 classes (Good, Average, Bad, Very Bad).
* **Model Architecture (Hybrid):**
  * **CNN Branch:** 1D Convolutional Neural Network processing raw time-series data (20x7 input).
  * **MLP Branch:** Multi-Layer Perceptron processing statistical features (Mean, Std, RMS, etc.).
  * **Performance:** Model trained ("best_road_model.h5") and exported as `model.tflite`.
* **Validation:**
  * Scripts in `src/testing_on_reallife_locations/` to validate model performance on real-world test data.

---

## 4. Backend & Cloud Infrastructure Progress

**Path:** `Backend/`
**Tech Stack:** Node.js, Express, Socket.IO, MongoDB, Redis, Google Cloud Platform (GCP).

### Completed Features

* **API & Services:**
  * **REST API:** Secure endpoints for Auth (JWT), Observations, and Road Segments.
  * **Map Matching:** Integration with OSRM to snap raw GPS points to actual road segments.
  * **Aggregation Service:** Logic to compute weighted average road quality scores over time.
* **Real-Time System:**
  * **Spatial Segmentation:** Geohash-based system (Precision 6) to group users into regional Socket.IO rooms.
  * **Broadcasting:** Real-time updates pushed *only* to users in the affected region.
* **Data & Security:**
  * **Database Schema:** Optimized MongoDB collections for Users, RoadSegments, and Observations.
  * **Authentication:** Full JWT flow including "Anonymous" login support for friction-less user onboarding.

### Pending / In Progress

* **Cloud Deployment:** Dockerization and deployment to **Google Cloud Run** (as per project synopsis).
* **Redis Integration:** Configuration for multi-server scaling (adapter logic).

---

## 5. Immediate Next Steps (Roadmap)

1. **ML Conversion:** Run `tensorflowjs_converter` on the `model.tflite` to generate the web-compatible model assets for the mobile app.
2. **End-to-End Integration:** Validate the full loop: `Sensor -> Model -> App -> API -> DB -> Socket -> Map Update`.
3. **Deployment:** Create `Dockerfile` for the backend and deploy to a staging environment on GCP.

---

## Artifacts Summary

| Component         | Key Artifacts                             | Status   |
| ----------------- | ----------------------------------------- | -------- |
| **Mobile**  | `mobile-app/src/services/ml.ts`         | ✅ Ready |
| **Mobile**  | `mobile-app/INTEGRATION_SUMMARY.md`     | ✅ Ready |
| **Model**   | `ml_model/src/model/model.tflite`       | ✅ Ready |
| **Model**   | `ml_model/src/model/scaler_params.json` | ✅ Ready |
| **Backend** | `Backend/docs/ARCHITECTURE.md`          | ✅ Ready |
| **Backend** | `Backend/src/services/socketService.js` | ✅ Ready |
