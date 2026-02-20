@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PerLap
color 0A

echo.
echo  PerLap - Cronometro de Vueltas RC
echo.

REM --- Buscar Python ---
set "PY="

where python >nul 2>&1
if !errorlevel!==0 (
    set "PY=python"
    goto :found
)

where python3 >nul 2>&1
if !errorlevel!==0 (
    set "PY=python3"
    goto :found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    goto :found
)

goto :nopython

:found
"!PY!" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if !errorlevel! neq 0 (
    echo  Python encontrado pero es menor a 3.10
    set "PY="
    goto :nopython
)
"!PY!" --version
echo.
goto :deps

REM --- No hay Python ---
:nopython
echo.
echo  Python 3.10+ no encontrado.
echo.
echo  1 = Instalar automaticamente (requiere internet)
echo  2 = Salir
echo.
set /p "OPT=  Elige (1/2): "
if "!OPT!"=="1" goto :instalar
echo.
echo  Instala Python desde https://www.python.org/downloads/
echo  Marca "Add Python to PATH" al instalar.
pause
exit /b 1

:instalar
echo.
echo  Descargando Python 3.12...
set "INST=%TEMP%\python_setup.exe"
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%INST%'"
if not exist "%INST%" (
    echo  Error al descargar.
    pause
    exit /b 1
)
echo  Instalando...
"%INST%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
del "%INST%" >nul 2>&1
echo.
echo  Python instalado. Cierra esta ventana y ejecuta PerLap.bat de nuevo.
pause
exit /b 0

REM --- Dependencias ---
:deps
cd /d "%~dp0"
echo  Directorio: %CD%
echo  Verificando dependencias...

"!PY!" -c "import PySide6; import cv2; import numpy; import serial" >nul 2>&1
if !errorlevel! neq 0 (
    echo  Instalando dependencias...
    "!PY!" -m pip install --upgrade pip >nul 2>&1
    "!PY!" -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo  Error instalando dependencias.
        pause
        exit /b 1
    )
    echo  Dependencias OK.
) else (
    echo  Dependencias OK.
)

REM --- Ejecutar ---
echo.
echo  Iniciando PerLap...
echo  Cierra esta ventana para detener.
echo.

"!PY!" main.py

if !errorlevel! neq 0 (
    echo.
    echo  PerLap cerro con error: !errorlevel!
    pause
)

endlocal
