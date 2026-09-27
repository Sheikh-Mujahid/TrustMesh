@echo off
title Trust Mesh IoT + Blockchain Platform
echo ============================================================
echo   Trust Mesh v1.2 -- IoT + Blockchain Agriculture Platform
echo ============================================================
echo.
echo   Web Dashboard : http://localhost:8000
echo   API Docs      : http://localhost:8000/docs
echo.
cd /d "%~dp0backend"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
) else (
    python -m uvicorn main:app --host 0.0.0.0 --port 8000
)
pause
