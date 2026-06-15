@echo off
:: kVASy Invoice Tool — Windows installer launcher
:: Double-click this file to run the PowerShell installer.

cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

if errorlevel 1 (
    echo.
    echo  Installation failed. See messages above.
    pause
)
