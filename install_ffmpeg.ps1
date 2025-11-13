# PowerShell script to auto-install FFmpeg
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FFmpeg Auto-Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ffmpegPath = "$PSScriptRoot\ffmpeg"
$ffmpegExe = "$ffmpegPath\bin\ffmpeg.exe"

# Check if already installed
if (Test-Path $ffmpegExe) {
    Write-Host "FFmpeg is already installed!" -ForegroundColor Green
    Write-Host "Location: $ffmpegExe" -ForegroundColor Gray
    exit 0
}

Write-Host "FFmpeg not found. Installing..." -ForegroundColor Yellow
Write-Host ""

# Create ffmpeg directory
if (-not (Test-Path $ffmpegPath)) {
    New-Item -ItemType Directory -Path $ffmpegPath | Out-Null
}

# Download FFmpeg essentials
$downloadUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$zipPath = "$PSScriptRoot\ffmpeg-essentials.zip"

Write-Host "Downloading FFmpeg..." -ForegroundColor Yellow
Write-Host "URL: $downloadUrl" -ForegroundColor Gray
Write-Host "This may take a few minutes (file is ~80 MB)..." -ForegroundColor Gray
Write-Host ""

try {
    # Download with progress
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
    $ProgressPreference = 'Continue'

    Write-Host "Download complete!" -ForegroundColor Green
    Write-Host ""

    # Extract
    Write-Host "Extracting FFmpeg..." -ForegroundColor Yellow
    Expand-Archive -Path $zipPath -DestinationPath "$PSScriptRoot\temp_ffmpeg" -Force

    # Find the ffmpeg folder inside (it has a version number)
    $extractedFolder = Get-ChildItem "$PSScriptRoot\temp_ffmpeg" -Directory | Select-Object -First 1

    # Move bin folder
    Move-Item "$($extractedFolder.FullName)\bin" "$ffmpegPath\bin" -Force

    # Cleanup
    Remove-Item $zipPath -Force
    Remove-Item "$PSScriptRoot\temp_ffmpeg" -Recurse -Force

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  FFmpeg installed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Location: $ffmpegExe" -ForegroundColor Gray

    # Verify installation
    & $ffmpegExe -version | Select-Object -First 1

    exit 0

} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to install FFmpeg" -ForegroundColor Red
    Write-Host "Error message: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual installation:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Gray
    Write-Host "2. Extract ffmpeg.exe to: $PSScriptRoot" -ForegroundColor Gray
    exit 1
}
