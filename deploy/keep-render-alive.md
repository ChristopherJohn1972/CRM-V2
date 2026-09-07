# Keep Render Alive — Ping System

## Problem
Render free tier spins down after 15 minutes of inactivity, causing ~30-60 second cold starts.

## Solution: Ping `/api/health` every 2 minutes

### Option A: cron-job.org (2-minute intervals) ✅ RECOMMENDED

1. Go to **https://cron-job.org** → sign up (free)
2. Click **"Create Job"**
3. Settings:
   - **Name:** `CRM Backend Keep-Alive`
   - **URL:** `https://crm-backend-49fn.onrender.com/api/health`
   - **Schedule:** `*/2 * * * *` (every 2 minutes)
   - **Request Method:** `GET`
4. Click **"Save"**
5. Enable the job

That's it. Render stays awake 24/7.

---

### Option B: GitHub Actions (5-minute intervals)

GitHub Actions minimum cron interval is 5 minutes.

1. Go to GitHub repo → **Settings → Secrets and variables → Actions**
2. Add secret:
   - **Name:** `RENDER_BACKEND_URL`
   - **Value:** `https://crm-backend-49fn.onrender.com`
3. The workflow file `.github/workflows/ping-render.yml` is already in the repo
4. Push to `main` to activate

---

## Verify It Works

1. Check cron-job.org execution logs (should show 200 OK every 2 min)
2. Or check GitHub Actions → Keep Render Alive → should show green checks
3. Visit `https://crm-backend-49fn.onrender.com/api/health` — should return `{"status":"ok"}`
4. Render logs should show periodic GET requests to `/api/health`
