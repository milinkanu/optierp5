# Deploy guide: Railway (backend) + Vercel (frontend)

This repo has:
- Backend: `erp-backend` (FastAPI, `main.py`)
- Frontend: `erp-frontend` (Vue 3 + Vite)

## Alternative: Deploy backend on Render (instead of Railway)

This repo includes a Render Blueprint at `render.yaml`.

### Render steps

1. Push repo to GitHub (or GitLab).
2. In Render: **New** → **Blueprint** → select your repo.
3. Render will detect `render.yaml` and create:
   - A web service named `erp-backend` (root dir `erp-backend`)
4. Add a PostgreSQL database in Render (recommended) and copy the **External Database URL**.
5. In Render → backend service → **Environment** set:
   - `DATABASE_URL` = Render Postgres external URL
   - `FINOPS_USE_DATABASE=true`
   - `JWT_SECRET=...` (32+ chars)
   - `JWT_ALGORITHM=HS256`
   - `JWT_EXPIRATION_MINUTES=60`
   - `DEV_ALLOW_ALL_ORIGINS=false`
   - `ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app` (add custom domain too if any)
6. Deploy and verify:
   - Open `https://<render-backend-url>/health`

## 1) Prep (one-time)

1. Push this repo to GitHub (or GitLab).
2. Ensure you **do not** commit secrets:
   - Backend secrets belong in Railway Variables
   - Frontend env belongs in Vercel Environment Variables

## 2) Deploy backend on Railway

### 2.1 Create project + service

1. In Railway: **New Project** → **Deploy from GitHub repo**.
2. Select this repository.
3. When Railway asks for a **Root Directory**, set it to: `erp-backend`
   - Railway will pick up `erp-backend/railway.toml` and start using `uvicorn`.

### 2.2 Add PostgreSQL (recommended for production)

1. In the Railway project: **Add** → **Database** → **PostgreSQL**.
2. Railway will create a database and provide a connection string.

### 2.3 Configure backend environment variables (Railway → Variables)

Minimum variables to set:
- `DATABASE_URL` = Railway Postgres connection string (starts with `postgresql://...`)
- `FINOPS_USE_DATABASE` = `true`
- `JWT_SECRET` = long random string (32+ chars)
- `JWT_ALGORITHM` = `HS256`
- `JWT_EXPIRATION_MINUTES` = `60`

CORS (important):
- `DEV_ALLOW_ALL_ORIGINS` = `false`
- `ALLOWED_ORIGINS` = your Vercel URL(s), comma-separated, example:
  - `https://your-app.vercel.app,https://your-custom-domain.com`
- (Optional) `ALLOW_ORIGIN_REGEX` only if you need wildcard-like matching

Other optional variables (keep if your code uses them):
- `OCR_ENABLED` (`true`/`false`)
- `UPLOAD_DIR` (Railway ephemeral disk; use object storage if you need persistence)
- `MAX_FILE_SIZE`

### 2.4 Deploy + get your backend URL

1. Railway will build + deploy automatically after variables are set.
2. In Railway service settings: find the **Public URL** for the backend, like:
   - `https://your-backend-production.up.railway.app`

Quick check:
- Open `https://.../health` (must return OK / JSON).

## 3) Deploy frontend on Vercel

### 3.1 Create project

1. In Vercel: **Add New** → **Project** → import the same Git repo.
2. In project settings:
   - **Root Directory**: `erp-frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
   - Vercel should also detect this from `erp-frontend/vercel.json`.

### 3.2 Configure frontend environment variables (Vercel → Settings → Environment Variables)

Set:
- `VITE_API_BASE_URL` = your Railway backend public URL (no trailing slash), example:
  - `https://your-backend-production.up.railway.app`

Redeploy after adding/changing env vars (Vercel usually prompts this).

## 4) Connect the two (CORS + URLs)

1. Once Vercel gives you the frontend URL (example `https://your-app.vercel.app`),
   go back to Railway and ensure:
   - `ALLOWED_ORIGINS` includes that exact Vercel URL
   - `DEV_ALLOW_ALL_ORIGINS=false`
2. Trigger a Railway redeploy (or just update variables; Railway redeploys automatically).

## 5) Typical production checklist

- Use Railway Postgres (not local connection strings).
- Rotate `JWT_SECRET` for production and keep it private.
- If you need file persistence for uploads, don’t rely on `UPLOAD_DIR` on Railway; use S3/R2/etc.
- Configure a custom domain on Vercel and add it to `ALLOWED_ORIGINS`.

## 6) Local parity (optional)

Backend:
- `cd erp-backend`
- Create `.env` locally (don’t commit it)
- Run: `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload`

Frontend:
- `cd erp-frontend`
- Create `.env.local` with `VITE_API_BASE_URL=http://localhost:8000`
- Run: `npm run dev`
