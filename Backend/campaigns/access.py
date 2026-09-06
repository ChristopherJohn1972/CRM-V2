import sqlalchemy as sa

from iam.models import AccessScope
from campaigns.models import Campaign


def can_access_campaign(db, principal, campaign):
    if principal is None:
        return False
    scope = principal.effective_scope("campaigns")
    if scope == AccessScope.ALL:
        return True
    if scope == AccessScope.TEAM:
        return (
            campaign.owner_user_id == principal.user_id
        )
    if scope == AccessScope.ASSIGNED:
        return (
            campaign.owner_user_id == principal.user_id
            or campaign.created_by == principal.user_id
        )
    if scope == AccessScope.OWN:
        return (
            campaign.owner_user_id == principal.user_id
            or campaign.created_by == principal.user_id
        )
    return False


def scope_campaign_queryset(db, principal, stmt):
    if principal is None:
        return stmt.where(sa.false())
    scope = principal.effective_scope("campaigns")
    if scope == AccessScope.ALL:
        return stmt
    if scope == AccessScope.TEAM:
        return stmt.where(Campaign.owner_user_id == principal.user_id)
    if scope == AccessScope.ASSIGNED:
        return stmt.where(
            sa.or_(
                Campaign.owner_user_id == principal.user_id,
                Campaign.created_by == principal.user_id,
            )
        )
    if scope == AccessScope.OWN:
        return stmt.where(
            sa.or_(
                Campaign.owner_user_id == principal.user_id,
                Campaign.created_by == principal.user_id,
            )
        )
    return stmt.where(sa.false())
