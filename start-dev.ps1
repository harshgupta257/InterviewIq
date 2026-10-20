# Starts the InterviewIQ backend (http://localhost:8000) and web app (http://localhost:5173)
# in two new PowerShell windows. Usage, from this folder:
#   powershell -ExecutionPolicy Bypass -File .\start-dev.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js is not installed (needed for the web app)." -ForegroundColor Red
    Write-Host "Install the LTS version, then open a NEW terminal and re-run this script:"
    Write-Host "  winget install OpenJS.NodeJS.LTS      (or download from https://nodejs.org)"
    exit 1
}

# Backend: Python 3.12 virtual environment, dependencies, config.
# Uses the "py" launcher so a different default Python (e.g. 3.11) is never picked up.
$py = Join-Path $backend ".venv\Scripts\python.exe"
$venvOk = (Test-Path $py) -and ((& $py -c "import sys, asyncpg; print(sys.version_info[:2] >= (3, 12))" 2>$null) -eq "True")
if (-not $venvOk) {
    if (-not (Get-Command py -ErrorAction SilentlyContinue) -or -not (py -3.12 -c "print(1)" 2>$null)) {
        Write-Host "Python 3.12+ is required. Install it from https://www.python.org/downloads/ and re-run." -ForegroundColor Red
        exit 1
    }
    Write-Host "Creating Python 3.12 virtual environment (first run only)..."
    if (Test-Path (Join-Path $backend ".venv")) {
        Remove-Item -Recurse -Force (Join-Path $backend ".venv") -ErrorAction Stop
    }
    py -3.12 -m venv (Join-Path $backend ".venv")
    & $py -m pip install -r (Join-Path $backend "requirements-dev.txt")
}
if (-not (Test-Path (Join-Path $backend ".env"))) {
    Copy-Item (Join-Path $backend ".env.example") (Join-Path $backend ".env")
}

# Frontend: dependencies, config
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing web app dependencies (first run only)..."
    Push-Location $frontend; npm install; Pop-Location
}
if (-not (Test-Path (Join-Path $frontend ".env.local"))) {
    Copy-Item (Join-Path $frontend ".env.example") (Join-Path $frontend ".env.local")
}

$apiBusy = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($apiBusy) {
    Write-Host "Port 8000 is already in use; assuming the backend is already running."
} else {
    Start-Process powershell -WorkingDirectory $backend -ArgumentList "-NoExit", "-Command", "& '$py' -m uvicorn app.asgi:app --reload --port 8000"
}
Start-Process powershell -WorkingDirectory $frontend -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host ""
Write-Host "Web app:  http://localhost:5173   <- open this in your browser" -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs"
