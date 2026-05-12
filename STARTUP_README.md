# OptiERP — Startup Guide (Windows)

This repo has two apps:
- Backend: `erp-backend` (FastAPI)
- Frontend: `erp-frontend` (Vue 3 + Vite)

## Prerequisites

- Python 3.9+ installed
- Node.js 18+ installed (includes `npm`)
- PostgreSQL (optional for dev; many endpoints run without DB depending on `.env`)

## Backend (FastAPI)

### 1) Create and install dependencies (first time)

From repo root:

```powershell
cd erp-backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\pip.exe install fastapi uvicorn[standard] sqlalchemy python-jose[cryptography] passlib[bcrypt] pydantic email-validator python-dotenv httpx psycopg2-binary
```

If you already have a dependency list you prefer, install that instead.

### 2) Configure environment

Backend reads `erp-backend/.env`. Update at least:
- `JWT_SECRET`
- `DATABASE_URL` (if using DB)
- `ALLOWED_ORIGINS` (e.g. `http://localhost:5173`)

### 3) Run backend (one command)

From repo root:

```powershell
.\scripts\start-backend.cmd
```

Backend runs on `http://localhost:8000`.

## Frontend (Vue)

### 1) Configure environment

Frontend reads `erp-frontend/.env.local`. Set:
- `VITE_API_BASE_URL=http://localhost:8000`

### 2) Install deps (first time)

From repo root:

```powershell
cd erp-frontend
cmd /c npm install
```

### 3) Run frontend (one command)

From repo root:

```powershell
.\scripts\start-frontend.cmd
```

Frontend runs on `http://localhost:5173`.

## Typical dev workflow

Open two terminals at repo root:

1) Backend:
```powershell
.\scripts\start-backend.cmd
```

2) Frontend:
```powershell
.\scripts\start-frontend.cmd
```

## Notes / Troubleshooting

- If PowerShell blocks `npm` with “running scripts is disabled”, use the provided `*.cmd` scripts (they run `npm` via `cmd.exe`).
- If port `8000` or `5173` is busy, stop the other process or change the port in the script.

