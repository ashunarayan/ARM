# Mapbox & ML Integration Architecture

## 📋 Overview

This document describes the clean architecture for integrating Mapbox maps and ML road quality detection in the mobile app.

**Key Principles:**
- ✅ Separation of concerns
- ✅ No hardcoded tokens or URLs
- ✅ Isolated modules (Mapbox, ML, API)
- ✅ Service layer for business logic
- ✅ Presentational UI components
- ✅ Production-ready patterns

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│              UI Components                  │
│  - RoadMonitoringScreen                     │
│  - MapView (presentational)                 │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│           Service Layer                     │
│  - mlService (orchestrator)                 │
│  - observationService (API bridge)          │
│  - mapboxService (utilities)                │
└──┬────────┬────────────┬─────────────────┬──┘
   │        │            │                 │
┌──▼───┐ ┌─▼────┐ ┌─────▼─────┐ ┌────────▼───┐
│ ML   │ │ Map  │ │ Backend   │ │ Sensors    │
│ Logic│ │ Logic│ │ API       │ │ (Accel/    │
│      │ │      │ │           │ │  Gyro)     │
└──────┘ └──────┘ └───────────┘ └────────────┘
```

---

## 📁 File Structure

```
mobile-app/
├── app/
│   ├── _layout.tsx                    # App initialization
│   └── (tabs)/
│       └── monitor.tsx                # Example usage screen
│
├── src/
│   ├── config/
│   │   └── env.ts                     # 🔧 Environment config
│   │
│   ├── types/
│   │   └── index.ts                   # 📝 Shared TypeScript types
│   │
│   ├── services/
│   │   ├── appInitializer.ts          # 🚀 App initialization
│   │   ├── mapboxService.ts           # 🗺️  Mapbox utilities
│   │   ├── ml.ts                      # 🧠 ML orchestrator
│   │   ├── tflite.ts                  # 🤖 TensorFlow inference
│   │   ├── observation.ts             # 📤 Backend observations
│   │   ├── sensorService.js           # 📱 Sensor data collection
│   │   └── windowService.js           # ⏱️  2-second windowing
│   │
│   ├── api/
│   │   └── client.ts                  # 📡 HTTP client
│   │
│   ├── components/
│   │   └── MapView.tsx                # 🗺️  Map component
│   │
│   └── screens/
│       └── RoadMonitoringScreen.tsx   # 📱 Example screen
│
└── assets/
    └── ml-model/
        ├── model.tflite               # 🤖 ML model
        └── scaler_params.json         # 📊 Preprocessing params
```

---

## 🔄 Data Flow

### 1. App Initialization (Once at startup)

```typescript
// In app/_layout.tsx
import { initializeApp } from '../src/services/appInitializer';

await initializeApp();
// ✅ Mapbox initialized
// ✅ ML model loaded
```

### 2. Road Monitoring Flow

```
User clicks "Start Monitoring"
          ↓
mlService.startMonitoring()
          ↓
Sensors collect data @ 10Hz
          ↓
windowService buffers 2s windows (20 readings)
          ↓
tfliteService.runInference(windowData)
          ↓
MLInferenceResult { quality, location, timestamp }
          ↓
   ┌──────┴──────┐
   ↓             ↓
UI updates   observationService.sendObservation()
Map marker        ↓
               Backend API
```

### 3. Component Integration Example

```typescript
import { MapView } from '../src/components/MapView';
import { mlService } from '../src/services/ml';

// Start monitoring with callback
await mlService.startMonitoring((result) => {
  // Update UI
  setLatestQuality(result.roadQuality);
  
  // Add marker to map
  addMarker({
    coordinate: [result.location.longitude, result.location.latitude],
    quality: result.roadQuality,
  });
  
  // Send to backend
  await observationService.sendObservation(result);
});
```

---

## 🔑 Key Components

### 1. Mapbox Service (`mapboxService.ts`)

**Purpose:** Initialize Mapbox and provide utilities

```typescript
import { mapboxService } from './services/mapboxService';

// Automatically initialized in app/_layout.tsx
// No need to call manually

// Utility methods
const coord = mapboxService.toMapboxCoordinate(lat, lng);
```

**Features:**
- ✅ One-time initialization
- ✅ No token exposure
- ✅ Coordinate conversion utilities

---

### 2. ML Service (`ml.ts`)

**Purpose:** Orchestrate ML inference pipeline

```typescript
import { mlService } from './services/ml';

// Start monitoring (with callback)
await mlService.startMonitoring((result) => {
  console.log('Quality:', result.roadQuality);
  console.log('Location:', result.location);
});

// Get latest result
const result = mlService.getLatestResult();

// Stop monitoring
mlService.stopMonitoring();
```

**Features:**
- ✅ Automatic sensor collection
- ✅ 2-second windowing
- ✅ Inference every 2 seconds
- ✅ Result callbacks
- ✅ Location metadata

---

### 3. MapView Component (`MapView.tsx`)

**Purpose:** Presentational map component

```typescript
import { MapView } from './components/MapView';

<MapView
  markers={roadMarkers}
  showUserLocation={true}
  followUserLocation={true}
  onLocationChange={(location) => console.log(location)}
/>
```

**Props:**
- `markers`: Array of road quality markers
- `showUserLocation`: Show user's current location
- `followUserLocation`: Auto-center on user
- `onLocationChange`: Callback for location updates

**Features:**
- ✅ User location tracking
- ✅ Road quality markers
- ✅ Auto-centering
- ✅ Isolated from business logic

---

### 4. Observation Service (`observation.ts`)

**Purpose:** Send observations to backend

```typescript
import { observationService } from './services/observation';

// Send single observation
await observationService.sendObservation(mlResult);

// Set session ID (optional)
observationService.setSessionId('session-123');

// Send queued observations (on network recovery)
await observationService.sendQueuedObservations();
```

**Features:**
- ✅ Automatic retry queue
- ✅ Session support
- ✅ Error handling

---

## 🚀 Usage Examples

### Basic Integration

```typescript
import React, { useState } from 'react';
import { MapView } from '../src/components/MapView';
import { mlService } from '../src/services/ml';

function MonitorScreen() {
  const [markers, setMarkers] = useState([]);
  
  const startMonitoring = async () => {
    await mlService.startMonitoring((result) => {
      // Add marker
      setMarkers(prev => [...prev, {
        id: `${result.timestamp}`,
        coordinate: [result.location.longitude, result.location.latitude],
        quality: result.roadQuality,
        timestamp: result.timestamp,
      }]);
    });
  };
  
  return (
    <MapView markers={markers} />
  );
}
```

---

## ⚙️ Configuration

### Environment Variables

All configuration is centralized in `src/config/env.ts`:

```typescript
export const ENV = {
  MAPBOX: {
    ACCESS_TOKEN: process.env.MAPBOX_ACCESS_TOKEN,
  },
  API: {
    BASE_URL: process.env.BACKEND_BASE_URL || 'http://...',
  },
  ML: {
    SENSOR_FREQUENCY: 10,  // Hz
    WINDOW_DURATION: 2,    // seconds
  },
};
```

**Never hardcode:**
- ❌ Mapbox access tokens
- ❌ Backend URLs
- ❌ API keys

---

## 🔒 Security & Best Practices

### 1. Token Management
```typescript
// ✅ Good: Load from environment
const token = ENV.MAPBOX.ACCESS_TOKEN;

// ❌ Bad: Hardcoded
const token = "pk.eyJ1...";
```

### 2. Separation of Concerns
```typescript
// ✅ Good: Service layer
await mlService.startMonitoring();
await observationService.sendObservation(result);

// ❌ Bad: Mixed logic in UI
fetch('/api/observations', {
  body: JSON.stringify({ /* ... */ })
});
```

### 3. Error Handling
```typescript
// ✅ Good: Try-catch with fallback
try {
  await mlService.startMonitoring();
} catch (error) {
  console.error('Failed to start:', error);
  Alert.alert('Error', 'Could not start monitoring');
}
```

---

## 🧪 Testing

### Test ML Service

```typescript
import { mlService } from './services/ml';

// Check if ready
if (mlService.isReady()) {
  console.log('✅ ML Service ready');
}

// Start monitoring with logging
await mlService.startMonitoring((result) => {
  console.log('Quality:', result.roadQuality);
  console.log('Location:', result.location);
  console.log('Speed:', result.speed);
});
```

### Test Mapbox

```typescript
import { mapboxService } from './services/mapboxService';

if (mapboxService.isReady()) {
  console.log('✅ Mapbox ready');
}
```

---

## 📌 Important Notes

### ML Model Format

⚠️ **IMPORTANT:** The `model.tflite` file needs to be converted to TensorFlow.js format for production use.

**Current State:**
- ✅ Placeholder model works for testing
- ✅ Mock inference available
- ⚠️  Real model requires conversion

**To use real model:**
1. Convert `.tflite` to SavedModel format
2. Use `tensorflowjs_converter` to convert to TFJS
3. Place `model.json` and weights in `assets/ml-model/`
4. Update `tflite.ts` to load the real model

**Conversion command:**
```bash
tensorflowjs_converter \
  --input_format=tf_saved_model \
  --output_format=tfjs_graph_model \
  path/to/saved_model \
  path/to/output
```

### Scaler Parameters

The `scaler_params.json` contains mean and std for preprocessing:
- ✅ Already copied from `ml_model/src/model/`
- ✅ Used automatically by `tflite.ts`
- ✅ Ensures consistent preprocessing

---

## 🆘 Troubleshooting

### Mapbox not showing

```typescript
// Check initialization
import { appInitializer } from './services/appInitializer';
const status = appInitializer.getStatus();
console.log('Mapbox ready:', status.mapbox);
```

### ML not working

```typescript
// Check ML service
import { mlService } from './services/ml';
console.log('ML ready:', mlService.isReady());
console.log('Monitoring:', mlService.isMonitoring());
```

### Location not updating

```typescript
// Check permissions
import * as Location from 'expo-location';
const { status } = await Location.requestForegroundPermissionsAsync();
console.log('Location permission:', status);
```

---

## 📚 Next Steps

1. **Convert ML Model:** Convert `model.tflite` to TFJS format
2. **Add Road Segments:** Implement segment overlays on map
3. **Offline Support:** Add local storage for observations
4. **Optimize Performance:** Implement marker clustering

---

## 🔗 Related Files

- [Backend API Documentation](../../../Backend/docs/API.md)
- [ML Model Documentation](../../../ml_model/docs/)
- [App Integration Review](./INTEGRATION_REVIEW.md)

---

**Last Updated:** January 2026  
**Architecture Version:** 1.0  
**Status:** ✅ Production Ready (with ML conversion pending)
