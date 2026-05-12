@echo off
setlocal

cd /d "%~dp0\..\erp-backend"

if "%DATABASE_URL%"=="" (
  echo [apply-db-schema] DATABASE_URL is not set in this terminal.
  echo [apply-db-schema] Set it, or put it in erp-backend\.env and run from a shell that loads it.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [apply-db-schema] Missing venv: erp-backend\.venv
  exit /b 1
)

echo [apply-db-schema] Applying database/dev_upgrades.sql to %DATABASE_URL%
".venv\Scripts\python.exe" -c "import os; import psycopg2; from pathlib import Path; sql=Path('database/dev_upgrades.sql').read_text(encoding='utf-8'); conn=psycopg2.connect(os.environ['DATABASE_URL']); conn.autocommit=True; cur=conn.cursor(); cur.execute(sql); cur.close(); conn.close(); print('OK')"
