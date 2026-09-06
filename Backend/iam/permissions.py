import logging
from functools import lru_cache

import sqlalchemy as sa
from rest_framework.permissions import BasePermission

from common.exceptions import PermissionDeniedError
from iam.models import (
    AccessPolicy,
    Permission,
    Role,
    RolePermission,
    UserAccessPolicy,
    RoleAccessPolicy,
    UserPermission,
    UserRole,
    AccessScope,
)

logger = logging.getLogger(__name__)


class UserPrincipal:
    def __init__(self, session, user):
        self.session = session
        self.user = user
        self._allowed = None
        self._denied = None
        self._scope = None
        # Resolve permissions and scope eagerly so the caller can release the
        # SQLAlchemy session immediately after construction.
        self._load_permissions()
        self._load_scopes()

    @property
    def user_id(self):
        return self.user.user_id

    @property
    def username(self):
        return self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def department_id(self):
        return self.user.department_id

    @property
    def team_id(self):
        return self.user.team_id

    def display_name(self):
        return self.user.display_name()

    def _load_permissions(self):
        if self._allowed is not None:
            return
        perm = Permission.__table__
        up = UserPermission.__table__
        rp = RolePermission.__table__
        ur = UserRole.__table__

        user_perm_join = (
            sa.select(
                perm.c.code,
                up.c.effect,
            )
            .select_from(up.join(perm, up.c.permission_id == perm.c.permission_id))
            .where(up.c.user_id == self.user_id, perm.c.is_active == sa.true())
        )
        user_rows = self.session.execute(user_perm_join).fetchall()

        role_perm_join = (
            sa.select(perm.c.code)
            .select_from(ur.join(rp, ur.c.role_id == rp.c.role_id).join(perm, rp.c.permission_id == perm.c.permission_id))
            .where(ur.c.user_id == self.user_id, perm.c.is_active == sa.true())
        )
        role_codes = {row.code for row in self.session.execute(role_perm_join).fetchall()}

        allowed = set(role_codes)
        denied = set()
        for row in user_rows:
            if row.effect == "DENY":
                denied.add(row.code)
            else:
                allowed.add(row.code)
        self._allowed = allowed
        self._denied = denied

    def get_permissions(self):
        self._load_permissions()
        return sorted(self._allowed - self._denied)

    def get_role_codes(self):
        ur = UserRole.__table__
        role = Role.__table__
        rows = self.session.execute(
            sa.select(role.c.code)
            .select_from(ur.join(role, ur.c.role_id == role.c.role_id))
            .where(ur.c.user_id == self.user_id)
        ).fetchall()
        return sorted({row.code for row in rows})

    def has_permission(self, code):
        self._load_permissions()
        return code in self._allowed and code not in self._denied

    def _load_scopes(self):
        if self._scope is not None:
            return self._scope

        up = UserAccessPolicy.__table__
        rp = RoleAccessPolicy.__table__
        ap = AccessPolicy.__table__
        ur = UserRole.__table__

        role_scopes = (
            sa.select(ap.c.scope)
            .select_from(ur.join(rp, ur.c.role_id == rp.c.role_id).join(ap, rp.c.access_policy_id == ap.c.access_policy_id))
            .where(ur.c.user_id == self.user_id, ap.c.is_active == sa.true())
        )
        user_scopes = (
            sa.select(ap.c.scope)
            .select_from(up.join(ap, up.c.access_policy_id == ap.c.access_policy_id))
            .where(up.c.user_id == self.user_id, ap.c.is_active == sa.true())
        )
        scopes = {row.scope for row in self.session.execute(role_scopes).fetchall()}
        scopes.update(row.scope for row in self.session.execute(user_scopes).fetchall())

        ranking = {
            AccessScope.NONE.value: 0,
            AccessScope.OWN.value: 1,
            AccessScope.ASSIGNED.value: 2,
            AccessScope.TEAM.value: 3,
            AccessScope.DEPARTMENT.value: 4,
            AccessScope.ALL.value: 5,
        }
        self._scope = max(scopes, key=lambda s: ranking.get(s, 0)) if scopes else AccessScope.NONE.value
        return self._scope

    def effective_scope(self, resource):
        return self._load_scopes()


class IsAuthenticated(BasePermission):
    message = "Authentication credentials were not provided."

    def has_permission(self, request, view):
        principal = getattr(request, "user", None)
        return isinstance(principal, UserPrincipal)


class HasPermission(BasePermission):
    def __init__(self, permission_code):
        self.permission_code = permission_code

    def has_permission(self, request, view):
        principal = getattr(request, "user", None)
        if not isinstance(principal, UserPrincipal):
            return False
        return principal.has_permission(self.permission_code)


def require_permission(permission_code):
    def decorator(view_method):
        view_method.required_permission = permission_code
        return view_method

    return decorator


class PermissionRequiredMixin:
    required_permission = None

    def check_permissions(self, request):
        principal = getattr(request, "user", None)
        if not isinstance(principal, UserPrincipal):
            raise PermissionDeniedError("Authentication required.")
        if self.required_permission and not principal.has_permission(self.required_permission):
            raise PermissionDeniedError(
                f"Missing required permission: {self.required_permission}"
            )
