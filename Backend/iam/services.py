import hashlib
import logging
import secrets

import sqlalchemy as sa
import jwt
from datetime import datetime, timedelta, timezone

import bcrypt
from django.conf import settings

from common.exceptions import APIError
from iam.models import AuthenticationCredential, PasswordResetToken, User, UserSession, UserStatus

logger = logging.getLogger(__name__)

BCRYPT_PREFIX = b"$2"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        if hashed.startswith("$2"):
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        return bcrypt.checkpw(plain.encode("utf-8"), BCRYPT_PREFIX + hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def issue_access_token(user_id, session_id) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": "internal",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise APIError("Token has expired.", status_code=401, error_code="token_expired")
    except jwt.InvalidTokenError:
        raise APIError("Invalid token.", status_code=401, error_code="token_invalid")
    return payload


def get_user_by_credentials(session, login: str):
    stmt = sa.select(User).where(
        (User.username == login) | (User.email == login)
    )
    return session.execute(stmt).scalar_one_or_none()


def authenticate(session, login: str, password: str):
    user = get_user_by_credentials(session, login)
    if user is None:
        return None

    credential = session.execute(
        sa.select(AuthenticationCredential).where(
            AuthenticationCredential.user_id == user.user_id
        )
    ).scalar_one_or_none()
    if credential is None or not verify_password(password, credential.password_hash):
        _increment_failed_attempts(session, credential)
        session.commit()
        return None

    if user.status != UserStatus.ACTIVE.value:
        raise APIError("User account is not active.", status_code=403, error_code="account_inactive")

    if credential.locked_until and credential.locked_until > datetime.now(timezone.utc).replace(tzinfo=None):
        raise APIError("Account temporarily locked.", status_code=403, error_code="account_locked")

    credential.failed_login_attempts = 0
    credential.locked_until = None
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.commit()
    return user


def _increment_failed_attempts(session, credential):
    if credential is None:
        return
    credential.failed_login_attempts += 1
    if credential.failed_login_attempts >= 5:
        credential.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15)


def create_session(session, user, ip_address, user_agent) -> UserSession:
    token = secrets.token_urlsafe(32)
    user_session = UserSession(
        user_id=user.user_id,
        session_token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        ip_address=ip_address,
        user_agent=(user_agent or "")[:500],
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            minutes=settings.JWT_ACCESS_TTL_MINUTES
        ),
    )
    session.add(user_session)
    session.flush()
    return user_session


def revoke_session(session, user_session_id):
    user_session = session.get(UserSession, user_session_id)
    if user_session:
        user_session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)


RESET_TOKEN_TTL_MINUTES = 30


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_reset_token(session, user_id) -> str:
    token = secrets.token_urlsafe(32)
    session.add(
        PasswordResetToken(
            user_id=user_id,
            token_hash=_token_hash(token),
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
        )
    )
    session.flush()
    return token


def reset_password(session, token: str, new_password: str):
    if len(new_password) < 8:
        raise APIError(
            "Password must be at least 8 characters.",
            status_code=422,
            error_code="password_too_short",
            field_errors={"new_password": "Password must be at least 8 characters."},
        )

    row = session.execute(
        sa.select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _token_hash(token)
        )
    ).scalar_one_or_none()

    if row is None:
        raise APIError("Invalid password reset token.", status_code=400, error_code="invalid_reset_token")
    if row.consumed_at is not None:
        raise APIError("Password reset token has already been used.", status_code=400, error_code="reset_token_used")
    if row.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise APIError("Password reset token has expired.", status_code=400, error_code="reset_token_expired")

    user = session.get(User, row.user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise APIError("Account is not active.", status_code=403, error_code="account_inactive")

    credential = session.execute(
        sa.select(AuthenticationCredential).where(
            AuthenticationCredential.user_id == user.user_id
        )
    ).scalar_one_or_none()

    if credential is None:
        credential = AuthenticationCredential(user_id=user.user_id)
        session.add(credential)

    credential.password_hash = hash_password(new_password)
    credential.password_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    credential.failed_login_attempts = 0
    credential.locked_until = None
    row.consumed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.flush()
    return user
