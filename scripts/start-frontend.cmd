@echo off
setlocal

cd /d "%~dp0\..\erp-frontend"

if not exist "node_modules" (
  echo [start-frontend] node_modules not found. Installing...
  cmd /c npm install || exit /b 1
)

echo [start-frontend] Starting Vite dev server on http://localhost:5173
cmd /c npm run dev

