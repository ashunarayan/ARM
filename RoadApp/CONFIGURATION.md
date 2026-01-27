## CONFIGURATION INSTRUCTIONS

Before building the app, you MUST configure the following:

### 1. Firebase Setup

1. Go to Firebase Console: https://console.firebase.google.com
2. Create a new project or select existing one
3. Add an Android app with package name: `com.roadapp`
4. Download `google-services.json`
5. Place it at: `RoadApp/android/app/google-services.json`
6. Update Firebase config in `RoadApp/src/config/index.ts`:

```typescript
export const FIREBASE_CONFIG = {
  apiKey: 'YOUR_ACTUAL_API_KEY',
  authDomain: 'your-project-id.firebaseapp.com',
  projectId: 'your-project-id',
  storageBucket: 'your-project-id.appspot.com',
  messagingSenderId: 'YOUR_SENDER_ID',
  appId: 'YOUR_APP_ID',
};
```

### 2. Mapbox Setup

1. Create account at: https://account.mapbox.com
2. Get your PUBLIC access token
3. Get your SECRET download token
4. Update in `RoadApp/src/config/index.ts`:

```typescript
export const MAPBOX_ACCESS_TOKEN = 'pk.YOUR_ACTUAL_PUBLIC_TOKEN';
```

5. Update in `RoadApp/android/gradle.properties`:

```
MAPBOX_DOWNLOADS_TOKEN=sk.YOUR_ACTUAL_SECRET_TOKEN
```

### 3. Backend URL

Update in `RoadApp/src/config/index.ts`:

```typescript
export const BACKEND_URL = __DEV__ 
  ? Platform.OS === 'android' ? 'http://10.0.2.2:3000' : 'http://localhost:3000'
  : 'https://your-production-backend.com';
```

For local development on Android emulator, use `http://10.0.2.2:3000`
For physical device, use your computer's IP address, e.g., `http://192.168.1.100:3000`

### 4. Build Commands

After configuration:

```bash
cd RoadApp
npx react-native run-android
```

For APK:

```bash
cd RoadApp/android
./gradlew assembleDebug
```

APK will be at: `RoadApp/android/app/build/outputs/apk/debug/app-debug.apk`

### 5. Verification Checklist

- [ ] `google-services.json` exists in `android/app/`
- [ ] Firebase config updated in `src/config/index.ts`
- [ ] Mapbox public token in `src/config/index.ts`
- [ ] Mapbox secret token in `android/gradle.properties`
- [ ] Backend URL configured for your environment
- [ ] TFLite model exists at `src/assets/model.tflite`
