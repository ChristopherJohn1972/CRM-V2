# CRM V2 Deployment Guide: PythonAnywhere + Aiven

## Overview

| Layer | Platform | Tier | Cold Start |
|-------|----------|------|------------|
| Backend | PythonAnywhere | Free | **Zero** |
| Database | Aiven PostgreSQL | Free | **Zero** |
| Frontend | Vercel | Free | **Zero** |

---

## Step 1: Create Aiven Database

1. Go to [console.aiven.io](https://console.aiven.io)
2. Sign up / Login
3. Click **Create Service**
4. Select **PostgreSQL**
5. Choose **Free** tier (select AWS or GCP region closest to you)
6. Click **Create**
7. Wait ~2 minutes for provisioning
8. Copy these from the **Overview** page:
   - **Host**: `xxx-xxx-xxx.aivencloud.com`
   - **Port**: `28062` (or shown port)
   - **User**: `avnadmin`
   - **Password**: (shown on creation)
   - **Database**: `defaultdb`

---

## Step 2: Create PythonAnywhere Account

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Sign up with GitHub (same account as your repo)

---

## Step 3: Clone and Setup on PythonAnywhere

### 3.1 Open a Bash Console

On PythonAnywhere Dashboard → **Bash** console

### 3.2 Clone the repository

```bash
cd ~
git clone https://github.com/ChristopherJohn1972/CRM-V2.git crm-v2-backend
cd crm-v2-backend/Backend
```

### 3.3 Create virtual environment and install dependencies

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.4 Create .env file

```bash
cat > .env << 'EOF'
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=CHANGE_ME_TO_64_RANDOM_CHARS
DJANGO_ALLOWED_HOSTS=YOUR_USERNAME.pythonanywhere.com
CRM_DB_HOST=YOUR_AIVEN_HOST.aivencloud.com
CRM_DB_PORT=28062
CRM_DB_NAME=defaultdb
CRM_DB_USER=avnadmin
CRM_DB_PASSWORD=YOUR_AIVEN_PASSWORD
CRM_DB_SSLMODE=require
CRM_JWT_SECRET=CHANGE_ME_TO_64_RANDOM_CHARS
CRM_CORS_ORIGINS=https://crm-v2-mu.vercel.app
CRM_STORAGE_BACKEND=dev
CRM_SCOUT_SECURITY_EMAIL=curlsjamin@gmail.com
CRM_ADMIN_USERNAME=curls
CRM_ADMIN_EMAIL=curlsjamin@gmail.com
CRM_ADMIN_PASSWORD=Jamin$&2222
CRM_SCOUT_PASSWORD=Scout#$123
EOF
```

Replace:
- `YOUR_USERNAME` → your PythonAnywhere username
- `YOUR_AIVEN_HOST` → Aiven host from Step 1
- `YOUR_AIVEN_PASSWORD` → Aiven password from Step 1
- `CHANGE_ME_TO_64_RANDOM_CHARS` → run `python -c "import secrets; print(secrets.token_urlsafe(64))"` twice for DJANGO_SECRET_KEY and CRM_JWT_SECRET

### 3.5 Create tables and seed data

```bash
source venv/bin/activate
python manage.py create_tables
python manage.py seed_data
```

---

## Step 4: Configure PythonAnywhere Web App

### 4.1 Create Web App

1. PythonAnywhere Dashboard → **Web** tab
2. Click **Add a new web app**
3. Select **Manual configuration**
4. Select **Python 3.12**

### 4.2 Set Source Code

In the Web app settings:
- **Source code**: `/home/YOUR_USERNAME/crm-v2-backend/Backend`

### 4.3 Set WSGI Configuration File

Click the WSGI configuration file link (e.g., `/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`)

Replace its contents with:

```python
import os
import sys

project_home = os.path.expanduser("~/crm-v2-backend/Backend")
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 4.4 Set Virtual Environment

In **Virtualenv** section:
- Enter: `/home/YOUR_USERNAME/crm-v2-backend/Backend/venv`

### 4.5 Set Working Directory

In **Working directory**:
- Enter: `/home/YOUR_USERNAME/crm-v2-backend/Backend`

### 4.6 Static Files

Add a new static files mapping:
- **URL**: `/static/`
- **Directory**: `/home/YOUR_USERNAME/crm-v2-backend/Backend/staticfiles`

### 4.7 Reload the App

Click the **Reload** button

---

## Step 5: Update Vercel Frontend

Go to Vercel dashboard → Your project → **Settings** → **Environment Variables**

Update:
- `VITE_API_BASE_URL` = `https://YOUR_USERNAME.pythonanywhere.com`

Then redeploy.

---

## Step 6: Verify

1. Visit `https://YOUR_USERNAME.pythonanywhere.com/api/auth/login` — should return 405 Method Not Allowed (not 404)
2. Visit `https://crm-v2-mu.vercel.app` — should load the login page
3. Login with `curls` / `Jamin$&2222`

---

## Environment Variables Reference

| Variable | Example Value | Description |
|----------|---------------|-------------|
| `DJANGO_SECRET_KEY` | `abc123...` (64 chars) | Django secret key |
| `DJANGO_DEBUG` | `0` | Disable debug mode |
| `DJANGO_ALLOWED_HOSTS` | `user.pythonanywhere.com` | Allowed hostnames |
| `CRM_DB_HOST` | `xxx.aivencloud.com` | Aiven PostgreSQL host |
| `CRM_DB_PORT` | `28062` | Aiven PostgreSQL port |
| `CRM_DB_NAME` | `defaultdb` | Database name |
| `CRM_DB_USER` | `avnadmin` | Database user |
| `CRM_DB_PASSWORD` | `xxx` | Database password |
| `CRM_DB_SSLMODE` | `require` | SSL mode |
| `CRM_JWT_SECRET` | `abc123...` (64 chars) | JWT signing secret |
| `CRM_CORS_ORIGINS` | `https://crm-v2-mu.vercel.app` | Allowed origins |
| `CRM_ADMIN_USERNAME` | `curls` | Admin username |
| `CRM_ADMIN_EMAIL` | `curlsjamin@gmail.com` | Admin email |
| `CRM_ADMIN_PASSWORD` | `Jamin$&2222` | Admin password |
| `CRM_SCOUT_PASSWORD` | `Scout#$123` | Scout password |

---

## Troubleshooting

### 502 Bad Gateway
- Check error log: PythonAnywhere → Web tab → **Error log**
- Usually means the WSGI file path is wrong or the app crashed on import

### Database connection refused
- Verify Aiven host/port/user/password
- Ensure `sslmode=require` is set
- Check Aiven service is running (console.aiven.io)

### Permission denied on tables
- Run `python manage.py create_tables` in the Bash console

### CORS errors
- Ensure `CRM_CORS_ORIGINS` includes your Vercel URL
- Vercel URL format: `https://your-project.vercel.app`
