# Road Quality Monitor: End-to-End Walkthrough

## 1. Project Overview
**Road Quality Monitor** is a mobile application that uses your phone's sensors and on-device Machine Learning to automatically detect road defects (like potholes) and visualize them on a map. It allows users to contribute to a shared, real-time database of road conditions.

## 2. User Journey & Features

### Phase 1: Access & Security
*   **Secure Entry**: When you launch the app, you are greeted with a secure Login Screen.
*   **Guest Mode**: For quick testing, you can "Continue as Guest" to start monitoring immediately without an account.
*   **User Accounts**: Registered users can sign in with email/password to track their personal contribution history.
*   **Session Management**: The app securely maintains your session so you don't have to log in every time.

### Phase 2: The Map Interface
*   **Live Map**: Once inside, you see a full-screen map powered by **Mapbox**.
*   **Location Tracking**: The app centers on your current GPS location.
*   **Crowdsourced Data**: You can see markers dropped by *other users* in real-time.
    -   **Green**: Good Road
    -   **Yellow**: Average Road
    -   **Red**: Bad Road / Pothole

### Phase 3: Road Quality Monitoring
*   **Start Monitoring**: Press the "Start Monitoring" button to begin.
*   **Data Collection**: The app silently records high-frequency accelerometer and gyroscope data.
*   **Real-Time Sync**: If a defect is found, it is instantly sent to the server and broadcast to all other connected users.

## 3. Under the Hood: The ML Engine
This app doesn't just send raw sensor data to a server (which would be slow and expensive). Instead, it runs an advanced **Artificial Intelligence Brain** directly on your phone using **TensorFlow Lite (TFLite)**.

Here is the step-by-step process of how the App "Thinks":

### Step 1: Listening (Data Acquisition)
The app listens to your phone's internal sensors 10 times every second (10Hz). It captures 7 distinct signals:
1.  **Acceleration X, Y, Z**: How much the phone is bumping up/down or side-to-side.
2.  **Rotation X, Y, Z**: How much the phone is tilting or turning.
3.  **Speed**: How fast the vehicle is moving.

### Step 2: Packaging (Windowing)
Every 2 seconds, it takes the last 20 frames of data and creates a "Window". This snapshot represents the motion of the vehicle over that specific stretch of road.

### Step 3: Feature Extraction (Math)
Raw sensor numbers are noisy. To make sense of them, the app calculates **42 specific mathematical features** from that window. For each of the 7 signals, it computes:
*   **Mean**: The average value.
*   **Standard Deviation**: How much it shakes.
*   **RMS**: The energy of the vibration.
*   **Range**: The difference between the biggest bump and deepest dip.
*   **Skewness & Kurtosis**: The shape of the vibration wave (crucial for distinguishing potholes from speed bumps).

### Step 4: Making the Decision (Inference)
This mathematical fingerprint is fed into two parts of the Neutral Network model:
1.  **Statistical Input**: The 42 calculated features.
2.  **Raw Input**: The original sensor waves.

The **TFLite Model** processes this data in milliseconds and outputs a probability score for road quality:
*   **Class 0**: Smooth Road
*   **Class 1**: Minor Irregularities
*   **Class 2**: Severe Damage (Pothole)

This entire process happens locally on your device, ensuring privacy and zero lag.

## 4. Technical Architecture

### Frontend (Mobile App)
*   **Framework**: React Native (Android).
*   **Maps**: Integrated `@rnmapbox/maps` for high-performance vector maps.
*   **AI Engine**: `react-native-fast-tflite` for offline, edge-AI inference.

### Backend (Server)
*   **Real-Time Core**: **Socket.IO** server handles instant communication.
*   **Database**: MongoDB stores User profiles and Road Quality logs.
*   **Security**: Authenticated API endpoints.

## 5. How to Run & Verify

1.  **Start the Server**:
    ```powershell
    cd Backend
    npm start
    ```
2.  **Connect Device**:
    ```powershell
    adb reverse tcp:8081 tcp:8081
    adb reverse tcp:5000 tcp:5000
    ```
3.  **Launch App**:
    ```powershell
    npx react-native run-android
    ```
4.  **Test the Loop**:
    *   **Login** as Guest.
    *   **Shake** the phone to simulate driving over a bump.
    *   **Watch** as a new marker appears on the map automatically!
