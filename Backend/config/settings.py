import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

pymysql.install_as_MySQLdb()

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "common",
    "iam",
    "clients",
    "quotes",
    "activities",
    "communications",
    "documents",
    "accounting",
    "customer360",
    "portal",
    "sales_orders",
    "campaigns",
    "leads",
    "event_engine",
    "attribution",
    "referrals",
    "momentum",
    "ussd",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "common.middleware.RequestContextMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {},
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("CRM_DB_NAME", "crm_v2"),
        "USER": os.getenv("CRM_DB_USER", "root"),
        "PASSWORD": os.getenv("CRM_DB_PASSWORD", ""),
        "HOST": os.getenv("CRM_DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("CRM_DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "iam.authentication.JWTBearerAuthentication",
        "portal.authentication.PortalJWTBearerAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "iam.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

AUTHENTICATION_BACKENDS = []

# Django's auth/contenttypes tables are never used (SQLAlchemy owns the schema;
# auth is JWT-based). Keep the apps for DRF's AnonymousUser default but tell
# Django there are no migrations to apply, so `runserver` stops nagging.
MIGRATION_MODULES = {
    "auth": None,
    "contenttypes": None,
}

JWT_SECRET = os.getenv("CRM_JWT_SECRET", SECRET_KEY)
JWT_ALGORITHM = os.getenv("CRM_JWT_ALGORITHM", "HS256")
JWT_ACCESS_TTL_MINUTES = int(os.getenv("CRM_JWT_ACCESS_TTL_MINUTES", "60"))

STORAGE_BACKEND = os.getenv("CRM_STORAGE_BACKEND", "dev")
STORAGE_ROOT = str(BASE_DIR / (os.getenv("CRM_STORAGE_ROOT", "storage/").lstrip("./")))
if not os.path.isabs(STORAGE_ROOT):
    STORAGE_ROOT = str(BASE_DIR / STORAGE_ROOT)

S3_BUCKET = os.getenv("CRM_S3_BUCKET", "")
S3_REGION = os.getenv("CRM_S3_REGION", "")
S3_PRESIGNED_URL_TTL = int(os.getenv("CRM_S3_PRESIGNED_URL_TTL", "300"))

ACCOUNTING_BASE_URL = os.getenv("CRM_ACCOUNTING_BASE_URL", "").rstrip("/")
ACCOUNTING_API_TOKEN = os.getenv("CRM_ACCOUNTING_API_TOKEN", "")
ACCOUNTING_TIMEOUT_SECONDS = int(os.getenv("CRM_ACCOUNTING_TIMEOUT_SECONDS", "3"))

SMS_PROVIDER_URL = os.getenv("CRM_SMS_PROVIDER_URL", "")
SMS_PROVIDER_TOKEN = os.getenv("CRM_SMS_PROVIDER_TOKEN", "")
WEBHOOK_SECRET = os.getenv("CRM_WEBHOOK_SECRET", "")

OPENAI_API_KEY = os.getenv("CRM_OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("CRM_OPENAI_MODEL", "dall-e-3")

SCOUT_SECURITY_RECIPIENT = os.getenv("CRM_SCOUT_SECURITY_EMAIL", "")

PASSWORD_HASHER = "bcrypt"

# Portal boundary settings
PORTAL_COMPANY_NAME = os.getenv("CRM_PORTAL_COMPANY_NAME", "CRM V2")
PORTAL_LOCKOUT_ATTEMPTS = int(os.getenv("CRM_PORTAL_LOCKOUT_ATTEMPTS", "5"))
PORTAL_LOCKOUT_MINUTES = int(os.getenv("CRM_PORTAL_LOCKOUT_MINUTES", "15"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s level=%(levelname)s logger=%(name)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}