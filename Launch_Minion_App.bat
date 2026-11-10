@echo off
if exist "%~dp0dist\Minion\Minion.exe" (
    start "" "%~dp0dist\Minion\Minion.exe"
) else (
    start "" pythonw "%~dp0app.py"
)
