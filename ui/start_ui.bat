@echo off
setlocal enabledelayedexpansion
cls
echo ========================================
echo   Dancer Tracking UI - Launcher
echo ========================================
echo.

REM ============================================
REM Verificar Python
REM ============================================
echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en PATH
    echo.
    echo Descarga Python: https://www.python.org/downloads/
    echo IMPORTANTE: Marca "Add Python to PATH" durante la instalacion
    echo.
    pause
    exit /b 1
)
echo OK: Python encontrado
python --version
echo.

REM ============================================
REM Verificar FFmpeg
REM ============================================
echo [2/4] Verificando FFmpeg...
set FFMPEG_EXE=%~dp0ffmpeg\bin\ffmpeg.exe

if exist "%FFMPEG_EXE%" (
    echo OK: FFmpeg ya instalado
) else (
    echo FFmpeg no encontrado. Instalando automaticamente...
    echo (Descarga ~80 MB, por favor espera...)
    echo.
    powershell -ExecutionPolicy Bypass -File "%~dp0install_ffmpeg.ps1"
    if errorlevel 1 (
        echo.
        echo ADVERTENCIA: Instalacion de FFmpeg fallo
        echo La UI funcionara pero el export de video puede fallar
        echo Opcion manual: https://www.gyan.dev/ffmpeg/builds/
        echo.
        pause
    )
)
set PATH=%~dp0ffmpeg\bin;%PATH%
echo.

REM ============================================
REM Configurar entorno Python
REM ============================================
echo [3/4] Configurando entorno Python...

if not exist "venv\" (
    echo Creando entorno virtual...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Instalando/actualizando dependencias...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo al instalar dependencias
    echo.
    echo Intenta instalar manualmente con:
    echo   pip install PyQt5 opencv-contrib-python numpy matplotlib Pillow
    echo.
    pause
    exit /b 1
)
echo OK: Dependencias instaladas
echo.

REM ============================================
REM Iniciar UI
REM ============================================
echo [4/4] Iniciando interfaz grafica...
echo.
echo ========================================
echo   Abriendo Dancer Tracking UI
echo ========================================
echo.
echo IMPORTANTE:
echo   - La ventana de la UI se abrira en unos segundos
echo   - NO cierres esta ventana de comandos mientras uses la UI
echo   - Los mensajes de error aparecerán aqui si hay problemas
echo.

python dancer_tracking_ui.py

echo.
echo ========================================
echo   UI Cerrada
echo ========================================
echo.
pause
