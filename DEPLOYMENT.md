# Deploy guide: Render (Backend & Postgres Database) + Vercel (Frontend)

This guide walks you through deploying the OptiERP application using Render for the FastAPI backend and PostgreSQL database, and Vercel for the Vue 3 + Vite frontend.

## 1. Push Repository to GitHub
Ensure the entire repository is pushed to a private GitHub (or GitLab/Bitbucket) repository. 
Do not commit local `.env` files or secret values.

---

## 2. Deploy Database & Backend on Render
Render allows deploying both the database and the web service simultaneously using the Blueprint feature defined in `render.yaml`.

### 2.1 Deploy using Render Blueprint
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click **New** (top-right) and select **Blueprint**.
3. Connect your GitHub repository.
4. Render will automatically read `render.yaml` and prompt you to create the resources:
   - **Postgres Database**: `finops-db` (on the Free plan)
   - **Web Service**: `erp-backend` (on the Starter plan)
5. Review the service name and environment variables. Render will automatically:
   - Link the Postgres database, injecting the `DATABASE_URL` connection string.
   - Generate a secure random string for `JWT_SECRET`.
6. Click **Apply** to provision and build the services.

---

## 3. Initialize the Database Schema
Since the database does not use auto-migrations, you must apply the SQL schemas manually to your new Render Postgres instance.

### 3.1 Get your External Connection String
1. In the Render Dashboard, click on your PostgreSQL database resource `finops-db`.
2. Look for the **External Connection String** (this allows connections from outside Render's network, e.g., your local machine).
3. Copy the URL (starts with `postgresql://...`).

### 3.2 Run the Migration Script
1. On your local machine, navigate to the `erp-backend` directory.
2. Ensure you have the virtual environment activated and dependencies installed.
3. Execute the migration runner script, passing the Render External Connection String as the `DATABASE_URL` environment variable:
   ```bash
   DATABASE_URL="<your-render-external-connection-string>" python database/apply_schema.py
   ```
4. Verify the console output shows all 7 SQL files applied successfully.

---

## 4. Deploy Frontend on Vercel
Vercel is used to build and host the static Vue 3 + Vite frontend.

### 4.1 Project Import
1. Log in to the [Vercel Dashboard](https://vercel.com).
2. Click **Add New** → **Project** and import your Git repository.
3. Configure the following project settings:
   - **Root Directory**: Select `erp-frontend`.
   - **Build Command**: `npm run build` (detected automatically)
   - **Output Directory**: `dist` (detected automatically)

### 4.2 Configure Environment Variables
Before deploying, add the following environment variable under the **Environment Variables** section:
- **Key**: `VITE_API_BASE_URL`
- **Value**: The public URL of your Render backend service (no trailing slash), e.g., `https://erp-backend.onrender.com`.

### 4.3 Deploy
Click **Deploy**. Vercel will build the project and output a production URL, e.g., `https://optierp-frontend.vercel.app`.

---

## 5. Enable CORS for Frontend
To allow the frontend to safely communicate with the backend:
1. Copy the Vercel deployment URL (e.g., `https://optierp-frontend.vercel.app`).
2. Go to the **Render Dashboard** → click your `erp-backend` Web Service.
3. Go to **Environment** tab.
4. Find the `ALLOWED_ORIGINS` variable and change its value to your Vercel URL.
5. Save changes. Render will automatically redeploy the backend with the new CORS settings.
