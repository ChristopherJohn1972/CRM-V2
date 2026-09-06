import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message, status_code=400, error_code=None, field_errors=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.field_errors = field_errors


class PermissionDeniedError(APIError):
    def __init__(self, message="You do not have permission to perform this action."):
        super().__init__(message, status_code=403, error_code="permission_denied")


class NotFoundError(APIError):
    def __init__(self, message="Resource not found."):
        super().__init__(message, status_code=404, error_code="not_found")


class ConflictError(APIError):
    def __init__(self, message, error_code="conflict"):
        super().__init__(message, status_code=409, error_code=error_code)


class UnprocessableEntityError(APIError):
    def __init__(self, message, field_errors=None):
        super().__init__(
            message, status_code=422, error_code="unprocessable_entity", field_errors=field_errors
        )


class ValidationError_(APIError):
    def __init__(self, message, field_errors=None):
        super().__init__(
            message, status_code=400, error_code="validation_error", field_errors=field_errors
        )


def api_exception_handler(exc, context):
    if isinstance(exc, APIError):
        body = {
            "detail": exc.message,
            "code": exc.error_code,
        }
        if exc.field_errors:
            body["field_errors"] = exc.field_errors
        return Response(body, status=exc.status_code)

    from rest_framework.views import exception_handler as drf_exception_handler

    return drf_exception_handler(exc, context)
