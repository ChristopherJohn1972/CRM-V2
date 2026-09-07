# Railway Deployment Guide

## Architecture

```
Vercel (frontend)
    │ HTTPS
    ▼
Railway (Django backend)
    │ DATABASE_URL + TLS
    ▼
Aiven PostgreSQL
```

## Prerequisites

1. **GitHub account** — code already at `https://github.com/ChristopherJohn1972/CRM-V2.git`
2. **Railway account** — https://railway.app (sign up with GitHub, $5 free trial credit)
3. **Aiven PostgreSQL** — already running at `crm-v2-db-cr-management.e.aivencloud.com:27771`
4. **Vercel frontend** — already deployed at `https://crm-v2-mu.vercel.app`

## Step 1: Create Railway Project

1. Go to https://railway.app
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select `ChristopherJohn1972/CRM-V2` repo
4. Select **`Backend`** as the root directory
5. Railway will auto-detect the Python project

## Step 2: Set Environment Variables

Go to **Service → Variables** tab and add:

```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_SECRET_KEY=your_secure_random_string_at_least_50_chars
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=your-app-name.up.railway.app

# Database (from Aiven)
DATABASE_URL=postgresql://avnadmin:YOUR_AIVEN_PASSWORD@crm-v2-db-cr-management.e.aivencloud.com:27771/defaultdb?sslmode=require

# JWT
CRM_JWT_SECRET=your_jwt_secret_key_at_least_64_chars_long_here
CRM_JWT_ACCESS_TTL_MINUTES=60
CRM_JWT_ALGORITHM=HS256

# CORS
CRM_CORS_ORIGINS=https://crm-v2-mu.vercel.app

# Storage
CRM_STORAGE_BACKEND=dev
CRM_STORAGE_ROOT=./storage

# Email
CRM_EMAIL_HOST=smtp.gmail.com
CRM_EMAIL_PORT=587
CRM_EMAIL_USE_TLS=true
CRM_EMAIL_HOST_USER=your_email@gmail.com
CRM_EMAIL_HOST_PASSWORD=your_app_password
CRM_DEFAULT_FROM_EMAIL=CRM <noreply@yourdomain.com>

# Scout
CRM_SCOUT_SECURITY_EMAIL=your_email@example.com
```

**⚠️ IMPORTANT:** Replace placeholder values with actual secrets. Never commit real passwords.

## Step 3: Set Build & Start Commands

In **Service → Settings**:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120`
- **Port:** `8000` (or leave blank, Railway auto-assigns)

## Step 4: Deploy

1. Railway auto-deploys on every push to `main`
2. Or click **"Deploy"** manually
3. Wait for build to complete (~2-3 minutes)

## Step 5: Run Migrations & Seed Data

In **Service → Deployments → latest → View Logs**, click **"Shell"** tab:

```bash
# Create tables
python manage.py create_tables

# Seed data (roles, permissions, admin user)
python manage.py seed_data
```

## Step 6: Get Railway Backend URL

After deployment, Railway provides a URL like:
```
https://your-app-name-production.up.railway.app
```

Test it:
```bash
curl https://your-app-name-production.up.railway.app/api/auth/login/
```

## Step 7: Update Frontend

Update Vercel env var:
```bash
# In Vercel dashboard → Settings → Environment Variables
VITE_API_BASE_URL=https://your-app-name-production.up.railway.app
```

Update Railway CORS:
```bash
CRM_CORS_ORIGINS=https://crm-v2-mu.vercel.app
```

## Step 8: Verify Deployment

1. Go to `https://crm-v2-mu.vercel.app`
2. Login with admin credentialsin$&2222`
3. Verify all modules load without 500 errors
4. Test campaign CRUD
5. Test lead status transitions
6. Test sales order edit/delete

## Step 9: Set Up Auto-Deploy

Railway auto-deploys on every push to `main`. Just:
```bash
git add .
git commit -m "Your changes"
git push origin main
```

## Cost

- **Free trial:** $5 credit (one-time)
- **After trial:** $5/month (hobby plan)
- **What you get:** No cold starts, HTTPS, env vars, GitHub integration, shell access

## Troubleshooting

### "Application failed to respond"
- Check logs in Railway dashboard
- Ensure `DATABASE_URL` is correct
- Ensure Aiven whitelist includes Railway IPs (or disable IP restriction)

### "CORS error"
- Set `CRM_CORS_ORIGINS=https://crm-v2-mu.vercel.app`
- Ensure no trailing slash

### "Table doesn't exist"
- Run `python manage.py create_tables` in Railway shell

### "Permission denied"
- Run `python manage.py seed_data` in Railway shell

## Files Created

- `Backend/railway.json` — Railway build/deploy config
- `Backend/.env.example` — Environment variable template
- `deploy/railway-deploy.md` — This guide
