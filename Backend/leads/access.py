import sqlalchemy as sa

from iam.models import AccessScope
from leads.models import Lead


def can_access_lead(db, principal, lead):
    if principal is None:
        return False
    scope = principal.effective_scope("leads")
    if scope == AccessScope.ALL:
        return True
    if scope == AccessScope.TEAM:
        return (
            lead.assigned_team_id == principal.team_id
            or lead.assigned_user_id == principal.user_id
        )
    if scope == AccessScope.ASSIGNED:
        return lead.assigned_user_id == principal.user_id
    if scope == AccessScope.OWN:
        return lead.created_by == principal.user_id
    return False


def scope_lead_queryset(db, principal, stmt):
    if principal is None:
        return stmt.where(sa.false())
    scope = principal.effective_scope("leads")
    if scope == AccessScope.ALL:
        return stmt
    if scope == AccessScope.TEAM:
        return stmt.where(
            sa.or_(
                Lead.assigned_team_id == principal.team_id,
                Lead.assigned_user_id == principal.user_id,
            )
        )
    if scope == AccessScope.ASSIGNED:
        return stmt.where(Lead.assigned_user_id == principal.user_id)
    if scope == AccessScope.OWN:
        return stmt.where(Lead.created_by == principal.user_id)
    return stmt.where(sa.false())
