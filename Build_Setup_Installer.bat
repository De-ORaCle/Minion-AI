@echo off
title Building Minion AI Windows Setup Installer
echo =====================================================================
echo 🍌 Minion AI — Compiling Windows Setup Installer (Minion_Setup_v1.0.exe)
echo =====================================================================
echo.
python build_installer.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup creation encountered an error. Please see details above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Setup installer is ready: dist\Minion_Setup_v1.0.exe
echo Anyone can double-click this single file to install Minion AI on Windows!
echo.
pause
