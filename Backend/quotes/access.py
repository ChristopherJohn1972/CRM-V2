import sqlalchemy as sa
from iam.models import AccessScope
from quotes.models import Quote


def can_access_quote(db, principal, quote):
    """Check if the principal can access the given quote based on scope."""
    if principal is None:
        return False

    scope = principal.effective_scope("quotes")

    if scope == AccessScope.ALL.value:
        return True

    if scope == AccessScope.TEAM.value:
        if principal.team_id and quote.assigned_team_id == principal.team_id:
            return True
        if principal.team_id and quote.owner_user_id == principal.user_id:
            return True

    if scope == AccessScope.ASSIGNED.value:
        if quote.assigned_user_id == principal.user_id:
            return True
        if quote.owner_user_id == principal.user_id:
            return True

    if scope == AccessScope.OWN.value:
        if quote.owner_user_id == principal.user_id:
            return True
        if quote.created_by == principal.user_id:
            return True

    return False


def scope_quote_queryset(db, principal, stmt):
    """Filter a quote query by the principal's effective scope."""
    if principal is None:
        return stmt.where(sa.false())

    # Always exclude soft-deleted quotes
    stmt = stmt.where(Quote.deleted_at.is_(None))

    scope = principal.effective_scope("quotes")

    if scope == AccessScope.ALL.value:
        return stmt

    if scope == AccessScope.TEAM.value:
        conditions = [Quote.assigned_team_id == principal.team_id]
        if principal.team_id:
            return stmt.where(sa.or_(*conditions))

    if scope == AccessScope.ASSIGNED.value:
        return stmt.where(
            sa.or_(
                Quote.assigned_user_id == principal.user_id,
                Quote.owner_user_id == principal.user_id,
            )
        )

    if scope == AccessScope.OWN.value:
        return stmt.where(
            sa.or_(
                Quote.owner_user_id == principal.user_id,
                Quote.created_by == principal.user_id,
            )
        )

    return stmt.where(sa.false())
