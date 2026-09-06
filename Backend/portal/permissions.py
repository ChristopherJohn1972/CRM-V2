import logging

import sqlalchemy as sa
from rest_framework.permissions import BasePermission

from portal.enums import PORTAL_RELATIONSHIP_RANK
from portal.models import CustomerAccount, PortalPermission, PortalUser, PortalUserCustomer, PortalUserPermission

logger = logging.getLogger(__name__)


class PortalPrincipal:
    """Eagerly-resolved portal identity.

    Holds the portal permissions (ALLOW wins over DENY), the set of customer
    accounts the portal user is explicitly and actively linked to, and the role
    rank per customer account. Everything is loaded up-front so the SQLAlchemy
    session can be released immediately after construction (mirrors UserPrincipal).
    """

    kind = "portal"

    def __init__(self, session, portal_user: PortalUser):
        self.portal_user = portal_user
        self._allowed = set()
        self._denied = set()
        self._customer_account_ids = set()
        self._roles = {}
        self._load_permissions(session)
        self._load_customer_accounts(session)

    @property
    def portal_user_id(self):
        return self.portal_user.portal_user_id

    @property
    def email(self):
        return self.portal_user.email

    @property
    def customer_account_ids(self):
        return set(self._customer_account_ids)

    @property
    def must_change_password(self):
        return getattr(self.portal_user, "_must_change_password", False)

    def display_name(self):
        return f"{self.portal_user.first_name} {self.portal_user.last_name}".strip()

    def _load_permissions(self, session):
        perm = PortalPermission.__table__
        up = PortalUserPermission.__table__
        rows = session.execute(
            sa.select(perm.c.code, up.c.effect)
            .select_from(up.join(perm, up.c.portal_permission_id == perm.c.portal_permission_id))
            .where(up.c.portal_user_id == self.portal_user_id, perm.c.is_active == sa.true())
        ).fetchall()
        for code, effect in rows:
            if effect == "DENY":
                self._denied.add(code)
            else:
                self._allowed.add(code)

    def _load_customer_accounts(self, session):
        rows = session.execute(
            sa.select(
                PortalUserCustomer.customer_account_id,
                PortalUserCustomer.role,
            ).where(
                PortalUserCustomer.portal_user_id == self.portal_user_id,
                PortalUserCustomer.is_active == sa.true(),
            )
        ).fetchall()
        for customer_account_id, role in rows:
            self._customer_account_ids.add(customer_account_id)
            self._roles[customer_account_id] = role

    def has_permission(self, code):
        return code in self._allowed and code not in self._denied

    def get_permissions(self):
        return sorted(self._allowed - self._denied)

    def role(self, customer_account_id):
        return self._roles.get(customer_account_id)

    def relationship_rank(self, customer_account_id):
        role = self._roles.get(customer_account_id)
        if role is None:
            return 0
        return PORTAL_RELATIONSHIP_RANK.get(role, 0)

    def can_access_customer_account(self, customer_account_id):
        return customer_account_id in self._customer_account_ids


class IsPortalAuthenticated(BasePermission):
    message = "Portal authentication credentials were not provided."

    def has_permission(self, request, view):
        principal = getattr(request, "user", None)
        return isinstance(principal, PortalPrincipal)


class HasPortalPermission(BasePermission):
    def __init__(self, permission_code):
        self.permission_code = permission_code

    def has_permission(self, request, view):
        principal = getattr(request, "user", None)
        if not isinstance(principal, PortalPrincipal):
            return False
        return principal.has_permission(self.permission_code)