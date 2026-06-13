# SafarnamaGPT - Build Android APK
# Run from the 'Safarnama Tourism App' folder: .\build_apk.ps1

$ErrorActionPreference = "Stop"

# -- 1. Locate Flutter SDK -----------------------------------------------------
$flutter = Get-Command flutter -ErrorAction SilentlyContinue
if (-not $flutter) {
    # Common install paths
    $candidates = @(
        "$env:USERPROFILE\flutter\bin\flutter.bat",
        "C:\flutter\bin\flutter.bat",
        "C:\src\flutter\bin\flutter.bat",
        "$env:LOCALAPPDATA\flutter\bin\flutter.bat"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $flutter = $c; break }
    }
}
if (-not $flutter) {
    Write-Host ""
    Write-Host "Flutter SDK not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Flutter from: https://docs.flutter.dev/get-started/install/windows"
    Write-Host "Then re-run this script."
    Write-Host ""
    exit 1
}
$flutterCmd = if ($flutter -is [System.Management.Automation.CommandInfo]) { "flutter" } else { $flutter }

Write-Host "Flutter found: $flutterCmd" -ForegroundColor Green

# -- 2. Get dependencies -------------------------------------------------------
Write-Host "`nInstalling packages..." -ForegroundColor Cyan
& $flutterCmd pub get

# -- 3. Build APK -------------------------------------------------------------
Write-Host "`nBuilding release APK..." -ForegroundColor Cyan
& $flutterCmd build apk --release

# -- 4. Done -------------------------------------------------------------------
$apkPath = "build\app\outputs\flutter-apk\app-release.apk"
if (Test-Path $apkPath) {
    $size = [math]::Round((Get-Item $apkPath).Length / 1MB, 1)
    Write-Host ""
    Write-Host "APK built successfully! ($size MB)" -ForegroundColor Green
    Write-Host "Location: $(Resolve-Path $apkPath)"
    Write-Host ""
    Write-Host "Transfer to your Android phone and install it." -ForegroundColor Yellow
    Write-Host "Make sure 'Install from unknown sources' is enabled in Android settings."
} else {
    Write-Host "Build may have failed - APK not found at $apkPath" -ForegroundColor Red
}
