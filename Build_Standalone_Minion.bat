@echo off
title Building Minion AI Standalone Executable
echo =====================================================================
echo 🍌 Minion AI — Standalone Packaging (Fusing Python into Native App)
echo =====================================================================
echo.
python build_executable.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build encountered an error. Please see details above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Standalone Minion application is ready inside: dist\Minion\Minion.exe
echo You can copy or distribute the 'dist\Minion' folder to any Windows machine.
echo No Python installation required!
echo.
pause
