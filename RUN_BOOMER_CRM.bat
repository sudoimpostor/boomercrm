@echo off
setlocal
title Boomer CRM
cd /d "%~dp0"

echo ========================================================
echo   BOOMER CRM - High-Visibility Desktop Operations Suite
echo ========================================================
echo.
echo Starting Boomer CRM...

:: Check for local portable Python first, then fall back to system python
if exist ".\python_full\pythonw.exe" (
    start "" ".\python_full\pythonw.exe" app_gui.py
    exit /b
)
if exist ".\python_embed\pythonw.exe" (
    start "" ".\python_embed\pythonw.exe" app_gui.py
    exit /b
)

:: Check for system pythonw or python
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw app_gui.py
    exit /b
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python app_gui.py
    exit /b
)

echo.
echo [ERROR] Python was not found on your system!
echo Please install Python 3.10+ from https://www.python.org/
echo and ensure it is added to your PATH.
echo.
pause
