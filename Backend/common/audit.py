import logging

from common import context

logger = logging.getLogger(__name__)


def record_audit(
    session,
    *,
    actor_user_id=None,
    actor_portal_user_id=None,
    action,
    resource_type=None,
    resource_id=None,
    description=None,
    metadata=None,
    actor_type="INTERNAL_USER",
    request=None,
):
    ctx = context.get_request_context(request) if request is not None else {}
    from iam.models import AuditLog

    entry = AuditLog(
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        actor_portal_user_id=actor_portal_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent"),
        metadata_={"correlation_id": ctx.get("correlation_id"), **(metadata or {})},
    )
    session.add(entry)
    return entry


def audit_login(session, *, user_id, action, description, request=None):
    record_audit(
        session,
        actor_user_id=user_id,
        action=action,
        resource_type="users",
        resource_id=user_id,
        description=description,
        request=request,
    )
