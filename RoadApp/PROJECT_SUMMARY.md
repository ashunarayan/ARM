# RoadApp - Project Summary

## Overview
Production-ready React Native CLI app for road quality monitoring with on-device ML inference, Firebase authentication, and Mapbox visualization.

## Architecture

### Tech Stack
- **React Native CLI 0.83.1** (NOT Expo)
- **TypeScript 5.8.3**
- **Firebase Auth** (@react-native-firebase/auth)
- **Mapbox Maps** (@rnmapbox/maps) - Native implementation
- **TensorFlow Lite** (react-native-tflite) - On-device inference
- **Axios** - HTTP client
- **AsyncStorage** - Token persistence

### Project Structure
```
RoadApp/
├── android/                  # Android native code
│   ├── app/
│   │   ├── build.gradle     # App build config + Firebase plugin
│   │   └── google-services.json  # Firebase config (ADD THIS)
│   ├── build.gradle         # Project build config + Mapbox
│   └── gradle.properties    # Mapbox download token (UPDATE THIS)
├── src/
│   ├── assets/
│   │   └── model.tflite     # TFLite model (COPIED FROM ml_model/)
│   ├── config/
│   │   └── index.ts         # Firebase, Mapbox, Backend URLs (UPDATE THIS)
│   ├── screens/
│   │   ├── AuthScreen.tsx   # Login/Signup UI
│   │   └── MapScreen.tsx    # Map + Observation collection
│   ├── services/
│   │   ├── apiClient.ts     # Axios instance with auth interceptor
│   │   ├── authService.ts   # Firebase auth wrapper
│   │   ├── mlService.ts     # TFLite model inference
│   │   └── observationService.ts  # Backend API calls
│   └── types/
│       └── index.ts         # TypeScript interfaces
├── App.tsx                  # Root component with auth flow
├── package.json             # Dependencies
└── tsconfig.json            # TypeScript config

```

## Data Flow

### Authentication Flow
1. User enters email/password in AuthScreen
2. Firebase Auth signs in/signs up
3. Firebase ID token obtained
4. Token stored in AsyncStorage
5. API client automatically adds token to all requests via interceptor

### Observation Collection Flow
1. User clicks "Collect Observation" on MapScreen
2. Sensor data collected (mocked in current version)
3. MLService runs TFLite model on-device
4. Model predicts road quality score (0-3)
5. ObservationService sends to Backend:
   ```json
   {
     "latitude": 37.78825,
     "longitude": -122.4324,
     "roadQuality": 2,
     "timestamp": "2026-01-26T10:00:00.000Z",
     "speed": 30,
     "deviceMetadata": {
       "model": "Pixel 6",
       "os": "android 13",
       "appVersion": "1.0.0"
     }
   }
   ```
6. Backend validates Firebase token
7. Backend performs map matching
8. Backend aggregates and stores observation

### Map Visualization Flow
1. MapScreen loads road segments from Backend
2. Backend returns segments with aggregated quality scores
3. Mapbox renders GeoJSON LineStrings
4. Segments colored by score:
   - 0-0.5: Green (excellent)
   - 0.5-1.5: Light green (good)
   - 1.5-2.5: Orange (fair)
   - 2.5-3.0: Red (poor)

## API Contract with Backend

### Submit Observation
**Endpoint:** `POST /api/observations`
**Headers:** `Authorization: Bearer <firebase_id_token>`
**Body:**
```json
{
  "latitude": number,
  "longitude": number,
  "roadQuality": 0 | 1 | 2 | 3,
  "timestamp": string (ISO 8601),
  "speed": number (optional),
  "deviceMetadata": {
    "model": string,
    "os": string,
    "appVersion": string
  }
}
```

### Get Road Segments
**Endpoint:** `GET /api/roads/segments`
**Headers:** `Authorization: Bearer <firebase_id_token>`
**Query Params:**
- `latitude`: number
- `longitude`: number
- `radius`: number (meters, default 5000)

**Response:**
```json
{
  "segments": [
    {
      "roadSegmentId": "string",
      "aggregatedQualityScore": number,
      "confidenceScore": number,
      "geometry": {
        "type": "LineString",
        "coordinates": [[lng, lat], ...]
      },
      "regionId": "string"
    }
  ]
}
```

## ML Model

### Model Details
- **File:** `src/assets/model.tflite`
- **Input:** 7 features (accelerometer X/Y/Z, gyroscope X/Y/Z, speed)
- **Output:** 4 class probabilities [0, 1, 2, 3]
- **Inference:** On-device (NOT sent to backend)

### Current Implementation
- Model loaded once on MapScreen mount
- Prediction runs synchronously when collecting observation
- Dummy sensor data used (real sensors TODO)

## Configuration Requirements

### Required Before Build
1. **Firebase:**
   - `google-services.json` in `android/app/`
   - Firebase config in `src/config/index.ts`

2. **Mapbox:**
   - Public token in `src/config/index.ts`
   - Secret token in `android/gradle.properties`

3. **Backend:**
   - Backend URL in `src/config/index.ts`
   - Backend server running and accessible

4. **ML Model:**
   - `model.tflite` in `src/assets/` (already copied)

## Build & Deploy

### Development Build
```bash
npx react-native run-android
```

### Debug APK
```bash
cd android
./gradlew assembleDebug
```
Output: `android/app/build/outputs/apk/debug/app-debug.apk`

### Release APK (TODO: Setup keystore)
```bash
cd android
./gradlew assembleRelease
```

## Known Limitations & TODOs

### Current Limitations
- No real sensor integration (accelerometer/gyroscope)
- No location tracking (using hardcoded coordinates)
- No real-time observation collection during driving
- No offline support
- Android-only (iOS not configured)

### Production TODOs
1. Integrate real device sensors (react-native-sensors)
2. Add location tracking with react-native-geolocation
3. Implement background observation collection
4. Add offline queue with local database
5. Implement proper error handling and retry logic
6. Add user feedback and loading states
7. Optimize ML inference performance
8. Add proper logging and analytics
9. Setup release keystore and signing
10. Add iOS support

## Testing

### Test Accounts
Create test Firebase accounts manually in Firebase Console.

### Test Observations
1. Ensure Backend is running
2. Update BACKEND_URL to point to Backend
3. Sign in with Firebase account
4. Click "Collect Observation"
5. Verify observation appears in Backend database

### Test Map
1. Ensure Backend has road segments with aggregated scores
2. Map should render colored lines based on quality scores

## Security Notes

- Firebase ID tokens expire after 1 hour (auto-refreshed)
- No sensitive data stored locally except Firebase token
- All Backend requests require valid Firebase token
- Model runs locally - no data sent for inference

## Support

For configuration help, see:
- `SETUP_GUIDE.md` - Detailed setup instructions
- `CONFIGURATION.md` - Quick configuration reference
- `README.md` - Getting started guide
