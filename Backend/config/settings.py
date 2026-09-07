import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "whitenoise",
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
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "common.middleware.RequestContextMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    h.strip()
    for h in os.getenv("CRM_CORS_ORIGINS", "").split(",")
    if h.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "x-csrftoken",
    "x-requested-with",
]

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
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("CRM_DB_NAME", "crm_v2"),
        "USER": os.getenv("CRM_DB_USER", "postgres"),
        "PASSWORD": os.getenv("CRM_DB_PASSWORD", ""),
        "HOST": os.getenv("CRM_DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("CRM_DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": os.getenv("CRM_DB_SSLMODE", "require"),
        },
    }
}

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

FRONTEND_DIR = STATIC_ROOT / "frontend"

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

EMAIL_BACKEND = os.getenv("CRM_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("CRM_EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("CRM_EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("CRM_EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = os.getenv("CRM_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("CRM_EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("CRM_DEFAULT_FROM_EMAIL", "CRM V2 <noreply@crm.local>")

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