# TinyML Integration Guide

## Overview

This mobile app integrates an on-device TensorFlow Lite model for real-time road quality classification. The ML pipeline runs entirely on the device and sends only the final classification results to the backend.

## Architecture

```
Sensors (10Hz) → Windowing (2s) → TFLite Inference → Backend API
    ↓                ↓                    ↓               ↓
[ax,ay,az,       [20x7 matrix]      [0,1,2,3]    {lat,lng,quality}
 wx,wy,wz,
 speed]
```

## Components

### 1. Sensor Collection (`sensorService.js`)
- **Purpose**: Collects accelerometer, gyroscope, and location data
- **Sampling Rate**: 10 Hz (100ms intervals)
- **Sensors**:
  - Accelerometer (ax, ay, az)
  - Gyroscope (wx, wy, wz)
  - Location (speed, lat, lng)

### 2. Windowing (`windowService.js`)
- **Purpose**: Buffers sensor readings into 2-second windows
- **Window Size**: 20 readings (2s @ 10Hz)
- **Output**: 20x7 sensor matrix + metadata

### 3. TFLite Inference (`tfliteService.js`)
- **Purpose**: Runs on-device ML inference
- **Model**: Hybrid CNN
- **Input**: 20x7 tensor [batch, time_steps, features]
- **Output**: Integer classification (0-3)
  - 0 = very bad
  - 1 = bad
  - 2 = good
  - 3 = very good

### 4. ML Service (`mlService.js`)
- **Purpose**: Orchestrates the complete pipeline
- **API**:
  - `initialize()` - Setup TensorFlow and load model
  - `startMonitoring()` - Begin continuous monitoring
  - `stopMonitoring()` - Stop monitoring
  - `getLatestResult()` - Get most recent classification

### 5. Observation Service (`observationService.js`)
- **Purpose**: Sends results to backend API
- **API Endpoint**: `POST /api/observations`
- **Payload**: 
  ```json
  {
    "latitude": number,
    "longitude": number,
    "roadQuality": number,
    "speed": number,
    "timestamp": string
  }
  ```

## Installation

### 1. Install Dependencies

```bash
cd mobile-app
npm install
```

Required packages:
- `@tensorflow/tfjs`
- `@tensorflow/tfjs-react-native`
- `expo-sensors`
- `expo-location`
- `expo-gl`
- `expo-file-system`
- `expo-asset`

### 2. Convert TFLite Model

The `.tflite` model must be converted to TensorFlow.js format:

```bash
# Install converter
pip install tensorflowjs

# Convert model
tensorflowjs_converter \
  --input_format=tf_saved_model \
  --output_format=tfjs_graph_model \
  ml_model/src/model/saved_model \
  mobile-app/assets/ml-model/
```

This creates:
- `model.json`
- `group1-shard1of1.bin` (or multiple weight files)

### 3. Place Model Files

Copy the converted files to:
```
mobile-app/assets/ml-model/
├── model.json
└── group1-shard1of1.bin
```

## Usage

### Basic Integration

```javascript
import { mlService } from './src/services/mlService';
import { startObservationCollection } from './src/services/observationService';

// In your app initialization (e.g., App.js or _layout.tsx)
useEffect(() => {
  const setup = async () => {
    try {
      // Initialize ML pipeline
      await mlService.initialize();
      
      // Start continuous monitoring
      await mlService.startMonitoring();
      
      // Start sending observations every 10 seconds
      const cleanup = await startObservationCollection(10);
      
      // Cleanup on unmount
      return cleanup;
    } catch (error) {
      console.error('Setup failed:', error);
    }
  };
  
  const cleanup = setup();
  return () => cleanup?.();
}, []);
```

### Manual Observation

```javascript
import { sendObservation } from './src/services/observationService';

// Send a single observation
const handleSendObservation = async () => {
  try {
    await sendObservation();
    console.log('Observation sent!');
  } catch (error) {
    console.error('Failed:', error);
  }
};
```

### Get Latest Result

```javascript
import { mlService } from './src/services/mlService';

const result = mlService.getLatestResult();
if (result) {
  console.log('Road Quality:', result.roadQuality);
  console.log('Location:', result.latitude, result.longitude);
  console.log('Speed:', result.speed);
}
```

## Data Flow

### Step-by-Step Process

1. **Sensor Collection (10Hz)**
   ```javascript
   {
     ax: 0.12, ay: 9.8, az: 0.05,
     wx: 0.01, wy: -0.02, wz: 0.00,
     speed: 15.5,
     location: { latitude: 40.7128, longitude: -74.0060 }
   }
   ```

2. **Windowing (every 2 seconds)**
   ```javascript
   {
     sensorMatrix: [[ax,ay,az,wx,wy,wz,speed], ...] // 20 rows
     metadata: {
       latitude: 40.7128,
       longitude: -74.0060,
       averageSpeed: 15.2,
       timestamp: "2026-01-23T12:34:56.789Z"
     }
   }
   ```

3. **ML Inference**
   ```javascript
   Input:  [1, 20, 7] tensor
   Output: 2 (classification)
   Label:  "good"
   ```

4. **Backend Submission**
   ```json
   {
     "latitude": 40.7128,
     "longitude": -74.0060,
     "roadQuality": 2,
     "speed": 15.2,
     "timestamp": "2026-01-23T12:34:56.789Z"
   }
   ```

## Backend API Compliance

### Endpoint Contract

**URL**: `POST /api/observations`

**Headers**:
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "latitude": number,     // Required: Device location at window end
  "longitude": number,    // Required: Device location at window end
  "roadQuality": number,  // Required: 0-3 from ML model
  "speed": number,        // Required: Average speed over window (m/s)
  "timestamp": string     // Required: ISO-8601 format
}
```

**STRICT RULES**:
- ❌ DO NOT send raw sensor data
- ❌ DO NOT send windowed arrays
- ❌ DO NOT send accelerometer/gyroscope values
- ✅ ONLY send the 5 fields above

## Permissions

Add to `app.json`:
```json
{
  "expo": {
    "plugins": [
      [
        "expo-location",
        {
          "locationAlwaysAndWhenInUsePermission": "Allow app to use your location for road quality monitoring."
        }
      ],
      [
        "expo-sensors",
        {
          "motionPermission": "Allow app to access motion sensors for road quality detection."
        }
      ]
    ]
  }
}
```

## Performance Considerations

### Memory Management
- Sensors run continuously → small memory footprint
- Windows are processed immediately → no large buffers
- TensorFlow tensors are disposed after inference

### Battery Impact
- 10Hz sensor sampling is efficient
- On-device inference (~50ms) is fast
- No continuous GPS tracking (updates every 100ms)

### Network Usage
- Only sends 5 fields every 10 seconds
- Payload size: ~150 bytes
- Very low bandwidth usage

## Troubleshooting

### Model Not Loading

**Problem**: `Model not found` error

**Solution**:
1. Verify model files exist in `assets/ml-model/`
2. Check that model is converted to TensorFlow.js format
3. Rebuild the app: `expo start --clear`

### Sensors Not Available

**Problem**: `Sensor not available` error

**Solution**:
- Accelerometer/Gyroscope not available in iOS Simulator
- Test on real device
- Check permissions in device settings

### No ML Results

**Problem**: `No ML result available yet`

**Solution**:
- Wait 2 seconds for first window to complete
- Check that monitoring is started
- Verify sensors are collecting data

### Inference Errors

**Problem**: TensorFlow errors during inference

**Solution**:
- Check input tensor shape: `[1, 20, 7]`
- Verify model architecture matches input
- Enable mock inference temporarily

## Development Tips

### Enable Debug Logs
The services already include extensive console logging:
- 🚀 = Starting
- ✅ = Success
- ❌ = Error
- ⚠️ = Warning
- 🔮 = Inference
- 📤 = API Request

### Mock Mode
While developing, use mock inference:
```javascript
// In tfliteService.js
const roadQuality = await tfliteService.runMockInference(sensorMatrix);
```

### Adjust Observation Frequency
```javascript
// Send every 5 seconds instead of 10
await startObservationCollection(5);
```

## Production Checklist

- [ ] TFLite model converted to TensorFlow.js format
- [ ] Model files placed in `assets/ml-model/`
- [ ] All dependencies installed
- [ ] Permissions configured in `app.json`
- [ ] Tested on real device (not simulator)
- [ ] Backend API endpoint configured correctly
- [ ] Authentication token management working
- [ ] Error handling implemented
- [ ] Battery impact tested
- [ ] Network usage optimized

## API Reference

### mlService

```javascript
// Initialize (call once on app start)
await mlService.initialize();

// Start monitoring
await mlService.startMonitoring();

// Stop monitoring
mlService.stopMonitoring();

// Get latest result
const result = mlService.getLatestResult();
// Returns: { roadQuality, latitude, longitude, speed, timestamp }

// Check if ready
mlService.isReady();

// Get label from value
mlService.getRoadQualityLabel(2); // "good"

// Cleanup
mlService.dispose();
```

### observationService

```javascript
// Send single observation
await sendObservation();

// Start continuous collection (returns cleanup function)
const cleanup = await startObservationCollection(10);
cleanup(); // Call to stop

// Stop collection
stopObservationCollection();
```

## File Structure

```
mobile-app/
├── assets/
│   └── ml-model/
│       ├── model.json          # TensorFlow.js model
│       ├── group1-shard1of1.bin # Model weights
│       └── README.md            # Model documentation
├── src/
│   └── services/
│       ├── sensorService.js     # Sensor collection (10Hz)
│       ├── windowService.js     # 2-second windowing
│       ├── tfliteService.js     # TFLite inference
│       ├── mlService.js         # Pipeline orchestration
│       ├── observationService.js # Backend API
│       └── locationService.js   # Legacy (kept for compatibility)
└── docs/
    └── ML_INTEGRATION.md        # This file
```

## Next Steps

1. **Install dependencies**: `npm install` in mobile-app folder
2. **Convert model**: Use `tensorflowjs_converter`
3. **Copy model files**: Place in `assets/ml-model/`
4. **Test sensors**: Run on real device
5. **Verify backend**: Check API responses
6. **Monitor logs**: Watch console for pipeline status

## Support

For issues or questions:
1. Check console logs for detailed error messages
2. Verify all prerequisites are met
3. Test each component individually
4. Review backend API documentation
