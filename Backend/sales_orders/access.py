import sqlalchemy as sa
from iam.models import AccessScope
from sales_orders.models import SalesOrder


def can_access_order(db, principal, order):
    """Check if the principal can access the given sales order based on scope."""
    if principal is None:
        return False

    scope = principal.effective_scope("sales_orders")

    if scope == AccessScope.ALL.value:
        return True

    if scope == AccessScope.TEAM.value:
        if principal.team_id and order.assigned_team_id == principal.team_id:
            return True
        if principal.team_id and order.owner_user_id == principal.user_id:
            return True

    if scope == AccessScope.ASSIGNED.value:
        if order.assigned_user_id == principal.user_id:
            return True
        if order.owner_user_id == principal.user_id:
            return True

    if scope == AccessScope.OWN.value:
        if order.owner_user_id == principal.user_id:
            return True
        if order.created_by == principal.user_id:
            return True

    return False


def scope_order_queryset(db, principal, stmt):
    """Filter a sales order query by the principal's effective scope."""
    if principal is None:
        return stmt.where(sa.false())

    scope = principal.effective_scope("sales_orders")

    if scope == AccessScope.ALL.value:
        return stmt

    if scope == AccessScope.TEAM.value:
        conditions = [SalesOrder.assigned_team_id == principal.team_id]
        if principal.team_id:
            return stmt.where(sa.or_(*conditions))

    if scope == AccessScope.ASSIGNED.value:
        return stmt.where(
            sa.or_(
                SalesOrder.assigned_user_id == principal.user_id,
                SalesOrder.owner_user_id == principal.user_id,
            )
        )

    if scope == AccessScope.OWN.value:
        return stmt.where(
            sa.or_(
                SalesOrder.owner_user_id == principal.user_id,
                SalesOrder.created_by == principal.user_id,
            )
        )

    return stmt.where(sa.false())
