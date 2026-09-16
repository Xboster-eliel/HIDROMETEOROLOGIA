@echo off
title Git Push - Hidrometeorologia Dashboard
echo ========================================================
echo   Enviando cambios a GitHub (Xboster-eliel/HIDROMETEOROLOGIA)
echo ========================================================
echo.

cd /d "%~dp0"

echo 1. Comprobando estado del repositorio...
git status

echo.
echo 2. Guardando cambios pendientes...
git add .
set /p commit_msg="Introduce mensaje de commit (o presiona Enter para usar mensaje por defecto): "
if "%commit_msg%"=="" set commit_msg=Actualizacion del dashboard y calculos hidrometeorologicos

git commit -m "%commit_msg%"

echo.
echo 3. Enviando a GitHub (rama main)...
git push -u origin main

echo.
echo ========================================================
if %ERRORLEVEL% equ 0 (
    echo   [EXITO] Cambios enviados correctamente a GitHub.
    echo   Streamlit Cloud se actualizara en breve.
) else (
    echo   [AVISO] Si es la primera vez, inicia sesion en la ventana
    echo   del navegador que se abrio para autorizar a GitHub.
)
echo ========================================================
pause
