@echo off
setlocal enabledelayedexpansion
cls
echo ========================================
echo   Dancer Tracking - Sistema Completo
echo ========================================
echo.

REM ============================================
REM PASO 1: Verificar Python
REM ============================================
echo [1/7] Verificando Python...
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
REM PASO 2: Instalar FFmpeg si necesario
REM ============================================
echo [2/7] Verificando FFmpeg...
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
        echo ERROR: Instalacion de FFmpeg fallo
        echo Opcion manual: https://www.gyan.dev/ffmpeg/builds/
        pause
        exit /b 1
    )
)
set PATH=%~dp0ffmpeg\bin;%PATH%
echo.

REM ============================================
REM PASO 3: Configurar entorno Python
REM ============================================
echo [3/7] Configurando entorno Python...

if not exist "venv\" (
    echo Creando entorno virtual...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Instalando/actualizando dependencias...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo al instalar dependencias
    pause
    exit /b 1
)
echo OK: Dependencias instaladas
echo.

REM ============================================
REM PASO 4: Buscar video
REM ============================================
echo [4/7] Buscando video...
set VIDEO_PATH=
if exist "IMG_3048_con_Arjona.mov" (
    set VIDEO_PATH=IMG_3048_con_Arjona.mov
) else if exist "..\IMG_3048_con_Arjona.mov" (
    set VIDEO_PATH=..\IMG_3048_con_Arjona.mov
) else (
    echo No se encontro el video automaticamente.
    echo.
    set /p VIDEO_PATH="Ingresa la ruta completa del video: "
    if not exist "!VIDEO_PATH!" (
        echo ERROR: El archivo no existe
        pause
        exit /b 1
    )
)

echo OK: Video encontrado: %VIDEO_PATH%
echo.

REM ============================================
REM PASO 5: Decidir si trackear o usar coords existentes
REM ============================================
echo [5/7] Modo de operacion...
echo.

set USE_EXISTING_COORDS=N
if exist "coords.csv" (
    echo Se encontraron coordenadas existentes: coords.csv
    echo.
    set /p USE_EXISTING_COORDS="Usar coordenadas existentes? (S/N, default N): "
)

if /i "%USE_EXISTING_COORDS%"=="S" (
    echo Usando coords.csv existente
    goto export
)

REM ============================================
REM PASO 5A: TRACKING
REM ============================================
echo.
echo ========================================
echo   TRACKING
echo ========================================
echo.

echo Elige el tipo de tracker:
echo   1. KCF - Rapido y estable (RECOMENDADO)
echo   2. CSRT - Muy preciso pero puede fallar
echo   3. MOSSE - Muy rapido
echo   4. MIL - Buen balance
echo.
set /p TRACKER_CHOICE="Tu eleccion (1-4, default 1): "

REM Establecer default si no se ingreso nada
if "%TRACKER_CHOICE%"=="" set TRACKER_CHOICE=1

set TRACKER=KCF
if "%TRACKER_CHOICE%"=="1" set TRACKER=KCF
if "%TRACKER_CHOICE%"=="2" set TRACKER=CSRT
if "%TRACKER_CHOICE%"=="3" set TRACKER=MOSSE
if "%TRACKER_CHOICE%"=="4" set TRACKER=MIL

echo.
echo Estan ambos bailarines visibles desde el inicio?
set /p BOTH_VISIBLE="(S/N): "

REM Establecer default
if "%BOTH_VISIBLE%"=="" set BOTH_VISIBLE=S

set START_TIME=0
if /i "%BOTH_VISIBLE%"=="N" goto ask_start_time
goto continue_tracking

:ask_start_time
echo.
echo Especifica el momento (en SEGUNDOS) cuando aparecen ambos bailarines.
echo Ejemplo: Si aparecen a los 30 segundos, ingresa: 30
echo.
set /p START_TIME="Tiempo de inicio en segundos: "
REM Verificar que se ingreso un valor
if "%START_TIME%"=="" set START_TIME=0

:continue_tracking

echo.
echo ========================================
echo Iniciando tracking...
echo ========================================
echo.
echo Tracker: %TRACKER%
echo Inicio: %START_TIME%s
echo Video: %VIDEO_PATH%
echo.
echo IMPORTANTE:
echo   1. Dibuja un rectangulo GRANDE alrededor de los bailarines
echo   2. Incluye espacio alrededor de ellos
echo   3. Presiona ENTER para iniciar
echo.
echo DURANTE EL TRACKING:
echo   - VERDE = Tracking OK
echo   - NARANJA = Atencion (rectangulo se encoge)
echo   - ROJO = Problema detectado
echo.
echo   Presiona R = Re-inicializar si es necesario
echo   Presiona ESPACIO = Pausar/Reanudar
echo   Presiona ESC = Detener
echo.
echo Comando a ejecutar:
echo python track_improved.py "%VIDEO_PATH%" coords.csv --start-time %START_TIME% --tracker %TRACKER%
echo.
pause

echo Ejecutando tracking...
echo.
python track_improved.py "%VIDEO_PATH%" coords.csv --start-time %START_TIME% --tracker %TRACKER%

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Tracking fallo
    echo ========================================
    echo.
    echo Posibles causas:
    echo   - Python no puede abrir el video
    echo   - Falta alguna libreria
    echo   - Error en el script de Python
    echo.
    echo Por favor, revisa los mensajes de error arriba.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Tracking completado!
echo ========================================
echo.

REM ============================================
REM PASO 6: EXPORTAR
REM ============================================
:export
echo [6/7] Configuracion de export...
echo.

set /p MARGIN="Margen alrededor de bailarines (default 1.5): "
if "%MARGIN%"=="" set MARGIN=1.5

set /p SMOOTH="Suavizado de movimiento (default 10): "
if "%SMOOTH%"=="" set SMOOTH=10

REM Generar nombre de salida con timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set OUTPUT=output_!datetime:~0,8!_!datetime:~8,6!.mov

echo.
echo ========================================
echo   EXPORTANDO
echo ========================================
echo.
echo Video: %VIDEO_PATH%
echo Salida: !OUTPUT!
echo Margen: %MARGIN%x
echo Suavizado: %SMOOTH%
echo.
echo Esto tomara varios minutos...
echo.

python export_final.py "%VIDEO_PATH%" coords.csv "!OUTPUT!" --margin %MARGIN% --smooth %SMOOTH%

if errorlevel 1 (
    echo.
    echo ERROR: Export fallo
    pause
    exit /b 1
)

REM ============================================
REM PASO 7: FINALIZADO
REM ============================================
echo.
echo ========================================
echo   COMPLETADO!
echo ========================================
echo.
echo Archivo creado: !OUTPUT!
echo Ubicacion: %CD%
echo.

REM Mostrar tamaño del archivo
for %%A in ("!OUTPUT!") do set SIZE=%%~zA
set /a SIZE_MB=!SIZE! / 1048576

echo Tamaño: !SIZE_MB! MB
echo.
echo El video incluye:
echo   - Tracking dinamico centrado en bailarines
echo   - Audio original preservado
echo   - Alta calidad (CRF 18)
echo   - Sin deformacion
echo.

echo Deseas analizar las coordenadas del tracking?
set /p ANALYZE="(S/N): "

if /i "%ANALYZE%"=="S" (
    echo.
    echo Generando analisis...
    python analyze_tracking.py coords.csv
    if errorlevel 1 (
        echo.
        echo Nota: Analisis requiere matplotlib
        echo Instalar con: pip install matplotlib
    )
)

echo.
echo Gracias por usar Dancer Tracking!
echo.
pause
exit /b 0
