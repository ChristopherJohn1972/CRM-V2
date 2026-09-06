import logging
from datetime import datetime, timezone

import sqlalchemy as sa
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from common.db import SessionLocal
from iam.models import User, UserSession, UserStatus
from iam.permissions import UserPrincipal
from iam.services import decode_access_token

logger = logging.getLogger(__name__)


class TokenTypeError(AuthenticationFailed):
    pass


class JWTBearerAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]
        payload = decode_access_token(token)

        if payload.get("typ", "internal") != "internal":
            raise TokenTypeError("Unsupported token type for this endpoint.")

        session = SessionLocal()
        try:
            user = session.get(User, int(payload["sub"]))
            if user is None:
                raise AuthenticationFailed("User not found.")
            if user.status != UserStatus.ACTIVE.value:
                raise AuthenticationFailed("User account is not active.")

            user_session = session.get(UserSession, int(payload["sid"]))
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if user_session is None or user_session.revoked_at is not None:
                raise AuthenticationFailed("Session has been revoked.")
            if user_session.expires_at < now:
                raise AuthenticationFailed("Session has expired.")

            principal = UserPrincipal(session, user)
            request.auth_session = session
            # The principal resolved its permissions and scope eagerly, so the
            # session is no longer needed for this request.
            session.close()
            return (principal, token)
        except AuthenticationFailed:
            session.close()
            raise
        except Exception:
            session.close()
            logger.exception("authentication failed unexpectedly")
            raise AuthenticationFailed("Invalid credentials.")

    def authenticate_header(self, request):
        return "Bearer"
