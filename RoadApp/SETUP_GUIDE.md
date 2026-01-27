# RoadApp - Setup Guide

## Critical Setup Steps

### 1. Firebase Configuration

**Step 1:** Create/Select Firebase Project
- Go to https://console.firebase.google.com
- Create a new project or select existing
- Enable Email/Password authentication in Authentication > Sign-in methods

**Step 2:** Add Android App
- In Project Settings, add Android app
- Package name: `com.roadapp`
- Download `google-services.json`

**Step 3:** Place Firebase Config
- Copy `google-services.json` to: `android/app/google-services.json`

**Step 4:** Update App Config
Edit `src/config/index.ts` with your Firebase credentials:
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

### 2. Mapbox Configuration

**Step 1:** Get Mapbox Tokens
- Create account at https://account.mapbox.com
- Get PUBLIC access token (starts with `pk.`)
- Get SECRET download token (starts with `sk.`)

**Step 2:** Update Configs
Edit `src/config/index.ts`:
```typescript
export const MAPBOX_ACCESS_TOKEN = 'pk.YOUR_ACTUAL_TOKEN';
```

Edit `android/gradle.properties`:
```
MAPBOX_DOWNLOADS_TOKEN=sk.YOUR_ACTUAL_SECRET_TOKEN
```

### 3. Backend URL Configuration

Edit `src/config/index.ts`:

For Android Emulator:
```typescript
export const BACKEND_URL = 'http://10.0.2.2:3000';
```

For Real Device (use your computer's local IP):
```typescript
export const BACKEND_URL = 'http://192.168.1.XXX:3000';
```

For Production:
```typescript
export const BACKEND_URL = 'https://your-backend-domain.com';
```

### 4. Build Commands

**Run on Android Device/Emulator:**
```bash
npx react-native run-android
```

**Build Debug APK:**
```bash
cd android
./gradlew assembleDebug
```

APK location: `android/app/build/outputs/apk/debug/app-debug.apk`

**Build Release APK (requires keystore):**
```bash
cd android
./gradlew assembleRelease
```

### 5. Verification Checklist

Before building:
- [ ] `google-services.json` exists in `android/app/`
- [ ] Firebase config updated in `src/config/index.ts`
- [ ] Mapbox public token in `src/config/index.ts`
- [ ] Mapbox secret token in `android/gradle.properties`
- [ ] Backend URL configured correctly
- [ ] TFLite model exists at `src/assets/model.tflite`
- [ ] Backend server is running (for testing)

### 6. Common Issues

**Issue:** Build fails with "google-services.json not found"
**Solution:** Ensure file is in `android/app/` directory

**Issue:** Mapbox tiles don't load
**Solution:** Verify public token is correct and has proper permissions

**Issue:** Can't connect to backend from device
**Solution:** Use device IP, not localhost. Ensure firewall allows connections.

**Issue:** ML model fails to load
**Solution:** Verify `model.tflite` exists in `src/assets/`

### 7. Testing Backend Connection

From the app, if observation submission fails:
1. Check Backend URL in config
2. Ensure Backend is running
3. Check device/emulator network connectivity
4. Verify Firebase token is being sent correctly

### 8. Production Deployment

For production:
1. Generate release keystore
2. Update `android/app/build.gradle` with keystore config
3. Update BACKEND_URL to production URL
4. Build release APK
5. Test thoroughly on real devices
