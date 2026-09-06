# CRM V2

A full-stack CRM application with AI-powered campaigns, role-based access control, client portal, and comprehensive sales pipeline management.

## Architecture

```
CRM-V2/
├── Backend/          # Python Django REST API (SQLAlchemy + MySQL)
├── Frontend/         # React SPA (Vite)
├── ClientPortal/     # Customer-facing portal (React)
├── deploy/           # SQL migrations, deployment configs
├── .gitignore
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.13, Django REST Framework, SQLAlchemy, JWT auth |
| **Frontend** | React 18, React Router, Vite, CSS custom properties |
| **Database** | MySQL 8.0+ |
| **Auth** | JWT (PyJWT + bcrypt), role-based access control (RBAC) |
| **AI** | OpenAI DALL-E 3 (billboard generation), Pillow fallback |
| **Storage** | Local filesystem (dev) / S3-compatible (production) |

## Features

- **Client Management** — Full 360° customer view with contacts, addresses, relationships, documents
- **Quotes** — Multi-step quote builder with templates, PDF generation, client portal responses
- **Sales Orders** — Order lifecycle management with payments, receipts, financial calculations
- **Campaigns** — AI-powered creative generation, multi-channel campaign management
- **Leads** — Lead capture, scoring, qualification tracking
- **Client Portal** — Customer-facing portal for quotes, orders, complaints, rewards
- **Roles & Rights** — Granular permission system with access scope controls
- **Audit Logging** — Complete audit trail for all entity changes
- **USSD Integration** — USSD session and transaction support

## Project Structure

### Backend

```
Backend/
├── config/              # Django settings, URLs, WSGI
├── iam/                 # Identity & access management (users, roles, permissions)
├── clients/             # Customer management
├── quotes/              # Quote builder and management
├── sales_orders/        # Sales order lifecycle
├── campaigns/           # Campaign management and AI creative generation
├── leads/               # Lead capture and qualification
├── activities/          # Activity tracking and notes
├── communications/      # SMS, email, call logging
├── documents/           # Document management
├── portal/              # Client portal backend
├── customer360/         # 360° customer view aggregation
├── accounting/          # Accounting integration
├── referrals/           # Referral program
├── attribution/         # Multi-touch attribution
├── momentum/            # Momentum wallet/rewards
├── ussd/                # USSD integration
├── event_engine/        # Domain event processing
├── common/              # Shared utilities, base classes, middleware
├── deploy/sql/          # SQL migration scripts
├── manage.py            # Django management entry point
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variable template
```

### Frontend

```
Frontend/
├── src/
│   ├── api/             # API client functions
│   ├── auth/            # Authentication context and guards
│   ├── components/      # Reusable UI components
│   ├── pages/           # Page components by module
│   ├── styles/          # CSS stylesheets
│   ├── utils/           # Helpers, constants, formatters
│   └── App.jsx          # Root router
├── public/              # Static assets (logos, images)
├── package.json
└── .env.example
```

## Local Development Setup

### Prerequisites

- Python 3.13+
- Node.js 18+
- MySQL 8.0+
- Git

### 1. Clone the repository

```bash
git clone <repository-url>
cd CRM-V2
```

### 2. Database setup

```bash
# Create the database
mysql -u root -p -e "CREATE DATABASE crm_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run migrations (in order)
cd Backend
mysql -u root -p crm_v2 < deploy/sql/002_clients_phase_schema.sql
mysql -u root -p crm_v2 < deploy/sql/003_seed_clients_phase.sql
# ... run remaining migration files in numerical order
```

### 3. Backend setup

```bash
cd Backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your database credentials and secrets

# Run the server
python manage.py runserver
```

Backend runs at `http://localhost:8000`

### 4. Frontend setup

```bash
cd Frontend

# Install dependencies
npm install

# Configure environment
copy .env.example .env
# Edit .env if needed (default API URL is http://localhost:8000)

# Start dev server
npm run dev
```

Frontend runs at `http://localhost:5173`

### 5. Initial data

```bash
# Create admin user
python manage.py create_admin

# Create scout evaluation account
python manage.py create_scout_account
```

## Environment Variables

See `Backend/.env.example` and `Frontend/.env.example` for all configurable options.

Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `CRM_DB_PASSWORD` | MySQL password | Yes |
| `CRM_JWT_SECRET` | JWT signing secret (64+ chars) | Yes |
| `DJANGO_SECRET_KEY` | Django secret key | Yes |
| `CRM_OPENAI_API_KEY` | OpenAI API key for AI creatives | No |
| `VITE_API_URL` | Backend API URL for frontend | Yes |

## Testing

```bash
cd Backend
pytest
```

## Production Deployment

### Environment

- Set `DJANGO_DEBUG=0`
- Use a production MySQL instance
- Set strong `DJANGO_SECRET_KEY` and `CRM_JWT_SECRET`
- Configure `CORS_ALLOWED_ORIGINS` for your domain
- Set `CRM_STORAGE_BACKEND=s3` for file storage
- Configure SMS provider credentials

### Render.com (Recommended)

1. Create a MySQL database addon
2. Set environment variables in the Render dashboard
3. Deploy backend as a Web Service
4. Deploy frontend as a Static Site

### Database Migrations

SQL migrations are in `Backend/deploy/sql/`. Run them in numerical order against your production database.

## Security Notes

- **Never commit `.env` files** — use `.env.example` as a template
- **Never commit database dumps** containing real customer data
- **Never commit API keys, passwords, or secrets** — use environment variables
- **JWT secrets** must be unique per environment and at least 64 characters
- **Production** should use HTTPS, proper CORS restrictions, and rate limiting
- **Scout account** provides automated security monitoring with least-privilege access

## License

Private — All rights reserved.
