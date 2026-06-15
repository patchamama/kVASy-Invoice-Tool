#Requires -Version 5.1
<#
.SYNOPSIS
    kVASy Invoice Tool — Windows installer
.DESCRIPTION
    Installs Python 3.12 (if missing), creates a virtual environment,
    installs all dependencies, and launches the app.
    Run once from the project folder after cloning the repository.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$APP_NAME    = 'kVASy Invoice Tool'
$MIN_PYTHON  = [version]'3.11'
$PYTHON_URL  = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
$PYTHON_HASH = $null   # set to SHA256 string to enable integrity check
$PORT        = 5224

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# ── Helpers ────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n  >> $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Fatal { param($msg) Write-Host "`n  [ERROR]  $msg`n" -ForegroundColor Red; Read-Host "Press Enter to exit"; exit 1 }

function Find-Python {
    $candidates = @('python', 'python3', 'py')
    foreach ($cmd in $candidates) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match 'Python (\d+\.\d+)') {
                $found = [version]$Matches[1]
                if ($found -ge $MIN_PYTHON) { return $cmd }
            }
        } catch {}
    }
    return $null
}

# ── Banner ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ================================================================" -ForegroundColor Indigo
Write-Host "    $APP_NAME — Windows Installer" -ForegroundColor White
Write-Host "  ================================================================" -ForegroundColor Indigo

# ── Step 1: Python ─────────────────────────────────────────────────
Write-Step "Checking Python $MIN_PYTHON+ ..."

$pythonCmd = Find-Python

if ($null -eq $pythonCmd) {
    Write-Warn "Python $MIN_PYTHON+ not found. Trying to install via winget..."

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        try {
            winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
            Write-Ok "Python installed via winget."
        } catch {
            Write-Warn "winget install failed. Falling back to direct download..."
            $winget = $null
        }
    }

    if ($null -eq $winget) {
        Write-Warn "Downloading Python installer from python.org..."
        $installer = Join-Path $env:TEMP 'python_installer.exe'
        try {
            Invoke-WebRequest -Uri $PYTHON_URL -OutFile $installer -UseBasicParsing
        } catch {
            Write-Fatal "Could not download Python. Check your internet connection and retry."
        }

        if ($PYTHON_HASH) {
            $hash = (Get-FileHash $installer -Algorithm SHA256).Hash
            if ($hash -ne $PYTHON_HASH) { Write-Fatal "Python installer hash mismatch. Aborting." }
        }

        Write-Warn "Running Python installer — follow the prompts. Check 'Add Python to PATH'."
        Start-Process $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0' -Wait
        Remove-Item $installer -Force -ErrorAction SilentlyContinue

        # Refresh PATH so the new python is visible
        $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
                    [System.Environment]::GetEnvironmentVariable('Path','User')
    }

    $pythonCmd = Find-Python
    if ($null -eq $pythonCmd) {
        Write-Fatal "Python installation succeeded but 'python' is still not on PATH.`n         Open a new terminal and re-run this script."
    }
}

$ver = & $pythonCmd --version 2>&1
Write-Ok "Using $ver  ($pythonCmd)"

# ── Step 2: Virtual environment ────────────────────────────────────
Write-Step "Setting up virtual environment (.venv) ..."

if (-not (Test-Path '.venv')) {
    & $pythonCmd -m venv .venv
    Write-Ok "Virtual environment created."
} else {
    Write-Ok "Virtual environment already exists — skipping."
}

$pip    = '.\.venv\Scripts\pip.exe'
$python = '.\.venv\Scripts\python.exe'

# ── Step 3: Dependencies ───────────────────────────────────────────
Write-Step "Installing dependencies from requirements.txt ..."

& $pip install --upgrade pip --quiet
& $pip install -r requirements.txt --quiet

Write-Ok "Dependencies installed."

# ── Step 4: Config ─────────────────────────────────────────────────
Write-Step "Checking configuration ..."

if (-not (Test-Path 'config.py')) {
    Copy-Item 'config.example.py' 'config.py'
    Write-Warn "config.py created from template."
    Write-Warn "Open config.py in a text editor and fill in your SOAP credentials before using the app."
    Write-Host ""
    Write-Host "     File location: $ScriptDir\config.py" -ForegroundColor Yellow
} else {
    Write-Ok "config.py already exists."
}

# ── Step 5: Downloads folder ───────────────────────────────────────
if (-not (Test-Path 'downloads')) {
    New-Item -ItemType Directory -Path 'downloads' | Out-Null
}

# ── Step 6: Launch ─────────────────────────────────────────────────
Write-Step "Installation complete!"
Write-Host ""
Write-Host "  Starting $APP_NAME at http://localhost:$PORT" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop the server." -ForegroundColor Gray
Write-Host ""

# Open browser after short delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:$using:PORT"
} | Out-Null

$env:FLASK_RUN_PORT = $PORT
& $python app.py
