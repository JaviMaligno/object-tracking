@echo off
echo ========================================
echo   Video Converter for OpenCV
echo ========================================
echo.

REM Check if ffmpeg is installed
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo FFmpeg is not installed or not in PATH
    echo.
    echo Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
    echo.
    echo After downloading:
    echo   1. Extract the ZIP file
    echo   2. Copy ffmpeg.exe to this folder
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

echo FFmpeg detected
ffmpeg -version | findstr "ffmpeg version"
echo.

REM Find the video
set VIDEO_PATH=
if exist "IMG_3048_con_Arjona.mov" (
    set VIDEO_PATH=IMG_3048_con_Arjona.mov
) else if exist "..\IMG_3048_con_Arjona.mov" (
    set VIDEO_PATH=..\IMG_3048_con_Arjona.mov
) else (
    echo Video 'IMG_3048_con_Arjona.mov' not found
    pause
    exit /b 1
)

echo Video found: %VIDEO_PATH%
echo.

set OUTPUT=IMG_3048_con_Arjona_converted.mp4

echo Converting video to MP4 (H.264)...
echo This may take a few minutes...
echo.

ffmpeg -i "%VIDEO_PATH%" -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k "%OUTPUT%"

if errorlevel 1 (
    echo.
    echo Error during conversion
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Conversion completed!
echo ========================================
echo.
echo Original file: %VIDEO_PATH%
echo Converted file: %OUTPUT%
echo.
echo You can now use the converted file with run_tracking.bat
echo.
pause
