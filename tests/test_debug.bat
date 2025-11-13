@echo off
setlocal enabledelayedexpansion
cls

echo TEST DE DEBUG
echo ================================
echo.

echo Paso 1: Pregunta sobre bailarines visibles
set /p BOTH_VISIBLE="Estan ambos bailarines visibles desde el inicio? (S/N): "
echo Respuesta recibida: [%BOTH_VISIBLE%]
echo.

REM Establecer default
if "%BOTH_VISIBLE%"=="" set BOTH_VISIBLE=S
echo Despues de default: [%BOTH_VISIBLE%]
echo.

set START_TIME=0
echo START_TIME inicial: [%START_TIME%]
echo.

echo Comparando: [!BOTH_VISIBLE!] con [N]
if /i "!BOTH_VISIBLE!"=="N" (
    echo Entrando en el bloque N...
    echo.
    echo Especifica el momento en SEGUNDOS cuando aparecen ambos bailarines.
    echo Ejemplo: Si aparecen a los 30 segundos, ingresa: 30
    echo.
    set /p START_TIME="Tiempo de inicio en segundos: "
    echo Tiempo ingresado: [!START_TIME!]

    REM Verificar que se ingreso un valor
    if "!START_TIME!"=="" (
        echo START_TIME estaba vacio, estableciendo a 0
        set START_TIME=0
    )
) else (
    echo No entrando en bloque N, usando !BOTH_VISIBLE!
)

echo.
echo ================================
echo RESULTADO FINAL:
echo ================================
echo BOTH_VISIBLE = [!BOTH_VISIBLE!]
echo START_TIME = [!START_TIME!]
echo.
echo Si ves esto, el script funciona correctamente.
echo.
pause
