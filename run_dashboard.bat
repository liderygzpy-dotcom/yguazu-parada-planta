@echo off
title Yguazú Cementos - Dashboard Parada de Planta
color 0A

echo =======================================================================
echo          YGUAZÚ CEMENTOS S.A. - PLANTA INDUSTRIAL VILLA HAYES
echo            Sistema de Seguimiento Operativo - Parada Mayor
echo =======================================================================
echo.

:: 1. Verificación de entorno Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no se encuentra en el PATH.
    echo Por favor instala Python para ejecutar este Dashboard.
    pause
    exit /b
)

:: 2. Verificación e instalación de librerías necesarias
echo [1/2] Verificando dependencias (streamlit, pandas, openpyxl)...
pip install streamlit pandas openpyxl >nul 2>&1

:: 3. Lanzamiento del Dashboard
echo [2/2] Iniciando servidor y abriendo Dashboard en el navegador...
echo.
echo Presiona Ctrl+C en esta ventana para detener el servidor.
echo =======================================================================
echo.

streamlit run app.py

pause