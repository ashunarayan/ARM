# Pre-Build Verification Script

Write-Host "=== RoadApp Pre-Build Verification ===" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check 1: google-services.json
Write-Host "1. Checking google-services.json..." -NoNewline
if (Test-Path "android/app/google-services.json") {
    $content = Get-Content "android/app/google-services.json" -Raw
    if ($content -match '"package_name": "com.roadapp"') {
        Write-Host " PASS" -ForegroundColor Green
    } else {
        Write-Host " FAIL - Wrong package name" -ForegroundColor Red
        $allGood = $false
    }
} else {
    Write-Host " FAIL - File missing" -ForegroundColor Red
    $allGood = $false
}

# Check 2: Firebase config
Write-Host "2. Checking Firebase config..." -NoNewline
$config = Get-Content "src/config/index.ts" -Raw
if ($config -match "YOUR_FIREBASE_API_KEY") {
    Write-Host " FAIL - Not configured" -ForegroundColor Red
    $allGood = $false
} else {
    Write-Host " PASS" -ForegroundColor Green
}

# Check 3: Mapbox public token
Write-Host "3. Checking Mapbox public token..." -NoNewline
if ($config -match "YOUR_MAPBOX_ACCESS_TOKEN") {
    Write-Host " FAIL - Not configured" -ForegroundColor Red
    $allGood = $false
} else {
    Write-Host " PASS" -ForegroundColor Green
}

# Check 4: Mapbox secret token
Write-Host "4. Checking Mapbox secret token..." -NoNewline
$gradleProps = Get-Content "android/gradle.properties" -Raw
if ($gradleProps -match "YOUR_SECRET_MAPBOX_TOKEN") {
    Write-Host " FAIL - Not configured" -ForegroundColor Red
    $allGood = $false
} else {
    Write-Host " PASS" -ForegroundColor Green
}

# Check 5: TFLite model
Write-Host "5. Checking TFLite model..." -NoNewline
if (Test-Path "src/assets/model.tflite") {
    Write-Host " PASS" -ForegroundColor Green
} else {
    Write-Host " FAIL - File missing" -ForegroundColor Red
    $allGood = $false
}

# Check 6: Node modules
Write-Host "6. Checking node_modules..." -NoNewline
if (Test-Path "node_modules") {
    Write-Host " PASS" -ForegroundColor Green
} else {
    Write-Host " FAIL - Run npm install" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""
if ($allGood) {
    Write-Host "=== All checks passed! Ready to build. ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Run: npx react-native run-android" -ForegroundColor Cyan
} else {
    Write-Host "=== Configuration incomplete! ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please complete the configuration steps in SETUP_GUIDE.md" -ForegroundColor Yellow
}
