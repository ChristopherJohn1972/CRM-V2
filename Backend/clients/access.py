import sqlalchemy as sa

from iam.models import AccessScope, TeamMember, User
from iam.permissions import UserPrincipal
from clients.models import Customer, Branch


def _team_ids_for_user(db, principal):
    stmt = sa.select(TeamMember.team_id).where(
        TeamMember.user_id == principal.user_id,
        TeamMember.is_active == sa.true(),
    )
    return {row for row in db.execute(stmt).scalars().all()}


def _owner_team_ids(db, principal):
    if principal.team_id:
        return {principal.team_id}
    return _team_ids_for_user(db, principal)


def can_access_customer(db, principal: UserPrincipal, customer: Customer) -> bool:
    if not isinstance(principal, UserPrincipal):
        return False
    if customer.deleted_at is not None:
        return False
    scope = principal.effective_scope("clients.customer")
    if scope == AccessScope.ALL.value:
        return True
    if scope == AccessScope.DEPARTMENT.value:
        owner = db.get(User, customer.assigned_user_id) if customer.assigned_user_id else None
        owner_department = owner.department_id if owner else None
        if owner_department and principal.department_id:
            return owner_department == principal.department_id
        if customer.branch_id:
            branch = db.get(Branch, customer.branch_id)
            if branch and branch.department_id and principal.department_id:
                return branch.department_id == principal.department_id
        return False
    if scope in (AccessScope.TEAM.value, AccessScope.ASSIGNED.value):
        my_teams = _owner_team_ids(db, principal)
        member_team_ids = _team_ids_for_user(db, principal)
        if customer.assigned_team_id and customer.assigned_team_id in my_teams | member_team_ids:
            return True
        if customer.assigned_user_id == principal.user_id:
            return True
        if customer.assigned_user_id:
            member_stmt = sa.select(TeamMember.team_id).where(
                TeamMember.user_id == customer.assigned_user_id,
                TeamMember.is_active == sa.true(),
            )
            owner_team_ids = {row for row in db.execute(member_stmt).scalars().all()}
            return bool(owner_team_ids & member_team_ids)
        return False
    if scope == AccessScope.OWN.value:
        return customer.assigned_user_id == principal.user_id
    return False


def get_customer_for_request(db, request, customer_id, permission=None):
    from common.exceptions import NotFoundError, PermissionDeniedError
    from iam.permissions import UserPrincipal

    principal = getattr(request, "user", None)
    if not isinstance(principal, UserPrincipal):
        raise PermissionDeniedError("Authentication required.")
    if permission and not principal.has_permission(permission):
        raise PermissionDeniedError(f"Missing required permission: {permission}")

    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found.")
    if not can_access_customer(db, principal, customer):
        raise PermissionDeniedError()
    return customer


def scope_queryset(db, principal: UserPrincipal, statement):
    if not isinstance(principal, UserPrincipal):
        return statement.where(sa.false())
    customer = Customer.__table__
    statement = statement.where(customer.c.deleted_at.is_(None))
    scope = principal.effective_scope("clients.customer")
    if scope == AccessScope.ALL.value:
        return statement
    if scope == AccessScope.DEPARTMENT.value:
        if principal.department_id is None:
            # No department in context -> no department records.
            return statement.where(sa.false())
        user = User.__table__
        owner_department = sa.select(user.c.department_id).where(
            user.c.user_id == customer.c.assigned_user_id
        ).scalar_subquery()
        branch = Branch.__table__
        branch_department = sa.select(branch.c.department_id).where(
            branch.c.branch_id == customer.c.branch_id
        ).scalar_subquery()
        cond = (owner_department == principal.department_id) | (
            branch_department == principal.department_id
        )
        return statement.where(cond)
    if scope in (AccessScope.TEAM.value, AccessScope.ASSIGNED.value):
        my_teams = _owner_team_ids(db, principal)
        member_team_ids = _team_ids_for_user(db, principal)
        team_ids = my_teams | member_team_ids
        member = TeamMember.__table__
        cond = sa.or_(
            customer.c.assigned_user_id == principal.user_id,
            customer.c.assigned_team_id.in_(list(team_ids)),
            sa.exists(
                sa.select(member.c.team_member_id).where(
                    member.c.user_id == customer.c.assigned_user_id,
                    member.c.is_active == sa.true(),
                    member.c.team_id.in_(list(team_ids)),
                )
            ),
        )
        return statement.where(cond)
    if scope == AccessScope.OWN.value:
        return statement.where(customer.c.assigned_user_id == principal.user_id)
    # NONE scope: no record reach.
    return statement.where(sa.false())