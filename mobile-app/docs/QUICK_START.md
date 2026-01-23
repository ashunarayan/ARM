# Quick Start: TinyML Road Quality Detection

## Prerequisites

✅ Node.js and npm installed  
✅ Expo CLI installed (`npm install -g expo-cli`)  
✅ Real Android/iOS device (simulators lack sensors)  
✅ TensorFlow Lite model trained

## Step 1: Install Dependencies

```bash
cd mobile-app
npm install
```

This installs:
- TensorFlow.js packages
- Expo sensor modules
- Location services

## Step 2: Convert ML Model

Your `.tflite` model must be converted to TensorFlow.js format:

```bash
# Install converter
pip install tensorflowjs

# Convert (if you have a SavedModel)
tensorflowjs_converter \
  --input_format=tf_saved_model \
  --output_format=tfjs_graph_model \
  ml_model/src/model/saved_model \
  mobile-app/assets/ml-model/

# OR convert from Keras (.h5)
tensorflowjs_converter \
  --input_format=keras \
  ml_model/src/model/model.h5 \
  mobile-app/assets/ml-model/
```

**Alternative**: If conversion is complex, the app includes mock inference for testing.

## Step 3: Place Model Files

After conversion, you should have:
```
mobile-app/assets/ml-model/
├── model.json
└── group1-shard1of1.bin
```

## Step 4: Update App Layout

Add the ML pipeline to your app's main layout:

**File**: `mobile-app/app/_layout.tsx`

```typescript
import { useEffect } from 'react';
import { mlService } from '../src/services/mlService';
import { startObservationCollection } from '../src/services/observationService';

export default function RootLayout() {
  useEffect(() => {
    let cleanup: (() => void) | undefined;

    const initML = async () => {
      try {
        console.log('🚀 Initializing ML pipeline...');
        
        // Initialize ML service
        await mlService.initialize();
        
        // Start monitoring
        await mlService.startMonitoring();
        
        // Start sending observations every 10 seconds
        cleanup = await startObservationCollection(10);
        
        console.log('✅ ML pipeline ready');
      } catch (error) {
        console.error('❌ ML initialization failed:', error);
      }
    };

    initML();

    return () => {
      if (cleanup) cleanup();
    };
  }, []);

  return (
    // Your existing layout JSX
  );
}
```

## Step 5: Configure Permissions

Update `mobile-app/app.json`:

```json
{
  "expo": {
    "plugins": [
      [
        "expo-location",
        {
          "locationAlwaysAndWhenInUsePermission": "Allow app to monitor road quality using your location."
        }
      ],
      [
        "expo-sensors",
        {
          "motionPermission": "Allow app to detect road quality using motion sensors."
        }
      ]
    ],
    "ios": {
      "infoPlist": {
        "NSLocationWhenInUseUsageDescription": "This app needs location access for road quality monitoring.",
        "NSMotionUsageDescription": "This app uses motion sensors to detect road conditions."
      }
    },
    "android": {
      "permissions": [
        "ACCESS_COARSE_LOCATION",
        "ACCESS_FINE_LOCATION",
        "BODY_SENSORS"
      ]
    }
  }
}
```

## Step 6: Run the App

```bash
# Start Expo
npm start

# On your device:
# - Scan QR code with Expo Go app
# - OR build standalone app
```

## Step 7: Test the Pipeline

1. **Check Logs**: Watch console for pipeline status
   ```
   🚀 Initializing ML pipeline...
   ✅ All sensors available
   ✅ Model loaded successfully
   ✅ ML pipeline ready
   🪟 Window ready (20 readings)
   🔮 Running inference...
   ✅ Inference complete in 45ms
   📊 Predicted road quality: 2
   📤 Observation SENT
   ```

2. **Verify Data**: Check backend for observations
   ```bash
   # Should see POST requests to /api/observations
   # With payload: {latitude, longitude, roadQuality, speed, timestamp}
   ```

## Troubleshooting

### "Model not found"
- Model files missing or not converted
- Use mock inference temporarily: Already enabled in `tfliteService.js`
- Check `assets/ml-model/` folder

### "Sensor not available"
- Running on iOS Simulator (sensors not available)
- Solution: Test on real device

### "No ML result available yet"
- Normal for first 2 seconds
- Wait for window to complete (20 readings)

### Backend 400/500 errors
- Check API endpoint in `config.js`
- Verify authentication token
- Check payload matches backend schema exactly

## Backend API Contract

**CRITICAL**: Only these 5 fields are sent:

```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "roadQuality": 2,
  "speed": 15.5,
  "timestamp": "2026-01-23T12:34:56.789Z"
}
```

✅ Correct: Backend receives classification result  
❌ Wrong: Sending raw sensor arrays

## Pipeline Overview

```
Device Sensors → Buffer (2s) → ML Model → Backend
    10Hz           20 readings    0-3      API
```

**Timeline**:
- t=0.0s: Start collecting
- t=2.0s: First window ready → Inference → Send to backend
- t=2.1s: Second window ready → Inference → Send to backend
- ...continues every 100ms

**Observation Frequency**:
- Inference: Every 100ms (after initial 2s)
- API Submission: Every 10s (configurable)

## Next Steps

1. ✅ **Test on real device**: Verify sensors work
2. ✅ **Monitor logs**: Check pipeline status
3. ✅ **Verify backend**: Confirm observations arrive
4. ✅ **Optimize frequency**: Adjust observation interval
5. ✅ **Production build**: Create standalone app

## Code Examples

### Manual Observation

```javascript
import { sendObservation } from './src/services/observationService';

// Send observation on button press
<Button 
  title="Report Road Quality" 
  onPress={() => sendObservation()} 
/>
```

### Get Current Result

```javascript
import { mlService } from './src/services/mlService';

const result = mlService.getLatestResult();
console.log(`Road is ${mlService.getRoadQualityLabel(result?.roadQuality)}`);
```

### Stop/Start Monitoring

```javascript
// Stop
mlService.stopMonitoring();

// Restart
await mlService.startMonitoring();
```

## Files Created

| File | Purpose |
|------|---------|
| `sensorService.js` | Collects accelerometer, gyroscope, location |
| `windowService.js` | Buffers 2-second windows |
| `tfliteService.js` | Runs ML inference |
| `mlService.js` | Orchestrates pipeline |
| `observationService.js` | Sends to backend |

## Production Checklist

- [ ] Dependencies installed
- [ ] Model converted and placed
- [ ] Permissions configured
- [ ] Tested on real device
- [ ] Backend API working
- [ ] Logs monitored
- [ ] Battery impact acceptable
- [ ] Network usage optimized

---

**Need Help?** Check [ML_INTEGRATION.md](./ML_INTEGRATION.md) for detailed documentation.
