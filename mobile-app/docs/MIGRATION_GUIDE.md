# Migration Guide: Old ML Integration → New Architecture

## 📋 Overview

This guide explains how to migrate from the old ML integration to the new clean architecture.

---

## 🔄 What Changed?

### Before (Old Structure)

```
mobile-app/
├── src/
│   ├── services/
│   │   ├── mlService.js          # Mixed concerns
│   │   ├── tfliteService.js      # JS, no types
│   │   └── observationService.js
│   └── api/
│       └── apiClient.js          # Basic API client
```

**Issues:**
- ❌ JavaScript (no type safety)
- ❌ Mixed concerns in services
- ❌ No centralized initialization
- ❌ No Mapbox integration
- ❌ Hardcoded values

### After (New Structure)

```
mobile-app/
├── src/
│   ├── config/
│   │   └── env.ts                # ✅ Centralized config
│   ├── types/
│   │   └── index.ts              # ✅ Shared types
│   ├── services/
│   │   ├── appInitializer.ts     # ✅ App initialization
│   │   ├── mapboxService.ts      # ✅ Mapbox support
│   │   ├── ml.ts                 # ✅ Clean ML orchestrator
│   │   ├── tflite.ts             # ✅ TypeScript inference
│   │   └── observation.ts        # ✅ Typed API calls
│   ├── api/
│   │   └── client.ts             # ✅ Typed HTTP client
│   └── components/
│       └── MapView.tsx           # ✅ Reusable map
```

**Benefits:**
- ✅ TypeScript throughout
- ✅ Separated concerns
- ✅ Centralized config
- ✅ Mapbox integration
- ✅ Production-ready patterns

---

## 🔧 Migration Steps

### Step 1: Update Imports

**Old:**
```javascript
import { mlService } from './services/mlService';
import { getRoadQualityFromML } from './services/mlService';
```

**New:**
```typescript
import { mlService } from './services/ml';
// getRoadQualityFromML is deprecated - use mlService.getLatestResult()
```

### Step 2: Initialize App Services

**Old:**
```javascript
// No centralized initialization
await mlService.initialize();
```

**New:**
```typescript
// In app/_layout.tsx
import { initializeApp } from '../src/services/appInitializer';

await initializeApp();
// Initializes both Mapbox and ML automatically
```

### Step 3: Use ML Service with Callbacks

**Old:**
```javascript
await mlService.startMonitoring();

// Later, poll for results
const result = mlService.getLatestResult();
```

**New:**
```typescript
// Register callback for real-time results
await mlService.startMonitoring((result) => {
  console.log('Quality:', result.roadQuality);
  console.log('Location:', result.location);
  
  // Send to backend
  await observationService.sendObservation(result);
});
```

### Step 4: Update API Client

**Old:**
```javascript
import { apiRequest } from '../api/apiClient';

const data = await apiRequest('/observations', 'POST', payload);
```

**New:**
```typescript
import { apiRequest } from '../api/client';

const data = await apiRequest<ResponseType>('/observations', {
  method: 'POST',
  body: payload,
});
```

### Step 5: Use MapView Component

**Old:**
```javascript
// No map component
// Manual Mapbox setup
```

**New:**
```typescript
import { MapView } from '../src/components/MapView';

<MapView
  markers={roadMarkers}
  showUserLocation={true}
  onLocationChange={(location) => handleLocation(location)}
/>
```

---

## 📝 API Changes

### ML Service

| Old API | New API | Notes |
|---------|---------|-------|
| `mlService.initialize()` | `initializeApp()` | Use app initializer |
| `mlService.startMonitoring()` | `mlService.startMonitoring(callback)` | Now takes callback |
| `getRoadQualityFromML()` | `mlService.getLatestResult()` | Returns full result object |
| N/A | `mlService.onResult(callback)` | Add result listener |
| N/A | `mlService.isReady()` | Check initialization |
| N/A | `mlService.isMonitoring()` | Check monitoring state |

### Observation Service

| Old API | New API | Notes |
|---------|---------|-------|
| `observationService.send()` | `observationService.sendObservation(result)` | Clearer name |
| N/A | `observationService.sendQueuedObservations()` | Retry failed |
| N/A | `observationService.getQueueSize()` | Check queue |

---

## 🔀 Code Migration Examples

### Example 1: Basic Monitoring

**Old:**
```javascript
const MonitorScreen = () => {
  const startMonitoring = async () => {
    await mlService.initialize();
    await mlService.startMonitoring();
    
    // Poll for results
    setInterval(() => {
      const result = mlService.getLatestResult();
      if (result) {
        console.log(result);
      }
    }, 1000);
  };
  
  return <Button onPress={startMonitoring} />;
};
```

**New:**
```typescript
const MonitorScreen = () => {
  const [result, setResult] = useState<MLInferenceResult | null>(null);
  
  const startMonitoring = async () => {
    // No need to initialize - done in _layout.tsx
    await mlService.startMonitoring((result) => {
      setResult(result); // Real-time updates
    });
  };
  
  return <Button onPress={startMonitoring} />;
};
```

### Example 2: Sending Observations

**Old:**
```javascript
const sendObservation = async () => {
  const result = mlService.getLatestResult();
  
  await fetch('http://...', {
    method: 'POST',
    body: JSON.stringify({
      latitude: result.latitude,
      longitude: result.longitude,
      roadQuality: result.roadQuality,
    }),
  });
};
```

**New:**
```typescript
const sendObservation = async (result: MLInferenceResult) => {
  // Observation service handles everything
  await observationService.sendObservation(result);
  
  // Or automatically in ML callback
  await mlService.startMonitoring((result) => {
    observationService.sendObservation(result); // Automatic
  });
};
```

### Example 3: Map Integration

**Old:**
```javascript
// No map support
```

**New:**
```typescript
const MapScreen = () => {
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  
  useEffect(() => {
    mlService.startMonitoring((result) => {
      // Add marker for each result
      setMarkers(prev => [...prev, {
        id: `${result.timestamp}`,
        coordinate: [result.location.longitude, result.location.latitude],
        quality: result.roadQuality,
        timestamp: result.timestamp,
      }]);
    });
  }, []);
  
  return <MapView markers={markers} />;
};
```

---

## ⚠️ Breaking Changes

### 1. File Locations

```
❌ src/services/mlService.js     → ✅ src/services/ml.ts
❌ src/services/tfliteService.js → ✅ src/services/tflite.ts
❌ src/api/apiClient.js          → ✅ src/api/client.ts
```

### 2. Type Changes

```typescript
// Old (no types)
const result = mlService.getLatestResult();
// result.roadQuality, result.latitude, result.longitude

// New (typed)
const result: MLInferenceResult | null = mlService.getLatestResult();
// result.roadQuality, result.location.latitude, result.location.longitude
```

### 3. Callback Pattern

```typescript
// Old: Polling
setInterval(() => {
  const result = mlService.getLatestResult();
}, 1000);

// New: Event-driven
mlService.startMonitoring((result) => {
  // Called automatically every 2 seconds
});
```

---

## 🧹 Cleanup Old Files

After migration, you can safely remove:

```
❌ src/services/mlService.js       # Replaced by ml.ts
❌ src/services/tfliteService.js   # Replaced by tflite.ts
❌ src/api/apiClient.js            # Replaced by client.ts
```

**Keep these:**
- ✅ `src/services/sensorService.js` (still used)
- ✅ `src/services/windowService.js` (still used)
- ✅ `src/services/auth.js` (auth logic)

---

## ✅ Migration Checklist

- [ ] Update `app/_layout.tsx` with `initializeApp()`
- [ ] Replace old imports with new ones
- [ ] Update ML service calls to use callbacks
- [ ] Update API client calls with new syntax
- [ ] Add MapView component to screens
- [ ] Test ML monitoring
- [ ] Test Mapbox rendering
- [ ] Test backend observations
- [ ] Remove old service files
- [ ] Update documentation

---

## 🆘 Troubleshooting

### "ML Service not ready"

**Solution:** Ensure `initializeApp()` is called in `app/_layout.tsx`

```typescript
// In app/_layout.tsx
import { initializeApp } from '../src/services/appInitializer';

useEffect(() => {
  initializeApp();
}, []);
```

### "Mapbox access token not found"

**Solution:** Check `src/.env` file

```
MAPBOX_ACCESS_TOKEN=pk.eyJ1...
```

### Type errors

**Solution:** Install TypeScript types

```bash
npm install --save-dev @types/react @types/react-native
```

---

## 📚 Additional Resources

- [Architecture Documentation](./MAPBOX_ML_INTEGRATION.md)
- [Backend API](../../../Backend/docs/API.md)
- [ML Model Details](../../../ml_model/docs/)

---

**Migration Status:** ✅ Complete  
**Last Updated:** January 2026
