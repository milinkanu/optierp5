@echo off
setlocal

cd /d "%~dp0\..\erp-backend"

if not exist ".venv\Scripts\python.exe" (
  echo [start-backend] Missing venv: erp-backend\.venv
  echo [start-backend] Create it with: cd erp-backend ^&^& python -m venv .venv
  exit /b 1
)

if "%PORT%"=="" set "PORT=8001"
echo [start-backend] Starting FastAPI on http://localhost:%PORT%
".venv\Scripts\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port %PORT%
