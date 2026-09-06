import threading

from django.db import connection

_correlation_id = threading.local()


def set_request_context(request) -> None:
    _correlation_id.value = request.META.get("HTTP_X_REQUEST_ID") or ""


def get_correlation_id() -> str:
    return getattr(_correlation_id, "value", None) or ""


def get_request_context(request):
    return {
        "ip_address": request.META.get("REMOTE_ADDR"),
        "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:500],
        "correlation_id": request.META.get("HTTP_X_REQUEST_ID") or "",
    }
