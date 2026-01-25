# Quick Start Guide

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Expo CLI
- Android Studio (for Android) or Xcode (for iOS)

### Installation

```bash
cd mobile-app
npm install
```

### Configuration

1. **Mapbox Token**: Already set in `src/.env`
   ```
   MAPBOX_ACCESS_TOKEN=pk.eyJ1...
   ```

2. **Backend URL**: Update in `src/config/env.ts` if needed
   ```typescript
   API: {
     BASE_URL: 'http://YOUR_BACKEND_IP:5000/api',
   }
   ```

### Running the App

```bash
# Start development server
npm start

# Run on Android
npm run android

# Run on iOS
npm run ios
```

---

## 📱 Using Mapbox & ML

### 1. App automatically initializes on startup

No manual initialization needed - handled in `app/_layout.tsx`

### 2. Use MapView component

```typescript
import { MapView } from './src/components/MapView';

<MapView
  markers={markers}
  showUserLocation={true}
/>
```

### 3. Start ML monitoring

```typescript
import { mlService, observationService } from './src/services';

// Start monitoring
await mlService.startMonitoring((result) => {
  console.log('Road quality:', result.roadQuality);
  
  // Send to backend
  await observationService.sendObservation(result);
});

// Stop monitoring
mlService.stopMonitoring();
```

---

## 📖 Documentation

- [Complete Architecture Guide](./docs/MAPBOX_ML_INTEGRATION.md)
- [Migration Guide](./docs/MIGRATION_GUIDE.md)
- [Backend API](../Backend/docs/API.md)

---

## 🔧 Project Structure

```
src/
├── config/       # Configuration & environment
├── types/        # TypeScript types
├── services/     # Business logic (ML, API, Mapbox)
├── api/          # HTTP client
├── components/   # Reusable UI components
└── screens/      # Screen components
```

---

## ✅ Key Features

- ✅ Mapbox maps with user location
- ✅ ML road quality detection (10Hz sensors, 2s windows)
- ✅ Automatic backend sync
- ✅ TypeScript throughout
- ✅ Clean architecture
- ✅ No hardcoded tokens

---

## 🆘 Troubleshooting

### Map not showing?
Check Mapbox token in `src/.env`

### ML not working?
Check console for initialization errors

### Can't reach backend?
Update `BASE_URL` in `src/config/env.ts`

---

**Last Updated:** January 2026
