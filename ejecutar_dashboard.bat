@echo off
title Dashboard de Quantile Mapping - Hidrometeorologia
echo ========================================================
echo   Iniciando Dashboard de Quantile Mapping
echo   Precipitacion MPI-ESM1-2-HR vs Estacion Carolina
echo ========================================================
echo.

set PYTHON_EXE=C:\Users\eliel\AppData\Local\Programs\Python\Python311\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] No se encontro Python 3.11 en %PYTHON_EXE%
    pause
    exit /b 1
)

cd /d "%~dp0"
echo Ejecutando Streamlit en el puerto 8501...
"%PYTHON_EXE%" -m streamlit run app.py --server.port 8501 --server.headless false

pause
