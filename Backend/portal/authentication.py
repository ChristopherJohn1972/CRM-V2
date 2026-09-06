import logging
from datetime import datetime, timezone

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from common.db import SessionLocal
from portal.models import PortalSession, PortalUser, PortalUserStatus
from portal.permissions import PortalPrincipal
from portal.services import decode_portal_access_token

logger = logging.getLogger(__name__)


class PortalJWTBearerAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]
        payload = decode_portal_access_token(token)

        session = SessionLocal()
        try:
            portal_user = session.get(PortalUser, int(payload["sub"]))
            if portal_user is None:
                raise AuthenticationFailed("Portal user not found.")
            if portal_user.status != PortalUserStatus.ACTIVE.value:
                raise AuthenticationFailed("Portal account is not active.")

            portal_session = session.get(PortalSession, int(payload["sid"]))
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if portal_session is None or portal_session.revoked_at is not None:
                raise AuthenticationFailed("Session has been revoked.")
            if portal_session.expires_at < now:
                raise AuthenticationFailed("Session has expired.")

            principal = PortalPrincipal(session, portal_user)
            try:
                from portal.services import PortalAuthenticationService

                principal.portal_user._must_change_password = PortalAuthenticationService.must_change_password(
                    session, portal_user.portal_user_id
                )
            except Exception:
                principal.portal_user._must_change_password = False

            request.auth_session = session
            return (principal, token)
        except AuthenticationFailed:
            session.close()
            raise
        except Exception:
            session.close()
            logger.exception("portal authentication failed unexpectedly")
            raise AuthenticationFailed("Invalid credentials.")

    def authenticate_header(self, request):
        return "Bearer"