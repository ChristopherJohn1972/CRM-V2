import os
from pathlib import Path

from django.http import Http404, FileResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from iam.views import ForgotPasswordView, LoginView, LogoutView, MeView, RegisterView, ResetPasswordView
from config import settings


def serve_storage(request, path=""):
    storage_root = Path(getattr(settings, "STORAGE_ROOT", "storage/"))
    if not os.path.isabs(storage_root):
        storage_root = Path(settings.BASE_DIR) / storage_root
    file_path = storage_root / path
    if not file_path.exists() or not file_path.is_file():
        raise Http404("File not found")
    return FileResponse(open(file_path, "rb"), content_type="application/octet-stream")


urlpatterns = [
    path("api/auth/login", csrf_exempt(LoginView.as_view()), name="auth-login"),
    path("api/auth/logout", csrf_exempt(LogoutView.as_view()), name="auth-logout"),
    path("api/auth/me", csrf_exempt(MeView.as_view()), name="auth-me"),
    path("api/auth/register", csrf_exempt(RegisterView.as_view()), name="auth-register"),
    path("api/auth/forgot-password", csrf_exempt(ForgotPasswordView.as_view()), name="auth-forgot-password"),
    path("api/auth/reset-password", csrf_exempt(ResetPasswordView.as_view()), name="auth-reset-password"),
    path("api/storage/<path:path>", serve_storage, name="serve-storage"),
    path("api/", include("clients.urls")),
    path("api/", include("activities.urls")),
    path("api/", include("communications.urls")),
    path("api/", include("documents.urls")),
    path("api/", include("accounting.urls")),
    path("api/", include("customer360.urls")),
    path("api/", include("iam.urls")),
    path("api/", include("portal.urls")),
    path("api/", include("quotes.urls")),
    path("api/", include("sales_orders.urls")),
    path("api/", include("campaigns.urls")),
    path("api/", include("leads.urls")),
    path("api/", include("event_engine.urls")),
    path("api/", include("attribution.urls")),
    path("api/", include("referrals.urls")),
    path("api/", include("momentum.urls")),
    path("api/", include("ussd.urls")),
]