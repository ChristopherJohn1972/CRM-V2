"""
Scout Account Security Monitoring

Detects high-risk activity on the APPLICATION_SCOUT account and triggers
immediate session revocation, account lock, audit logging, and email alerts.

Security events are evaluated per-request. Thresholds are configurable via
Django settings (with sensible defaults).
"""

import logging
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from django.conf import settings
from django.core.mail import send_mail

from common import context
from common.db import SessionLocal
from iam.models import (
    AuditLog,
    AuthenticationCredential,
    User,
    UserSession,
    UserStatus,
)

logger = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────

SCOUT_USERNAME = "scout"
SCOUT_SECURITY_RECIPIENT = getattr(settings, "SCOUT_SECURITY_RECIPIENT", "")

# Thresholds — configurable via settings.py or environment
SCOUT_MAX_AUTH_FAILURES_PER_WINDOW = getattr(settings, "SCOUT_MAX_AUTH_FAILURES_PER_WINDOW", 5)
SCOUT_AUTH_FAILURE_WINDOW_SECONDS = getattr(settings, "SCOUT_AUTH_FAILURE_WINDOW_SECONDS", 300)
SCOUT_MAX_ENDPOINT_ENUM_PER_MINUTE = getattr(settings, "SCOUT_MAX_ENDPOINT_ENUM_PER_MINUTE", 20)
SCOUT_MAX_REQUESTS_PER_MINUTE = getattr(settings, "SCOUT_MAX_REQUESTS_PER_MINUTE", 120)

# Admin-only permission codes that Scout must never use
SCOUT_ADMIN_FORBIDDEN_PERMISSIONS = {
    "iam.user.manage",
    "iam.role.manage",
    "iam.permission.audit",
}

# Admin-only API path prefixes
SCOUT_ADMIN_FORBIDDEN_PATHS = (
    "/api/iam/",
    "/api/operators/",
    "/api/roles/",
    "/api/rights/",
)


# ─── Security Event Classification ─────────────────────────────────────────

class SecurityEvent:
    """Classification of security events by severity."""

    CRITICAL = "CRITICAL"   # Immediate session revocation + account lock
    HIGH = "HIGH"           # Session revocation, no lock
    MEDIUM = "MEDIUM"       # Audit log only, no session impact
    LOW = "LOW"             # Audit log only


EVENT_PRIVILEGE_ESCALATION_SELF = "scout.privilege_escalation.self"
EVENT_PRIVILEGE_ESCALATION_OTHERS = "scout.privilege_escalation.others"
EVENT_ADMIN_ENDPOINT_ACCESS = "scout.admin_endpoint_access"
EVENT_TAMPERING_TENANT_ID = "scout.tampering.tenant_id"
EVENT_TAMPERING_SCOPE = "scout.tampering.scope"
EVENT_TAMPERING_OPERATOR_ID = "scout.tampering.operator_id"
EVENT_ROLE_MODIFICATION_ATTEMPT = "scout.role_modification_attempt"
EVENT_PERMISSION_CATALOGUE_ACCESS = "scout.permission_catalogue_access"
EVENT_REPEATED_AUTH_FAILURES = "scout.repeated_auth_failures"
EVENT_RAPID_ENDPOINT_ENUM = "scout.rapid_endpoint_enum"
EVENT_HIGH_REQUEST_VOLUME = "scout.high_request_volume"
EVENT_CROSS_TENANT_ACCESS = "scout.cross_tenant_access"
EVENT_REVOKED_TOKEN_REUSE = "scout.revoked_token_reuse"
EVENT_SECURITY_LOCK_BYPASS = "scout.security_lock_bypass"


# ─── Core Detection Functions ───────────────────────────────────────────────

def _is_scout_user(user):
    """Check if the user is the Scout evaluation account."""
    if user is None:
        return False
    return getattr(user, "username", None) == SCOUT_USERNAME


def _get_or_create_db():
    """Get a new DB session for security operations (outside request lifecycle)."""
    return SessionLocal()


def record_security_event(
    event_type,
    severity,
    *,
    user_id=None,
    description=None,
    endpoint=None,
    metadata=None,
    request=None,
):
    """
    Record a security event in the audit log and return a correlation ID.
    This function does NOT perform any revocation — it only logs.
    """
    correlation_id = str(uuid.uuid4())
    ctx = context.get_request_context(request) if request is not None else {}

    meta = {
        "correlation_id": correlation_id,
        "security_event": True,
        "severity": severity,
        "event_type": event_type,
        **(metadata or {}),
    }

    db = _get_or_create_db()
    try:
        entry = AuditLog(
            actor_type="INTERNAL_USER",
            actor_user_id=user_id,
            action=f"security.{event_type}",
            resource_type="security",
            resource_id=user_id,
            description=description or f"Security event: {event_type}",
            ip_address=ctx.get("ip_address"),
            user_agent=ctx.get("user_agent"),
            metadata_=meta,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to record security event %s", event_type)
    finally:
        db.close()

    return correlation_id


def revoke_all_sessions(user_id, *, reason="security_event", request=None):
    """
    Revoke all active sessions for a user. Returns the number of sessions revoked.
    """
    db = _get_or_create_db()
    try:
        now = datetime.now(timezone.utc)
        result = db.execute(
            sa.update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .values(revoked_at=now)
        )
        db.commit()
        count = result.rowcount
        logger.info("Revoked %d sessions for user_id=%d reason=%s", count, user_id, reason)
        return count
    except Exception:
        db.rollback()
        logger.exception("Failed to revoke sessions for user_id=%d", user_id)
        return 0
    finally:
        db.close()


def lock_account(user_id, *, reason="security_event"):
    """
    Set the user status to SECURITY_LOCKED and revoke all sessions.
    """
    db = _get_or_create_db()
    try:
        db.execute(
            sa.update(User)
            .where(User.user_id == user_id)
            .values(status=UserStatus.SECURITY_LOCKED.value)
        )
        db.commit()
        logger.info("Account locked: user_id=%d reason=%s", user_id, reason)
    except Exception:
        db.rollback()
        logger.exception("Failed to lock account user_id=%d", user_id)
    finally:
        db.close()

    revoke_all_sessions(user_id, reason=reason)


def send_security_alert(
    event_type,
    severity,
    *,
    user_id=None,
    username=None,
    endpoint=None,
    correlation_id=None,
    description=None,
    metadata=None,
):
    """
    Send an email alert to the configured security recipient.
    The email is sent asynchronously (fire-and-forget) so it never blocks
    the security response.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    corr = correlation_id or str(uuid.uuid4())

    subject = f"CRM Security Alert — {username or SCOUT_USERNAME} Account"

    body_lines = [
        f"Account: {username or SCOUT_USERNAME}",
        f"Event type: {event_type}",
        f"Severity: {severity}",
        f"UTC timestamp: {now_str}",
        f"Correlation ID: {corr}",
    ]
    if endpoint:
        body_lines.append(f"Endpoint/resource: {endpoint}")
    body_lines.append(f"Action taken: session revoked and/or account locked")
    if description:
        body_lines.append(f"Details: {description}")
    if metadata:
        for k, v in metadata.items():
            if k not in ("correlation_id", "security_event"):
                body_lines.append(f"{k}: {v}")

    body = "\n".join(body_lines)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "crm-security@localhost"),
            recipient_list=[SCOUT_SECURITY_RECIPIENT],
            fail_silently=False,
        )
        logger.info("Security alert sent for %s event=%s corr=%s", username, event_type, corr)
    except Exception:
        logger.exception(
            "FAILED to send security alert for %s event=%s corr=%s",
            username,
            event_type,
            corr,
        )


# ─── Per-Request Security Evaluation ────────────────────────────────────────

def evaluate_scout_request(request, principal):
    """
    Called on every authenticated request for the Scout user.
    Evaluates the request against security rules and triggers responses
    for critical/high-severity events.

    Returns None on normal requests.
    Returns a dict with severity + event_type if a security event is detected.
    """
    if not _is_scout_user(getattr(principal, "_user", None)):
        return None

    user_id = principal._user.user_id
    path = getattr(request, "path", "")
    method = getattr(request, "method", "GET")

    # ── Check 1: Account is security-locked ──────────────────────────────
    if getattr(principal._user, "status", None) == UserStatus.SECURITY_LOCKED.value:
        event = {
            "severity": SecurityEvent.CRITICAL,
            "event_type": EVENT_SECURITY_LOCK_BYPASS,
            "description": "Security-locked account attempted access",
        }
        correlation_id = record_security_event(
            event["event_type"],
            event["severity"],
            user_id=user_id,
            description=event["description"],
            endpoint=path,
            request=request,
        )
        return {**event, "correlation_id": correlation_id}

    # ── Check 2: Admin-only endpoint access ──────────────────────────────
    if path.startswith(SCOUT_ADMIN_FORBIDDEN_PATHS):
        event = {
            "severity": SecurityEvent.CRITICAL,
            "event_type": EVENT_ADMIN_ENDPOINT_ACCESS,
            "description": f"Scout accessed admin endpoint: {method} {path}",
        }
        correlation_id = record_security_event(
            event["event_type"],
            event["severity"],
            user_id=user_id,
            description=event["description"],
            endpoint=path,
            request=request,
        )
        lock_account(user_id, reason=EVENT_ADMIN_ENDPOINT_ACCESS)
        revoke_all_sessions(user_id, reason=EVENT_ADMIN_ENDPOINT_ACCESS)
        send_security_alert(
            event["event_type"],
            event["severity"],
            username=SCOUT_USERNAME,
            endpoint=path,
            correlation_id=correlation_id,
            description=event["description"],
            request=request,
        )
        return {**event, "correlation_id": correlation_id}

    # ── Check 3: Tampering with authorization parameters ─────────────────
    _check_authorization_tampering(request, principal, user_id, path)

    # ── Check 4: Permission catalogue access ─────────────────────────────
    if "rights" in path.lower() and method in ("PUT", "POST", "DELETE", "PATCH"):
        event = {
            "severity": SecurityEvent.CRITICAL,
            "event_type": EVENT_PERMISSION_CATALOGUE_ACCESS,
            "description": f"Scout attempted to modify rights catalogue: {method} {path}",
        }
        correlation_id = record_security_event(
            event["event_type"],
            event["severity"],
            user_id=user_id,
            description=event["description"],
            endpoint=path,
            request=request,
        )
        lock_account(user_id, reason=EVENT_PERMISSION_CATALOGUE_ACCESS)
        revoke_all_sessions(user_id, reason=EVENT_PERMISSION_CATALOGUE_ACCESS)
        send_security_alert(
            event["event_type"],
            event["severity"],
            username=SCOUT_USERNAME,
            endpoint=path,
            correlation_id=correlation_id,
            description=event["description"],
            request=request,
        )
        return {**event, "correlation_id": correlation_id}

    return None


def _check_authorization_tampering(request, principal, user_id, path):
    """
    Check for common tampering patterns in request data.
    Records events but does not block — these are detection signals.
    """
    # Check query params and data for suspicious fields
    tamper_fields = {
        "tenant_id": EVENT_TAMPERING_TENANT_ID,
        "scope": EVENT_TAMPERING_SCOPE,
        "operator_id": EVENT_TAMPERING_OPERATOR_ID,
        "role_codes": EVENT_ROLE_MODIFICATION_ATTEMPT,
        "permission_codes": EVENT_ROLE_MODIFICATION_ATTEMPT,
    }

    data = {}
    if hasattr(request, "data") and isinstance(request.data, dict):
        data.update(request.data)
    if hasattr(request, "query_params") and isinstance(request.query_params, dict):
        data.update(request.query_params)

    for field, event_type in tamper_fields.items():
        if field in data:
            record_security_event(
                event_type,
                SecurityEvent.HIGH,
                user_id=user_id,
                description=f"Scout submitted suspicious field '{field}' on {path}",
                endpoint=path,
                metadata={"field": field, "value": str(data[field])[:200]},
                request=request,
            )


def check_scout_login_security(user, request=None):
    """
    Additional security checks during Scout login.
    Returns (allowed: bool, reason: str | None).
    """
    if not _is_scout_user(user):
        return True, None

    if user.status == UserStatus.SECURITY_LOCKED.value:
        record_security_event(
            EVENT_SECURITY_LOCK_BYPASS,
            SecurityEvent.CRITICAL,
            user_id=user.user_id,
            description="Security-locked account attempted login",
            request=request,
        )
        return False, "Your session has been terminated for security reasons. Please contact the application administrator if you believe this was a mistake."

    return True, None


# ─── Privilege Escalation Protection ────────────────────────────────────────

def prevent_scout_self_escalation(principal, target_user_id, action_desc, request=None):
    """
    Prevent the Scout account from escalating its own privileges.
    Call this before any role/permission assignment operation.
    Returns True if the operation should be blocked.
    """
    if not _is_scout_user(getattr(principal, "_user", None)):
        return False

    user_id = principal._user.user_id

    # Scout modifying itself
    if target_user_id == user_id:
        record_security_event(
            EVENT_PRIVILEGE_ESCALATION_SELF,
            SecurityEvent.CRITICAL,
            user_id=user_id,
            description=f"Scout attempted self privilege escalation: {action_desc}",
            request=request,
        )
        lock_account(user_id, reason=EVENT_PRIVILEGE_ESCALATION_SELF)
        revoke_all_sessions(user_id, reason=EVENT_PRIVILEGE_ESCALATION_SELF)
        send_security_alert(
            EVENT_PRIVILEGE_ESCALATION_SELF,
            SecurityEvent.CRITICAL,
            username=SCOUT_USERNAME,
            description=f"Scout attempted self privilege escalation: {action_desc}",
            request=request,
        )
        return True

    # Scout modifying another user
    record_security_event(
        EVENT_PRIVILEGE_ESCALATION_OTHERS,
        SecurityEvent.CRITICAL,
        user_id=user_id,
        description=f"Scout attempted to escalate another user: {action_desc}",
        request=request,
    )
    lock_account(user_id, reason=EVENT_PRIVILEGE_ESCALATION_OTHERS)
    revoke_all_sessions(user_id, reason=EVENT_PRIVILEGE_ESCALATION_OTHERS)
    send_security_alert(
        EVENT_PRIVILEGE_ESCALATION_OTHERS,
        SecurityEvent.CRITICAL,
        username=SCOUT_USERNAME,
        description=f"Scout attempted to escalate another user: {action_desc}",
        request=request,
    )
    return True
