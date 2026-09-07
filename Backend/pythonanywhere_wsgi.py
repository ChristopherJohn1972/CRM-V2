"""
PythonAnywhere WSGI configuration for CRM V2.

Upload this file to PythonAnywhere as your WSGI configuration file.
Path: ~/crm-v2-backend/wsgi.py
"""

import os
import sys

# Add your project directory to sys.path
project_home = os.path.expanduser("~/crm-v2-backend")
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Set environment variables (or use PythonAnywhere's Web app environment variables)
# os.environ["CRM_DB_HOST"] = "your-aiven-host.aivencloud.com"
# os.environ["CRM_DB_PORT"] = "28062"
# os.environ["CRM_DB_NAME"] = "defaultdb"
# os.environ["CRM_DB_USER"] = "avnadmin"
# os.environ["CRM_DB_PASSWORD"] = "your-aiven-password"
# os.environ["CRM_JWT_SECRET"] = "your-64-char-secret"
# os.environ["DJANGO_SECRET_KEY"] = "your-django-secret"
# os.environ["DJANGO_ALLOWED_HOSTS"] = "yourusername.pythonanywhere.com"
# os.environ["CRM_CORS_ORIGINS"] = "https://crm-v2-mu.vercel.app"
# os.environ["DJANGO_DEBUG"] = "0"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
