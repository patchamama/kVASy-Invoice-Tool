@echo off
setlocal enabledelayedexpansion

title kVASy Invoice Tool

cd /d "%~dp0"

:: ── Check Python ──────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found. Install Python 3.11+ from https://python.org
    echo         Make sure "Add Python to PATH" is checked during install.
    echo.
    pause
    exit /b 1
)

:: ── Create venv if missing ────────────────────────────────────────
if not exist ".venv\" (
    echo.
    echo  Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: ── Install / verify dependencies ─────────────────────────────────
.venv\Scripts\python.exe -c "import flask, zeep, requests" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Installing dependencies...
    .venv\Scripts\pip.exe install -q -r requirements.txt
    if errorlevel 1 (
        echo  ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: ── Check config.py ───────────────────────────────────────────────
if not exist "config.py" (
    echo.
    echo  WARNING: config.py not found.
    echo           Copy config.example.py to config.py and fill in your credentials.
    echo.
)

:: ── Create downloads dir ──────────────────────────────────────────
if not exist "downloads\" mkdir downloads

:: ── Menu ──────────────────────────────────────────────────────────
:MENU
echo.
echo ================================================================
echo   kVASy Invoice Tool  v%VERSION%
echo ================================================================
echo.
echo   1.  Run connection diagnostic (diagnose.py)
echo   2.  Start web app  (http://localhost:5224)
echo   3.  Exit
echo.

for /f %%v in ('type VERSION 2^>nul') do set VERSION=%%v

set /p CHOICE="  Your choice [1/2/3]: "

if "%CHOICE%"=="1" goto DIAGNOSE
if "%CHOICE%"=="2" goto APP
if "%CHOICE%"=="3" goto END

echo  Invalid choice — please enter 1, 2, or 3.
goto MENU

:: ── Diagnostic ────────────────────────────────────────────────────
:DIAGNOSE
echo.
echo  Running diagnostic — make sure VPN is active if required.
echo ----------------------------------------------------------------
.venv\Scripts\python.exe diagnose.py
echo.
echo ----------------------------------------------------------------
echo  Diagnostic finished. Press any key to return to the menu.
pause >nul
goto MENU

:: ── Web App ───────────────────────────────────────────────────────
:APP
echo.
echo  Starting kVASy Invoice Tool at http://localhost:5224
echo  Press Ctrl+C to stop the server.
echo.

:: Open browser after a short delay
start "" cmd /c "timeout /t 2 >nul && start http://localhost:5224"

set FLASK_RUN_PORT=5224
.venv\Scripts\python.exe app.py

echo.
echo  Server stopped. Press any key to return to the menu.
pause >nul
goto MENU

:END
endlocal
