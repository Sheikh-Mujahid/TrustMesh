# Trust Mesh Start Script — Windows PowerShell
# Run from the agriledger/ directory or from project root

$PYTHON = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-Not (Test-Path $PYTHON)) {
    Write-Host "ERROR: Virtual environment not found at $PYTHON" -ForegroundColor Red
    Write-Host "Run setup.ps1 first to create the environment." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Trust Mesh v1.2  --  IoT + Blockchain Agriculture Platform" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Python Environment : $PYTHON" -ForegroundColor Cyan
Write-Host "  Web Dashboard      : http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Interactive Docs   : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Database Support   : MySQL (auto-connects if available) / SQLite (zero-config)" -ForegroundColor Cyan
Write-Host ""

Set-Location (Join-Path $PSScriptRoot "backend")
& $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8000
