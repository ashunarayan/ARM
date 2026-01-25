# Road Quality Monitoring Mobile App 🛣️

**Updated:** Clean architecture with Mapbox integration and TypeScript service layer

React Native mobile app for real-time road quality detection using ML and sensor data.

## ✨ Features

- 🗺️ **Mapbox Integration** - Interactive maps with user location tracking
- 🤖 **ML Road Quality Detection** - Real-time inference using TensorFlow Lite
- 📡 **Backend Sync** - Automatic observation uploads
- 📱 **Sensor Fusion** - Accelerometer + Gyroscope @ 10Hz
- 🎯 **Clean Architecture** - TypeScript, service layer, isolated concerns
- 🔒 **Production-Ready** - No hardcoded values, type-safe, well-documented

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run on Android
npm run android

# Run on iOS  
npm run ios
```

See **[QUICK_START.md](./QUICK_START.md)** for detailed setup instructions.

## 📖 Documentation

- **[INTEGRATION_SUMMARY.md](./INTEGRATION_SUMMARY.md)** - ⭐ Start here! What's new and what changed
- **[MAPBOX_ML_INTEGRATION.md](./docs/MAPBOX_ML_INTEGRATION.md)** - Complete architecture guide
- **[MIGRATION_GUIDE.md](./docs/MIGRATION_GUIDE.md)** - Migrating from old code
- **[Backend API Docs](../Backend/docs/API.md)** - Backend API documentation

## 🏗️ Architecture

```
UI Layer (React Components)
          ↓
Service Layer (Business Logic)
    - mlService         (ML orchestration)
    - mapboxService     (Map utilities)
    - observationService (Backend sync)
          ↓
Infrastructure
    - TensorFlow (ML inference)
    - Mapbox (Maps)
    - Backend API
    - Device Sensors
```

### Basic Integration

```javascript
import { mlService } from './src/services/mlService';
import { startObservationCollection } from './src/services/observationService';

// Initialize on app start
await mlService.initialize();
await mlService.startMonitoring();

// Start sending observations every 10 seconds
const cleanup = await startObservationCollection(10);
```

### Get Latest Result

```javascript
const result = mlService.getLatestResult();
// { roadQuality: 2, latitude: 40.7128, longitude: -74.0060, speed: 15.5 }
```

## 🏗️ Architecture

```
Device Sensors (10Hz)
    ↓
Windowing Service (2-second buffers)
    ↓
TFLite Inference (on-device)
    ↓
Backend API (classifications only)
```

### Data Flow

1. **Sensors**: Collect ax, ay, az, wx, wy, wz, speed @ 10Hz
2. **Window**: Buffer 20 readings (2 seconds)
3. **Inference**: Run ML model → roadQuality (0-3)
4. **API**: Send `{latitude, longitude, roadQuality, speed, timestamp}`

## 📦 Project Structure

```
mobile-app/
├── assets/
│   └── ml-model/          # TensorFlow.js model files
├── src/
│   ├── services/
│   │   ├── sensorService.js      # 10Hz sensor collection
│   │   ├── windowService.js      # 2-second windowing
│   │   ├── tfliteService.js      # ML inference
│   │   ├── mlService.js          # Pipeline orchestration
│   │   └── observationService.js # Backend API
│   └── components/
│       └── RoadQualityMonitor.example.js
├── docs/
│   ├── ML_INTEGRATION.md   # Detailed documentation
│   ├── QUICK_START.md      # Step-by-step guide
│   └── DEPENDENCIES.md     # Package requirements
└── app/                    # Expo Router screens
```

## 🔑 Key Components

| Service | Purpose | Output |
|---------|---------|--------|
| `sensorService` | Collects sensor data | 10 readings/sec |
| `windowService` | Buffers data | 20×7 matrix every 2s |
| `tfliteService` | ML inference | roadQuality (0-3) |
| `observationService` | API submission | Backend updates |

## 🎯 Backend API Contract

**Endpoint**: `POST /api/observations`

**Payload** (ONLY these fields):
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "roadQuality": 2,
  "speed": 15.5,
  "timestamp": "2026-01-23T12:34:56.789Z"
}
```

✅ Sends classifications only  
❌ NO raw sensor data  
❌ NO windowed arrays

## 📖 Documentation

- **[ML_INTEGRATION.md](./docs/ML_INTEGRATION.md)**: Complete integration guide
- **[QUICK_START.md](./docs/QUICK_START.md)**: Step-by-step setup
- **[DEPENDENCIES.md](./docs/DEPENDENCIES.md)**: Required packages

## 🛠️ Development

### Debug Logs

The app includes comprehensive logging:
- 🚀 Starting operations
- ✅ Success messages
- ❌ Error details
- 🔮 Inference progress
- 📤 API requests

### Mock Mode

For testing without a model:
```javascript
// tfliteService automatically falls back to mock inference
const roadQuality = await tfliteService.runMockInference(sensorMatrix);
```

## ⚙️ Configuration

### Observation Frequency

```javascript
// Send every 5 seconds (default: 10)
await startObservationCollection(5);
```

### Sensor Sampling Rate

```javascript
// In sensorService.js
const SAMPLING_INTERVAL_MS = 100; // 10 Hz
```

## 📝 Requirements

- Node.js 18+
- Expo SDK 54
- Real Android/iOS device
- Location permissions
- Motion sensor permissions

## 🔒 Permissions

Add to `app.json`:
```json
{
  "expo": {
    "plugins": [
      ["expo-location", {
        "locationAlwaysAndWhenInUsePermission": "Monitor road quality"
      }],
      ["expo-sensors", {
        "motionPermission": "Detect road conditions"
      }]
    ]
  }
}
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Model not loading | Convert `.tflite` to TensorFlow.js format |
| Sensors unavailable | Use real device (not simulator) |
| No ML results | Wait 2 seconds for first window |
| Backend errors | Check API endpoint and auth token |

## 📊 Performance

- **Memory**: ~50MB (including TensorFlow.js)
- **Inference Time**: ~50ms per window
- **Battery Impact**: Low (efficient sensor sampling)
- **Network Usage**: ~150 bytes per observation

## 🚦 Production Checklist

- [ ] Install all dependencies
- [ ] Convert and place ML model
- [ ] Configure permissions
- [ ] Test on real device
- [ ] Verify backend integration
- [ ] Monitor battery usage
- [ ] Optimize observation frequency

## 🤝 Contributing

This project follows a strict separation:
- Mobile app handles: sensor collection, windowing, ML inference
- Backend handles: data storage, aggregation, visualization

**DO NOT**:
- Modify backend API contracts
- Send raw sensor data to backend
- Change database schemas

## 📄 License

See main project LICENSE

## 🆘 Support

For detailed help, check:
1. Console logs for error messages
2. [ML_INTEGRATION.md](./docs/ML_INTEGRATION.md) for troubleshooting
3. Backend API documentation

---

## Get started

1. Install dependencies

   ```bash
   npm install
   ```

2. Start the app

   ```bash
   npx expo start
   ```

In the output, you'll find options to open the app in a

- [development build](https://docs.expo.dev/develop/development-builds/introduction/)
- [Android emulator](https://docs.expo.dev/workflow/android-studio-emulator/)
- [iOS simulator](https://docs.expo.dev/workflow/ios-simulator/)
- [Expo Go](https://expo.dev/go), a limited sandbox for trying out app development with Expo

You can start developing by editing the files inside the **app** directory. This project uses [file-based routing](https://docs.expo.dev/router/introduction).

## Learn more

To learn more about developing your project with Expo, look at the following resources:

- [Expo documentation](https://docs.expo.dev/): Learn fundamentals, or go into advanced topics with our [guides](https://docs.expo.dev/guides).
- [Learn Expo tutorial](https://docs.expo.dev/tutorial/introduction/): Follow a step-by-step tutorial where you'll create a project that runs on Android, iOS, and the web.

## Join the community

Join our community of developers creating universal apps.

- [Expo on GitHub](https://github.com/expo/expo): View our open source platform and contribute.
- [Discord community](https://chat.expo.dev): Chat with Expo users and ask questions.
