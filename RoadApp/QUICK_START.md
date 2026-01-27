# Quick Start - RoadApp

## First Time Setup (REQUIRED)

### 1. Install Dependencies
```bash
cd RoadApp
npm install
```

### 2. Configure Firebase
1. Get `google-services.json` from Firebase Console
2. Place it in: `android/app/google-services.json`
3. Update `src/config/index.ts` with Firebase credentials

### 3. Configure Mapbox
1. Get tokens from https://account.mapbox.com
2. Update `src/config/index.ts` with public token
3. Update `android/gradle.properties` with secret token

### 4. Configure Backend
Update `src/config/index.ts` with backend URL:
- Emulator: `http://10.0.2.2:3000`
- Real device: `http://YOUR_LOCAL_IP:3000`

### 5. Verify Setup
```bash
npm run verify
```

## Running the App

### Start Metro Bundler
```bash
npm start
```

### Run on Android (new terminal)
```bash
npm run android
```

## Building APK

### Debug APK
```bash
cd android
./gradlew assembleDebug
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`

## Need Help?

- Configuration issues → See `SETUP_GUIDE.md`
- Architecture details → See `PROJECT_SUMMARY.md`
- Full documentation → See `CONFIGURATION.md`

## Common Commands

```bash
# Verify configuration
npm run verify

# Run linter
npm run lint

# Clean build
cd android && ./gradlew clean && cd ..

# Rebuild app
npm run android

# View logs
npx react-native log-android
```

## Troubleshooting

**Can't connect to backend?**
- Check BACKEND_URL in src/config/index.ts
- Ensure backend is running
- For device: use computer's local IP, not localhost

**Build fails?**
- Run `npm run verify` to check configuration
- Ensure google-services.json exists
- Check Mapbox tokens are set

**Map doesn't render?**
- Verify Mapbox public token
- Check network connectivity
- Ensure token has proper permissions

**ML inference fails?**
- Check model.tflite exists in src/assets/
- View logs: `npx react-native log-android`
