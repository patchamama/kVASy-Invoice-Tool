param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$APP_NAME   = 'kVASy Invoice Tool'
$MIN_PYTHON = [version]'3.11'
$PYTHON_URL = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
$PORT       = 5224

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Write-Step  { param($msg) Write-Host "`n  >> $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Fatal {
    param($msg)
    Write-Host "`n  [ERROR]  $msg`n" -ForegroundColor Red
    Read-Host 'Press Enter to exit'
    exit 1
}

function Find-Python {
    # 1) Commands already on PATH
    foreach ($cmd in @('python', 'python3', 'py')) {
        try {
            $out = & $cmd --version 2>&1
            if ($out -match 'Python (\d+\.\d+)') {
                if ([version]$Matches[1] -ge $MIN_PYTHON) { return $cmd }
            }
        } catch {}
    }
    # 2) Known install locations (current user + system, versions 3.11-3.13)
    $roots = @(
        "$env:LOCALAPPDATA\Programs\Python",
        "$env:ProgramFiles\Python",
        'C:\Python'
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        foreach ($dir in (Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending)) {
            $exe = Join-Path $dir.FullName 'python.exe'
            if (Test-Path $exe) {
                try {
                    $out = & $exe --version 2>&1
                    if ($out -match 'Python (\d+\.\d+)') {
                        if ([version]$Matches[1] -ge $MIN_PYTHON) { return $exe }
                    }
                } catch {}
            }
        }
    }
    return $null
}

# ── Banner ────────────────────────────────────────────────────────
Write-Host ''
Write-Host '  ================================================================' -ForegroundColor Blue
Write-Host "    $APP_NAME -- Windows Installer" -ForegroundColor White
Write-Host '  ================================================================' -ForegroundColor Blue

# ── Step 1: Python ────────────────────────────────────────────────
Write-Step "Checking Python $MIN_PYTHON+ ..."

$pythonCmd = Find-Python

if ($null -eq $pythonCmd) {
    Write-Warn "Python $MIN_PYTHON+ not found. Downloading installer from python.org..."

    $installer = Join-Path $env:TEMP 'python_installer.exe'

    try {
        Invoke-WebRequest -Uri $PYTHON_URL -OutFile $installer -UseBasicParsing
    } catch {
        Write-Fatal "Could not download Python. Check your internet connection and retry."
    }

    Write-Warn 'Running Python installer silently...'
    Start-Process $installer -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0' -Wait
    Remove-Item $installer -Force -ErrorAction SilentlyContinue

    # Refresh PATH in current session
    $machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath    = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path    = "$machinePath;$userPath"

    $pythonCmd = Find-Python
    if ($null -eq $pythonCmd) {
        Write-Fatal "Python was installed but could not be located.`n         Close this window, open a new terminal, and re-run install.bat."
    }
}

$pyVer = & $pythonCmd --version 2>&1
Write-Ok "Using $pyVer ($pythonCmd)"

# ── Step 2: Virtual environment ───────────────────────────────────
Write-Step 'Setting up virtual environment (.venv) ...'

if (-not (Test-Path '.venv')) {
    & $pythonCmd -m venv .venv
    Write-Ok 'Virtual environment created.'
} else {
    Write-Ok 'Virtual environment already exists -- skipping.'
}

$pip    = '.\.venv\Scripts\pip.exe'
$python = '.\.venv\Scripts\python.exe'

# ── Step 3: Dependencies ──────────────────────────────────────────
Write-Step 'Installing dependencies from requirements.txt ...'

& $pip install --upgrade pip --quiet
& $pip install -r requirements.txt --quiet

Write-Ok 'Dependencies installed.'

# ── Step 4: Config ────────────────────────────────────────────────
Write-Step 'Checking configuration ...'

if (-not (Test-Path 'config.py')) {
    Copy-Item 'config.example.py' 'config.py'
    Write-Warn 'config.py created from template.'
    Write-Warn "Edit it now: $ScriptDir\config.py"
    Write-Host ''
    Write-Host '  Fill in your SOAP credentials before using the app.' -ForegroundColor Yellow
} else {
    Write-Ok 'config.py already exists.'
}

# ── Step 5: Downloads folder ──────────────────────────────────────
if (-not (Test-Path 'downloads')) {
    New-Item -ItemType Directory -Path 'downloads' | Out-Null
}

# ── Step 6: Launch ────────────────────────────────────────────────
Write-Step 'Installation complete!'
Write-Host ''
Write-Host "  Starting $APP_NAME at http://localhost:$PORT" -ForegroundColor Green
Write-Host '  Press Ctrl+C to stop the server.' -ForegroundColor Gray
Write-Host ''

Start-Process "http://localhost:$PORT" -ErrorAction SilentlyContinue

$env:FLASK_RUN_PORT = $PORT
& $python app.py
