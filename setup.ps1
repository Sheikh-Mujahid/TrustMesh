# Trust Mesh Setup Script — Windows PowerShell
# Creates venv and installs all dependencies using uv

$UV = "uv"
$VENV = Join-Path $PSScriptRoot ".venv"
$PYTHON_VER = "3.10"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Trust Mesh Setup" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

# Check uv
try {
    $uvVersion = & uv --version 2>&1
    Write-Host "  [OK] uv found: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "  [!] uv not found. Install from https://github.com/astral-sh/uv" -ForegroundColor Red
    Write-Host "      Or: pip install uv" -ForegroundColor Yellow
    exit 1
}

# Create venv
Write-Host ""
Write-Host "  Creating virtual environment (.venv)..." -ForegroundColor Cyan
if (Test-Path $VENV) {
    Write-Host "  .venv already exists, skipping creation." -ForegroundColor Yellow
} else {
    & uv venv $VENV --python $PYTHON_VER
    Write-Host "  [OK] Virtual environment created." -ForegroundColor Green
}

# Install packages
Write-Host ""
Write-Host "  Installing Python packages..." -ForegroundColor Cyan
$VENV_PYTHON = Join-Path $VENV "Scripts\python.exe"
& uv pip install fastapi "uvicorn[standard]" mysql-connector-python "qrcode[pil]" python-multipart --python $VENV_PYTHON

Write-Host ""
Write-Host "  [OK] All packages installed." -ForegroundColor Green

# Verify
Write-Host ""
Write-Host "  Verifying installation..." -ForegroundColor Cyan
$verify = & $VENV_PYTHON -c "import fastapi,uvicorn,mysql.connector,qrcode; print('ALL OK')" 2>&1
if ($verify -match "ALL OK") {
    Write-Host "  [OK] $verify" -ForegroundColor Green
} else {
    Write-Host "  [!] Verification failed: $verify" -ForegroundColor Red
}

Write-Host ""
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "    1. Start MySQL and run: mysql -u root -p < database\agriledger.sql" -ForegroundColor White
Write-Host "    2. Run backend:         .\start.ps1" -ForegroundColor White
Write-Host "    3. Open frontend:       frontend\index.html (use VS Code Live Server)" -ForegroundColor White
Write-Host ""
