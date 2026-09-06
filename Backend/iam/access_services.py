"""Effective-access computation for internal operators.

Turns role grants + direct exceptions + scopes into a human-reviewable model:

    OPERATOR → ROLES → ROLE PERMISSIONS  (standard rights)
                         ↓
              + DIRECT EXCEPTIONS (user_permissions ALLOW/DENY, DENY wins)
                         ↓
              EFFECTIVE PERMISSION + SOURCE TRACING
                         ↓
              EFFECTIVE SCOPE (NONE < OWN < ASSIGNED < TEAM < DEPARTMENT < ALL)

The result of ``get_effective_access`` is the backend model that powers the
Operator / Roles / Rights / Access Review administration UI.
"""

from collections import defaultdict

import sqlalchemy as sa

from iam.models import (
    AccessPolicy,
    AccessScope,
    Permission,
    Role,
    RoleAccessPolicy,
    RolePermission,
    User,
    UserAccessPolicy,
    UserPermission,
    UserRole,
)

SCOPE_RANKING = {
    AccessScope.NONE.value: 0,
    AccessScope.OWN.value: 1,
    AccessScope.ASSIGNED.value: 2,
    AccessScope.TEAM.value: 3,
    AccessScope.DEPARTMENT.value: 4,
    AccessScope.ALL.value: 5,
}


def _scope_labels():
    return {
        AccessScope.NONE.value: "No records",
        AccessScope.OWN.value: "Records owned by the operator",
        AccessScope.ASSIGNED.value: "Records assigned to the operator",
        AccessScope.TEAM.value: "Records belonging to the operator's team",
        AccessScope.DEPARTMENT.value: "Records belonging to the operator's department",
        AccessScope.ALL.value: "All records permitted by the system",
    }


def _role_sources(session, user_id):
    """Map permission code -> set of role granting it."""
    role = Role.__table__
    rp = RolePermission.__table__
    ur = UserRole.__table__
    perm = Permission.__table__
    role_perm_rows = session.execute(
        sa.select(
            perm.c.code,
            role.c.role_id,
            role.c.code.label("role_code"),
            role.c.name.label("role_name"),
        )
        .select_from(
            ur.join(role, ur.c.role_id == role.c.role_id)
            .join(rp, ur.c.role_id == rp.c.role_id)
            .join(perm, rp.c.permission_id == perm.c.permission_id)
        )
        .where(
            ur.c.user_id == user_id,
            role.c.is_active == sa.true(),
            perm.c.is_active == sa.true(),
        )
    ).fetchall()

    by_code = defaultdict(list)
    for row in role_perm_rows:
        by_code[row.code].append(
            {
                "source": "role",
                "role_id": row.role_id,
                "role_code": row.role_code,
                "role_name": row.role_name,
                "effect": "ALLOW",
            }
        )
    return dict(by_code)


def _direct_rows(session, user_id):
    """Map permission code -> list of direct user_permissions rows."""
    perm = Permission.__table__
    up = UserPermission.__table__
    rows = session.execute(
        sa.select(perm.c.code, up.c.effect, up.c.reason)
        .select_from(up.join(perm, up.c.permission_id == perm.c.permission_id))
        .where(up.c.user_id == user_id, perm.c.is_active == sa.true())
    ).fetchall()

    by_code = defaultdict(list)
    for row in rows:
        by_code[row.code].append(
            {
                "source": "direct",
                "effect": row.effect,
                "reason": row.reason,
            }
        )
    return dict(by_code)


def _catalogue(session):
    rows = session.execute(
        sa.select(
            Permission.permission_id,
            Permission.code,
            Permission.name,
            Permission.resource,
            Permission.action,
            Permission.description,
            Permission.is_active,
        )
        .where(Permission.is_active == sa.true())
        .order_by(Permission.resource, Permission.action)
    ).all()
    return rows


def effective_access(session, user_id):
    """Compute the full access review for an internal operator.

    Returns a dict with operator summary, roles, effective permissions (each
    permission with its sources and the winning effect) and effective scope.
    """
    user = session.get(User, user_id)
    if user is None:
        return None

    ur = UserRole.__table__
    role = Role.__table__
    role_list = session.execute(
        sa.select(Role)
        .select_from(ur.join(role, ur.c.role_id == role.c.role_id))
        .where(ur.c.user_id == user_id)
        .order_by(role.c.code)
    ).scalars().all()

    role_sources = _role_sources(session, user_id)
    direct_rows = _direct_rows(session, user_id)

    permissions = []
    for row in _catalogue(session):
        sources = list(role_sources.get(row.code, [])) + list(direct_rows.get(row.code, []))
        if not sources:
            effective = "NONE"
        else:
            has_deny = any(s.get("effect") == "DENY" for s in sources)
            effective = "DENY" if has_deny else "ALLOW"
        permissions.append(
            {
                "permission_id": row.permission_id,
                "code": row.code,
                "name": row.name,
                "resource": row.resource,
                "action": row.action,
                "description": row.description,
                "effective": effective,
                "sources": sources,
            }
        )

    # Group by resource for the "RIGHTS" panel.
    by_resource = defaultdict(list)
    for p in permissions:
        by_resource[p["resource"]].append(p)

    scope_codes, scope = effective_scope(session, user_id)

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "department_id": user.department_id,
        "team_id": user.team_id,
        "status": user.status,
        "roles": [
            {
                "role_id": r.role_id,
                "code": r.code,
                "name": r.name,
                "is_system_role": bool(r.is_system_role),
            }
            for r in role_list
        ],
        "permissions": permissions,
        "rights_by_resource": {k: v for k, v in sorted(by_resource.items())},
        "scope": {
            "effective": scope,
            "meaning": _scope_labels().get(scope, scope),
            "policies": sorted(scope_codes),
        },
    }


def effective_scope(session, user_id):
    """Return (policy_codes, scope_name) merging role + direct policies.

    DENY/policies follow the ACCESS hierarchy
    NONE < OWN < ASSIGNED < TEAM < DEPARTMENT < ALL; the strongest applied
    policy wins, mirroring iam/permissions.UserPrincipal.
    """
    role = Role.__table__
    rap = RoleAccessPolicy.__table__
    ur = UserRole.__table__
    ap = AccessPolicy.__table__
    uap = UserAccessPolicy.__table__

    role_policies = set(
        session.execute(
            sa.select(ap.c.code, ap.c.scope)
            .select_from(ur.join(rap, ur.c.role_id == rap.c.role_id).join(ap, rap.c.access_policy_id == ap.c.access_policy_id))
            .where(ur.c.user_id == user_id, ap.c.is_active == sa.true())
        ).fetchall()
    )
    user_policies = set(
        session.execute(
            sa.select(ap.c.code, ap.c.scope)
            .select_from(uap.join(ap, uap.c.access_policy_id == ap.c.access_policy_id))
            .where(uap.c.user_id == user_id, ap.c.is_active == sa.true())
        ).fetchall()
    )
    codes = {code for code, _scope in role_policies | user_policies}
    scopes = {scope for _code, scope in role_policies | user_policies}
    if not scopes:
        return codes, AccessScope.NONE.value
    strongest = max(scopes, key=lambda s: SCOPE_RANKING.get(s, 0))
    return codes, strongest


def rights_preview_for_roles(session, role_ids):
    """The standard rights block that a set of roles provides (no direct rows)."""
    if not role_ids:
        return []
    role = Role.__table__
    rp = RolePermission.__table__
    perm = Permission.__table__
    rows = session.execute(
        sa.select(perm.c.code, perm.c.name, perm.c.resource, perm.c.action)
        .select_from(role.join(rp, role.c.role_id == rp.c.role_id).join(perm, rp.c.permission_id == perm.c.permission_id))
        .where(role.c.role_id.in_(role_ids), role.c.is_active == sa.true(), perm.c.is_active == sa.true())
        .order_by(perm.c.resource, perm.c.action)
    ).all()
    return [
        {
            "code": r.code,
            "name": r.name,
            "resource": r.resource,
            "action": r.action,
        }
        for r in rows
    ]


def rights_catalogue(session):
    perms = _catalogue(session)
    return [
        {
            "permission_id": p.permission_id,
            "code": p.code,
            "name": p.name,
            "resource": p.resource,
            "action": p.action,
            "description": p.description,
            "is_active": bool(p.is_active),
        }
        for p in perms
    ]