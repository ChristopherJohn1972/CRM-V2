import logging

import sqlalchemy as sa
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.models import Customer
from common import audit
from common.db import SessionLocal
from common.exceptions import APIError, NotFoundError, PermissionDeniedError
from portal.authentication import PortalJWTBearerAuthentication
from portal.models import (
    Complaint,
    CustomerAccount,
    Notification,
    Payment,
    PaymentReceipt,
    PortalPermission,
    PortalUser,
    PortalUserCustomer,
    PortalUserPermission,
    Reward,
    RewardRedemption,
)
from portal.permissions import IsPortalAuthenticated, PortalPrincipal
from portal.serializers import (
    PortalChangePasswordSerializer,
    PortalComplaintCreateSerializer,
    PortalComplaintMessageCreateSerializer,
    PortalComplaintReadSerializer,
    PortalComplaintTimelineEntrySerializer,
    PortalCustomerAccessReadSerializer,
    PortalCustomerAccessUpdateSerializer,
    PortalCustomerAccessWriteSerializer,
    PortalDashboardSerializer,
    PortalForgotPasswordSerializer,
    PortalLoginRequestSerializer,
    PortalLoginResponseSerializer,
    PortalMeSerializer,
    PortalMomentumSummarySerializer,
    PortalNotificationListResponseSerializer,
    PortalNotificationReadSerializer,
    PortalPaymentFilterSerializer,
    PortalPaymentListResponseSerializer,
    PortalPaymentReadSerializer,
    PortalPermissionAssignSerializer,
    PortalPermissionReadSerializer,
    PortalResetPasswordSerializer,
    PortalRewardReadSerializer,
    PortalRewardRedemptionReadSerializer,
    PortalSetupPasswordSerializer,
    PortalUserReadSerializer,
    PortalUserStatusSerializer,
    PortalUserWriteSerializer,
)
from portal.services import (
    ComplaintService,
    MomentumService,
    NotificationService,
    PortalAuthenticationService,
    PortalAuthorizationService,
    PortalCustomerAccessService,
    PortalPermissionService,
    PortalSessionService,
    PortalUserService,
    RewardService,
    decode_portal_access_token,
    issue_portal_access_token,
)

logger = logging.getLogger(__name__)

PERMISSION_PORTAL_CUSTOMER_VIEW = "portal.customer.view"


def _enum_value(value):
    """Render an SQLAlchemy enum member as its plain value for the API."""
    import enum as _enum

    return value.value if isinstance(value, _enum.Enum) else value


def _portal_principal(request) -> PortalPrincipal:
    return getattr(request, "user", None)


def _resolve_customer_account(db, customer_account_id, principal):
    """Resolve a customer_account_id to the underlying customer_id.

    Returns (customer_account, customer_id) or raises NotFoundError.
    """
    customer_account = db.get(CustomerAccount, int(customer_account_id))
    if customer_account is None:
        raise NotFoundError("Customer account not found.")
    if customer_account.customer_account_id not in principal.customer_account_ids:
        raise PermissionDeniedError("Access denied to this customer account.")
    return customer_account, customer_account.customer_id


def _require_portal_permission(principal, code, customer_account_id=None, min_relationship=None, db=None, request=None):
    if principal is None or not isinstance(principal, PortalPrincipal):
        raise PermissionDeniedError("Portal authentication required.")
    if principal.must_change_password:
        raise PermissionDeniedError("Password change required before accessing portal data.")
    PortalAuthorizationService.authorize_or_deny(
        db, principal, code, customer_account_id=customer_account_id, min_relationship=min_relationship, request=request
    )


class PortalLoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        serializer = PortalLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            email = serializer.validated_data["email"]
            account_number = serializer.validated_data["account_number"]
            password = serializer.validated_data["password"]
            logger.warning(f"Portal login attempt: email={email}, account={account_number}")
            portal_user, customer_account, must_change_password = PortalAuthenticationService.login(
                db, email, account_number, password,
            )
            portal_session, _token = PortalSessionService.create_session(
                db,
                portal_user.portal_user_id,
                request.META.get("REMOTE_ADDR"),
                request.META.get("HTTP_USER_AGENT", ""),
            )
            token = issue_portal_access_token(
                portal_user.portal_user_id, portal_session.portal_session_id
            )
            audit.record_audit(
                db,
                actor_portal_user_id=portal_user.portal_user_id,
                actor_type="PORTAL_USER",
                action="portal.login.success",
                resource_type="portal_users",
                resource_id=portal_user.portal_user_id,
                description=f"Portal user {portal_user.email} logged in to account {customer_account.account_number}",
                request=request,
            )
            db.commit()
            data = PortalLoginResponseSerializer(
                {
                    "token": token,
                    "token_type": "Bearer",
                    "expires_in": settings.JWT_ACCESS_TTL_MINUTES * 60,
                    "must_change_password": must_change_password,
                    "portal_user": {
                        "portal_user_id": portal_user.portal_user_id,
                        "email": portal_user.email,
                        "first_name": portal_user.first_name,
                        "last_name": portal_user.last_name,
                        "status": _enum_value(portal_user.status),
                        "account_number": customer_account.account_number,
                        "customer_account_id": customer_account.customer_account_id,
                    },
                }
            ).data
            return Response(data, status=status.HTTP_200_OK)
        finally:
            db.close()


class PortalLogoutView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request):
        principal = _portal_principal(request)
        payload = getattr(request, "auth", None)
        db = SessionLocal()
        try:
            if payload:
                token_payload = decode_portal_access_token(payload)
                PortalSessionService.revoke(db, int(token_payload["sid"]))
                audit.record_audit(
                    db,
                    actor_portal_user_id=principal.portal_user_id if principal else None,
                    actor_type="PORTAL_USER",
                    action="portal.logout",
                    resource_type="portal_users",
                    resource_id=principal.portal_user_id if principal else None,
                    description="Portal user logged out",
                    request=request,
                )
                db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class PortalChangePasswordView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request):
        principal = _portal_principal(request)
        serializer = PortalChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            PortalAuthenticationService.change_password(
                db,
                principal.portal_user_id,
                serializer.validated_data["current_password"],
                serializer.validated_data["new_password"],
            )
            audit.record_audit(
                db,
                actor_portal_user_id=principal.portal_user_id,
                actor_type="PORTAL_USER",
                action="portal.password.changed",
                resource_type="portal_users",
                resource_id=principal.portal_user_id,
                description="Portal user changed their password",
                request=request,
            )
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class PortalSetupPasswordView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request):
        principal = _portal_principal(request)
        serializer = PortalSetupPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            PortalAuthenticationService.setup_password(
                db,
                principal.portal_user_id,
                serializer.validated_data["password"],
            )
            audit.record_audit(
                db,
                actor_portal_user_id=principal.portal_user_id,
                actor_type="PORTAL_USER",
                action="portal.password.setup",
                resource_type="portal_users",
                resource_id=principal.portal_user_id,
                description="Portal user set initial password",
                request=request,
            )
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class PortalForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        serializer = PortalForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            portal_user, _ = PortalAuthenticationService.find_by_login(
                db,
                serializer.validated_data["email"],
                serializer.validated_data["account_number"],
            )
            from portal.enums import PortalUserStatus

            if portal_user is not None and portal_user.status != PortalUserStatus.DEACTIVATED.value:
                reset_token = PortalAuthenticationService.create_reset_token(
                    db, portal_user.portal_user_id
                )
            else:
                reset_token = None
            audit.record_audit(
                db,
                actor_type="SYSTEM",
                action="portal.password.reset_requested",
                resource_type="portal_users",
                resource_id=portal_user.portal_user_id if portal_user else None,
                description=f"Password reset requested for {serializer.validated_data['email']}",
                request=request,
            )
            db.commit()
            data = {
                "detail": "If an account exists for that login, a reset token has been delivered out-of-band."
            }
            # Development/reset-token delivery behind a dev-only flag; production
            # delivers the token through the email/SMS provider instead.
            if reset_token and settings.DEBUG:
                data["debug_reset_token"] = reset_token
            return Response(data, status=status.HTTP_200_OK)
        finally:
            db.close()


class PortalResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        serializer = PortalResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            portal_user = PortalAuthenticationService.reset_password(
                db,
                serializer.validated_data["token"],
                serializer.validated_data["new_password"],
            )
            audit.record_audit(
                db,
                actor_portal_user_id=portal_user.portal_user_id,
                actor_type="PORTAL_USER",
                action="portal.password.reset",
                resource_type="portal_users",
                resource_id=portal_user.portal_user_id,
                description=f"Portal user {portal_user.email} reset their password",
                request=request,
            )
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class PortalMeView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        principal = _portal_principal(request)
        data = PortalMeSerializer(
            {
                "portal_user_id": principal.portal_user_id,
                "email": principal.email,
                "first_name": principal.portal_user.first_name,
                "last_name": principal.portal_user.last_name,
                "phone": principal.portal_user.phone,
                "permissions": principal.get_permissions(),
                "customer_account_ids": sorted(principal.customer_account_ids),
                "must_change_password": principal.must_change_password,
            }
        ).data
        return Response(data)


class PortalCustomerListView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(principal, PERMISSION_PORTAL_CUSTOMER_VIEW, db=db, request=request)
            customer_account_ids = principal.customer_account_ids
            if not customer_account_ids:
                return Response({"customer_account_ids": [], "results": []})

            accounts = db.execute(
                sa.select(CustomerAccount).where(
                    CustomerAccount.customer_account_id.in_(customer_account_ids),
                )
            ).scalars().all()

            customer_ids = [a.customer_id for a in accounts]
            customers = db.execute(
                sa.select(Customer).where(
                    Customer.customer_id.in_(customer_ids),
                    Customer.deleted_at.is_(None),
                )
            ).scalars().all()
            customer_map = {c.customer_id: c for c in customers}

            links = db.execute(
                sa.select(PortalUserCustomer).where(
                    PortalUserCustomer.portal_user_id == principal.portal_user_id,
                    PortalUserCustomer.is_active == sa.true(),
                )
            ).scalars().all()
            link_map = {l.customer_account_id: l for l in links}

            results = []
            for a in accounts:
                customer = customer_map.get(a.customer_id)
                link = link_map.get(a.customer_account_id)
                results.append({
                    "customer_account_id": a.customer_account_id,
                    "account_number": a.account_number,
                    "customer_id": a.customer_id,
                    "customer_number": customer.customer_number if customer else None,
                    "display_name": customer.get_display_name() if customer else None,
                    "status": _enum_value(a.status),
                    "role": _enum_value(link.role) if link else None,
                    "is_primary": bool(link.is_primary) if link else False,
                })
            return Response({"customer_account_ids": sorted(customer_account_ids), "results": results})
        finally:
            db.close()


class PortalCustomerDetailView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, PERMISSION_PORTAL_CUSTOMER_VIEW, customer_account_id=int(customer_account_id), db=db, request=request
            )
            customer_account, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            customer = db.get(Customer, customer_id)
            if customer is None or customer.deleted_at is not None:
                raise NotFoundError("Customer not found.")
            link = db.execute(
                sa.select(PortalUserCustomer).where(
                    PortalUserCustomer.portal_user_id == principal.portal_user_id,
                    PortalUserCustomer.customer_account_id == int(customer_account_id),
                )
            ).scalar_one_or_none()
            data = {
                "customer_account_id": customer_account.customer_account_id,
                "account_number": customer_account.account_number,
                "customer_id": customer.customer_id,
                "customer_number": customer.customer_number,
                "status": _enum_value(customer_account.status),
                "customer_type": _enum_value(customer.customer_type),
                "display_name": customer.get_display_name(),
                "email": customer.email,
                "phone": customer.phone,
                "industry": customer.industry,
                "role": _enum_value(link.role) if link else None,
                "is_primary": bool(link.is_primary) if link else False,
            }
            return Response(data)
        finally:
            db.close()


class PortalUserListView(APIView):
    def post(self, request):
        principal = _portal_principal_for_internal(request)
        serializer = PortalUserWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            send_temp = serializer.validated_data.pop("send_temp_password", False)
            portal_user, temp_password = PortalUserService.create(db, **serializer.validated_data)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="portal.user.created",
                resource_type="portal_users",
                resource_id=portal_user.portal_user_id,
                description=f"Portal user {portal_user.email} created",
                request=request,
            )
            db.commit()
            db.refresh(portal_user)
            data = PortalUserReadSerializer(
                {
                    "portal_user_id": portal_user.portal_user_id,
                    "email": portal_user.email,
                    "first_name": portal_user.first_name,
                    "last_name": portal_user.last_name,
                    "phone": portal_user.phone,
                    "status": portal_user.status,
                    "email_verified_at": portal_user.email_verified_at,
                    "last_login_at": portal_user.last_login_at,
                }
            ).data
            if send_temp or settings.DEBUG:
                data["temp_password"] = temp_password
            return Response(data, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class PortalUserDetailView(APIView):
    def get(self, request, portal_user_id):
        _portal_principal_for_internal(request)
        db = SessionLocal()
        try:
            portal_user = _get_portal_user(db, portal_user_id)
            return Response(_serialize_portal_user(portal_user))
        finally:
            db.close()


class PortalUserStatusView(APIView):
    def patch(self, request, portal_user_id):
        serializer = PortalUserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            principal = _portal_principal_for_internal(request)
            portal_user = _get_portal_user(db, portal_user_id)
            PortalUserService.set_status(db, portal_user, serializer.validated_data["status"])
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="portal.user.status_changed",
                resource_type="portal_users",
                resource_id=portal_user.portal_user_id,
                description=f"Portal user {portal_user.email} status -> {serializer.validated_data['status']}",
                request=request,
            )
            db.commit()
            return Response(_serialize_portal_user(portal_user))
        finally:
            db.close()


class PortalUserPasswordView(APIView):
    """Re-issue temporary onboarding credentials (admin action)."""

    def post(self, request, portal_user_id):
        db = SessionLocal()
        try:
            principal = _portal_principal_for_internal(request)
            portal_user = _get_portal_user(db, portal_user_id)
            temp = PortalAuthenticationService.issue_temp_credential(db, portal_user)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="portal.user.password_reissued",
                resource_type="portal_users",
                resource_id=portal_user.portal_user_id,
                description=f"Temporary password re-issued for portal user {portal_user.email}",
                request=request,
            )
            db.commit()
            data = {"detail": "Temporary password issued.", "temp_password": temp}
            return Response(data)
        finally:
            db.close()


class PortalUserCustomerListView(APIView):
    def get(self, request, portal_user_id):
        _portal_principal_for_internal(request)
        db = SessionLocal()
        try:
            _get_portal_user(db, portal_user_id)
            return Response(_serialize_portal_user_customers(db, portal_user_id))
        finally:
            db.close()

    def post(self, request, portal_user_id):
        serializer = PortalCustomerAccessWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            principal = _portal_principal_for_internal(request)
            _get_portal_user(db, portal_user_id)
            customer_account = db.get(CustomerAccount, serializer.validated_data["customer_account_id"])
            if customer_account is None:
                raise NotFoundError("Customer account not found.")
            link = PortalCustomerAccessService.link(
                db,
                portal_user_id,
                serializer.validated_data["customer_account_id"],
                role=serializer.validated_data.get("role", "CONTACT"),
                is_primary=serializer.validated_data.get("is_primary", False),
                is_active=serializer.validated_data.get("is_active", True),
            )
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="portal.user.customer_linked",
                resource_type="portal_user_customers",
                resource_id=link.portal_user_customer_id,
                description=f"Portal user {portal_user_id} linked to customer account {serializer.validated_data['customer_account_id']}",
                request=request,
            )
            db.commit()
            db.refresh(link)
            return Response(_serialize_portal_user_customers(db, portal_user_id))
        finally:
            db.close()


class PortalUserCustomerLinkView(APIView):
    def delete(self, request, portal_user_id, link_id):
        db = SessionLocal()
        try:
            principal = _portal_principal_for_internal(request)
            link = db.get(PortalUserCustomer, int(link_id))
            if link is None or link.portal_user_id != int(portal_user_id):
                raise NotFoundError("Portal customer link not found.")
            PortalCustomerAccessService.deactivate(db, portal_user_id, link.customer_account_id)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="portal.user.customer_unlinked",
                resource_type="portal_user_customers",
                resource_id=link.portal_user_customer_id,
                description=f"Removed customer account {link.customer_account_id} from portal user {portal_user_id}",
                request=request,
            )
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class PortalPermissionListView(APIView):
    """Catalog + effective portal permissions for a portal user."""

    def get(self, request, portal_user_id):
        _portal_principal_for_internal(request)
        db = SessionLocal()
        try:
            _get_portal_user(db, portal_user_id)
            perm = PortalPermission.__table__
            up = PortalUserPermission.__table__
            rows = db.execute(
                sa.select(perm.c.code, perm.c.name, perm.c.resource, perm.c.action, up.c.effect)
                .select_from(perm.outerjoin(up, (up.c.portal_permission_id == perm.c.portal_permission_id) & (
                    up.c.portal_user_id == portal_user_id)))
                .where(perm.c.is_active == sa.true())
                .order_by(perm.c.code)
            ).fetchall()
            data = [
                {
                    "code": r.code,
                    "name": r.name,
                    "resource": r.resource,
                    "action": r.action,
                    "effect": r.effect,
                }
                for r in rows
            ]
            return Response({"permissions": data})
        finally:
            db.close()

    def post(self, request, portal_user_id):
        serializer = PortalPermissionAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            principal = _portal_principal_for_internal(request)
            _get_portal_user(db, portal_user_id)
            row = PortalPermissionService.grant(
                db,
                portal_user_id,
                serializer.validated_data["permission_code"],
                effect=serializer.validated_data.get("effect", "ALLOW"),
            )
            permission = db.get(PortalPermission, row.portal_permission_id)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="portal.user.permission_granted",
                resource_type="portal_user_permissions",
                resource_id=row.portal_user_permission_id,
                description=f"Portal permission {permission.code} {row.effect} for user {portal_user_id}",
                request=request,
            )
            db.commit()
            return Response({"detail": f"{permission.code} {row.effect}"})
        finally:
            db.close()


class PortalPermissionDetailView(APIView):
    def delete(self, request, portal_user_id, permission_code):
        db = SessionLocal()
        try:
            principal = _portal_principal_for_internal(request)
            _get_portal_user(db, portal_user_id)
            PortalPermissionService.revoke(db, portal_user_id, permission_code)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="portal.user.permission_revoked",
                resource_type="portal_user_permissions",
                description=f"Portal permission {permission_code} revoked for user {portal_user_id}",
                request=request,
            )
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


def _portal_principal_for_internal(request):
    from iam.permissions import UserPrincipal

    principal = getattr(request, "user", None)
    if not isinstance(principal, UserPrincipal):
        raise PermissionDeniedError("Internal user authentication required.")
    if not principal.has_permission("iam.user.manage"):
        raise PermissionDeniedError("Missing required permission: iam.user.manage")
    return principal


def _get_portal_user(db, portal_user_id):
    portal_user = db.get(PortalUser, int(portal_user_id))
    if portal_user is None:
        raise NotFoundError("Portal user not found.")
    return portal_user


def _serialize_portal_user(portal_user):
    return PortalUserReadSerializer(
        {
            "portal_user_id": portal_user.portal_user_id,
            "email": portal_user.email,
            "first_name": portal_user.first_name,
            "last_name": portal_user.last_name,
            "phone": portal_user.phone,
            "status": portal_user.status,
            "email_verified_at": portal_user.email_verified_at,
            "last_login_at": portal_user.last_login_at,
        }
    ).data


def _serialize_portal_user_customers(db, portal_user_id, link_id=None):
    rows = db.execute(
        sa.select(PortalUserCustomer, CustomerAccount, Customer)
        .outerjoin(CustomerAccount, PortalUserCustomer.customer_account_id == CustomerAccount.customer_account_id)
        .outerjoin(Customer, CustomerAccount.customer_id == Customer.customer_id)
        .where(PortalUserCustomer.portal_user_id == int(portal_user_id))
        .order_by(sa.desc(PortalUserCustomer.portal_user_customer_id))
    ).all()
    results = []
    for link, account, customer in rows:
        results.append(
            {
                "portal_user_customer_id": link.portal_user_customer_id,
                "portal_user_id": link.portal_user_id,
                "customer_account_id": link.customer_account_id,
                "account_number": account.account_number if account else None,
                "customer_id": account.customer_id if account else None,
                "customer_number": customer.customer_number if customer else None,
                "customer_name": customer.get_display_name() if customer else None,
                "role": _enum_value(link.role),
                "is_primary": bool(link.is_primary),
                "is_active": bool(link.is_active),
            }
        )
    return {"results": results}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class PortalDashboardView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(principal, "portal.customer.view", db=db, request=request)
            customer_account_ids = principal.customer_account_ids
            if not customer_account_ids:
                return Response({
                    "accounts": [],
                    "total_momentum": 0,
                    "total_notifications": 0,
                })

            accounts = db.execute(
                sa.select(CustomerAccount).where(
                    CustomerAccount.customer_account_id.in_(customer_account_ids),
                )
            ).scalars().all()

            results = []
            total_momentum = 0
            for a in accounts:
                customer = db.get(Customer, a.customer_id)
                if customer is None or customer.deleted_at is not None:
                    continue

                summary = MomentumService.get_summary(db, a.customer_id)
                payments_count = db.execute(
                    sa.select(sa.func.count(Payment.payment_id)).where(
                        Payment.customer_id == a.customer_id,
                        Payment.status == "CONFIRMED",
                    )
                ).scalar()
                open_complaints = ComplaintService.count_open_for_customer(db, a.customer_id)

                results.append({
                    "customer_account_id": a.customer_account_id,
                    "account_number": a.account_number,
                    "customer_id": a.customer_id,
                    "customer_number": customer.customer_number,
                    "display_name": customer.get_display_name(),
                    "account_status": _enum_value(a.status),
                    "momentum": summary["momentum"],
                    "momentum_remainder": summary["remainder"],
                    "next_momentum_required": summary["next_momentum_required"],
                    "payments_count": int(payments_count),
                    "open_complaints": open_complaints,
                })
                total_momentum += summary["momentum"]

            unread = NotificationService.count_unread(db, principal.portal_user_id)

            return Response({
                "accounts": results,
                "total_momentum": total_momentum,
                "unread_notifications": unread,
            })
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class PortalPaymentListView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.payment.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            serializer = PortalPaymentFilterSerializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            conditions = [
                Payment.customer_id == customer_id,
            ]
            if data.get("status"):
                conditions.append(Payment.status == data["status"])
            if data.get("date_from"):
                conditions.append(Payment.payment_date >= data["date_from"])
            if data.get("date_to"):
                conditions.append(Payment.payment_date <= data["date_to"])

            page = data.get("page", 1)
            page_size = data.get("page_size", 20)
            offset = (page - 1) * page_size

            total = db.execute(
                sa.select(sa.func.count(Payment.payment_id)).where(sa.and_(*conditions))
            ).scalar()

            payments = db.execute(
                sa.select(Payment)
                .where(sa.and_(*conditions))
                .order_by(sa.desc(Payment.payment_date))
                .limit(page_size)
                .offset(offset)
            ).scalars().all()

            results = []
            for p in payments:
                has_receipt = db.execute(
                    sa.select(sa.func.count(PaymentReceipt.receipt_id)).where(
                        PaymentReceipt.payment_id == p.payment_id
                    )
                ).scalar() > 0
                results.append({
                    "payment_id": p.payment_id,
                    "amount": float(p.amount),
                    "payment_date": p.payment_date.isoformat(),
                    "reference": p.reference,
                    "payment_method": p.payment_method,
                    "status": _enum_value(p.status),
                    "description": p.description,
                    "has_receipt": has_receipt,
                })

            momentum_data = MomentumService.get_payment_summary(
                db, customer_id, data.get("date_from"), data.get("date_to")
            )
            total_amount = sum(float(p.amount) for p in payments)

            return Response({
                "results": results,
                "total_qualifying": momentum_data["total_qualifying"],
                "total_amount": total_amount,
                "momentum": momentum_data["momentum"],
                "remainder": momentum_data["remainder"],
                "count": int(total),
            })
        finally:
            db.close()


class PortalPaymentDetailView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id, payment_id):
        principal = _portal_principal(request)
        customer_account_id, payment_id = int(customer_account_id), int(payment_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.payment.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            payment = db.get(Payment, payment_id)
            if payment is None or payment.customer_id != customer_id:
                raise NotFoundError("Payment not found.")

            has_receipt = db.execute(
                sa.select(sa.func.count(PaymentReceipt.receipt_id)).where(
                    PaymentReceipt.payment_id == payment_id
                )
            ).scalar() > 0

            return Response({
                "payment_id": payment.payment_id,
                "amount": float(payment.amount),
                "payment_date": payment.payment_date.isoformat(),
                "reference": payment.reference,
                "payment_method": payment.payment_method,
                "status": _enum_value(payment.status),
                "description": payment.description,
                "has_receipt": has_receipt,
            })
        finally:
            db.close()


class PortalPaymentReceiptView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id, payment_id):
        principal = _portal_principal(request)
        customer_account_id, payment_id = int(customer_account_id), int(payment_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.payment.view", customer_account_id=customer_account_id, db=db, request=request
            )
            receipt = db.execute(
                sa.select(PaymentReceipt).where(PaymentReceipt.payment_id == payment_id)
            ).scalar_one_or_none()
            if receipt is None:
                raise NotFoundError("Receipt not found.")
            return Response({
                "receipt_id": receipt.receipt_id,
                "receipt_number": receipt.receipt_number,
                "issued_at": receipt.issued_at.isoformat() if receipt.issued_at else None,
                "file_name": receipt.file_name,
                "storage_key": receipt.storage_key,
            })
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------

class PortalComplaintListView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.complaint.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            complaints = ComplaintService.list_for_customer(db, customer_id, principal.portal_user_id)
            data = []
            for c in complaints:
                data.append({
                    "complaint_id": c.complaint_id,
                    "complaint_number": c.complaint_number,
                    "subject": c.subject,
                    "category": c.category,
                    "priority": c.priority,
                    "status": _enum_value(c.status),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                })
            return Response({"results": data})
        finally:
            db.close()

    def post(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        serializer = PortalComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.complaint.create", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            complaint = ComplaintService.create(
                db,
                customer_id=customer_id,
                portal_user_id=principal.portal_user_id,
                **serializer.validated_data,
            )
            audit.record_audit(
                db,
                actor_portal_user_id=principal.portal_user_id,
                actor_type="PORTAL_USER",
                action="portal.complaint.created",
                resource_type="complaints",
                resource_id=complaint.complaint_id,
                description=f"Complaint {complaint.complaint_number} created",
                request=request,
            )
            db.commit()
            return Response({
                "complaint_id": complaint.complaint_id,
                "complaint_number": complaint.complaint_number,
                "subject": complaint.subject,
                "status": _enum_value(complaint.status),
            }, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class PortalComplaintDetailView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id, complaint_id):
        principal = _portal_principal(request)
        customer_account_id, complaint_id = int(customer_account_id), int(complaint_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.complaint.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            complaint = db.get(Complaint, complaint_id)
            if complaint is None or complaint.customer_id != customer_id:
                raise NotFoundError("Complaint not found.")
            return Response({
                "complaint_id": complaint.complaint_id,
                "complaint_number": complaint.complaint_number,
                "subject": complaint.subject,
                "category": complaint.category,
                "description": complaint.description,
                "priority": complaint.priority,
                "status": _enum_value(complaint.status),
                "preferred_contact": complaint.preferred_contact,
                "created_at": complaint.created_at.isoformat() if complaint.created_at else None,
                "updated_at": complaint.updated_at.isoformat() if complaint.updated_at else None,
            })
        finally:
            db.close()


class PortalComplaintMessageView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request, customer_account_id, complaint_id):
        principal = _portal_principal(request)
        customer_account_id, complaint_id = int(customer_account_id), int(complaint_id)
        serializer = PortalComplaintMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.complaint.respond", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            complaint = db.get(Complaint, complaint_id)
            if complaint is None or complaint.customer_id != customer_id:
                raise NotFoundError("Complaint not found.")

            msg = ComplaintService.add_message(
                db,
                complaint_id,
                sender_type="PORTAL_USER",
                portal_user_id=principal.portal_user_id,
                message=serializer.validated_data["message"],
            )
            audit.record_audit(
                db,
                actor_portal_user_id=principal.portal_user_id,
                actor_type="PORTAL_USER",
                action="portal.complaint.message_added",
                resource_type="complaint_messages",
                resource_id=msg.message_id,
                description=f"Message added to complaint {complaint.complaint_number}",
                request=request,
            )
            db.commit()
            return Response({
                "message_id": msg.message_id,
                "sender_type": msg.sender_type,
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class PortalComplaintTimelineView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id, complaint_id):
        principal = _portal_principal(request)
        customer_account_id, complaint_id = int(customer_account_id), int(complaint_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.complaint.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            complaint = db.get(Complaint, complaint_id)
            if complaint is None or complaint.customer_id != customer_id:
                raise NotFoundError("Complaint not found.")

            timeline = ComplaintService.get_timeline(db, complaint_id)
            for entry in timeline:
                if entry.get("created_at"):
                    entry["created_at"] = entry["created_at"].isoformat()
            return Response({"timeline": timeline})
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Documents (portal view over existing documents table)
# ---------------------------------------------------------------------------

class PortalDocumentListView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.document.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            from documents.models import Document

            category = request.query_params.get("category")
            conditions = [Document.customer_id == customer_id]
            if category:
                conditions.append(Document.document_type == category)

            docs = db.execute(
                sa.select(Document).where(sa.and_(*conditions)).order_by(sa.desc(Document.created_at))
            ).scalars().all()

            results = []
            for d in docs:
                results.append({
                    "document_id": d.document_id,
                    "document_type": d.document_type,
                    "current_version": d.current_version,
                    "access_classification": d.access_classification,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                })
            return Response({"results": results})
        finally:
            db.close()


class PortalDocumentDetailView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id, document_id):
        principal = _portal_principal(request)
        customer_account_id, document_id = int(customer_account_id), int(document_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.document.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            from documents.models import Document

            doc = db.get(Document, document_id)
            if doc is None or doc.customer_id != customer_id:
                raise NotFoundError("Document not found.")
            return Response({
                "document_id": doc.document_id,
                "document_type": doc.document_type,
                "current_version": doc.current_version,
                "access_classification": doc.access_classification,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            })
        finally:
            db.close()


class PortalDocumentDownloadView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id, document_id):
        principal = _portal_principal(request)
        customer_account_id, document_id = int(customer_account_id), int(document_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.document.download", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            from documents.models import Document, DocumentVersion

            doc = db.get(Document, document_id)
            if doc is None or doc.customer_id != customer_id:
                raise NotFoundError("Document not found.")

            version = db.execute(
                sa.select(DocumentVersion).where(
                    DocumentVersion.document_id == document_id,
                    DocumentVersion.is_current == sa.true(),
                )
            ).scalar_one_or_none()
            if version is None:
                raise NotFoundError("Document version not found.")

            from documents.storage import build_storage

            storage = build_storage(settings)
            url = storage.signed_url(version.storage_key, expires_in=3600)
            return Response({
                "download_url": url,
                "file_name": version.file_name,
                "mime_type": version.mime_type,
                "size_bytes": version.size_bytes,
            })
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class PortalNotificationListView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(principal, "portal.notification.view", db=db, request=request)
            unread_only = request.query_params.get("unread_only", "false").lower() == "true"
            notifications = NotificationService.list_for_user(
                db, principal.portal_user_id, unread_only=unread_only
            )
            data = []
            for n in notifications:
                data.append({
                    "notification_id": n.notification_id,
                    "type": _enum_value(n.type),
                    "title": n.title,
                    "body": n.body,
                    "reference_type": n.reference_type,
                    "reference_id": n.reference_id,
                    "is_read": bool(n.is_read),
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                })
            return Response({"count": len(data), "results": data})
        finally:
            db.close()


class PortalNotificationReadView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request, notification_id):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(principal, "portal.notification.read", db=db, request=request)
            NotificationService.mark_read(db, int(notification_id), principal.portal_user_id)
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class PortalNotificationReadAllView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(principal, "portal.notification.read", db=db, request=request)
            NotificationService.mark_all_read(db, principal.portal_user_id)
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

class PortalMomentumView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.momentum.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            summary = MomentumService.get_summary(db, customer_id)
            return Response(summary)
        finally:
            db.close()


class PortalMomentumHistoryView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.momentum.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            payments = db.execute(
                sa.select(Payment).where(
                    Payment.customer_id == customer_id,
                    Payment.status == "CONFIRMED",
                ).order_by(Payment.payment_date)
            ).scalars().all()

            running_total = 0.0
            history = []
            for p in payments:
                running_total += float(p.amount)
                history.append({
                    "payment_id": p.payment_id,
                    "reference": p.reference,
                    "amount": float(p.amount),
                    "payment_date": p.payment_date.isoformat(),
                    "running_total": running_total,
                    "momentum_at_point": int(running_total // 1000),
                })

            total = MomentumService.get_qualifying_total(db, customer_id)
            return Response({
                "total_qualifying": total,
                "momentum": int(total // 1000),
                "remainder": total % 1000,
                "history": history,
            })
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

class PortalRewardListView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(principal, "portal.reward.view", db=db, request=request)
            rewards = RewardService.list_all_active(db)
            data = []
            for r in rewards:
                data.append({
                    "reward_id": r.reward_id,
                    "name": r.name,
                    "description": r.description,
                    "required_momentum": r.required_momentum,
                    "status": _enum_value(r.status),
                    "redemption_limit": r.redemption_limit,
                    "available_from": r.available_from.isoformat() if r.available_from else None,
                    "available_until": r.available_until.isoformat() if r.available_until else None,
                })
            return Response({"results": data})
        finally:
            db.close()


class PortalRewardEligibleView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.reward.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            momentum = MomentumService.calculate_momentum(db, customer_id)
            rewards = RewardService.list_available(db, momentum)
            data = []
            for r in rewards:
                data.append({
                    "reward_id": r.reward_id,
                    "name": r.name,
                    "description": r.description,
                    "required_momentum": r.required_momentum,
                    "status": _enum_value(r.status),
                    "redemption_limit": r.redemption_limit,
                    "available_from": r.available_from.isoformat() if r.available_from else None,
                    "available_until": r.available_until.isoformat() if r.available_until else None,
                })
            return Response({"customer_momentum": momentum, "eligible_rewards": data})
        finally:
            db.close()


class PortalRewardRedeemView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request, customer_account_id, reward_id):
        principal = _portal_principal(request)
        customer_account_id, reward_id = int(customer_account_id), int(reward_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.reward.redeem", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            momentum = MomentumService.calculate_momentum(db, customer_id)
            redemption = RewardService.redeem(
                db,
                portal_user_id=principal.portal_user_id,
                customer_id=customer_id,
                reward_id=reward_id,
                customer_momentum=momentum,
            )
            audit.record_audit(
                db,
                actor_portal_user_id=principal.portal_user_id,
                actor_type="PORTAL_USER",
                action="portal.reward.redeemed",
                resource_type="reward_redemptions",
                resource_id=redemption.redemption_id,
                description=f"Reward {reward_id} redeemed for {redemption.momentum_used} momentum",
                request=request,
            )
            db.commit()
            return Response({
                "redemption_id": redemption.redemption_id,
                "reward_id": redemption.reward_id,
                "momentum_used": redemption.momentum_used,
                "status": _enum_value(redemption.status),
            }, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class PortalRewardRedemptionListView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, customer_account_id):
        principal = _portal_principal(request)
        customer_account_id = int(customer_account_id)
        db = SessionLocal()
        try:
            _require_portal_permission(
                principal, "portal.reward.view", customer_account_id=customer_account_id, db=db, request=request
            )
            _, customer_id = _resolve_customer_account(db, customer_account_id, principal)
            redemptions = RewardService.list_redemptions(db, principal.portal_user_id, customer_id)
            data = []
            for r in redemptions:
                reward = db.get(Reward, r.reward_id)
                data.append({
                    "redemption_id": r.redemption_id,
                    "reward_id": r.reward_id,
                    "reward_name": reward.name if reward else None,
                    "momentum_used": r.momentum_used,
                    "status": _enum_value(r.status),
                    "redeemed_at": r.redeemed_at.isoformat() if r.redeemed_at else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })
            return Response({"results": data})
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class PortalProfileView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        principal = _portal_principal(request)
        db = SessionLocal()
        try:
            _require_portal_permission(principal, "portal.profile.view", db=db, request=request)
            links = db.execute(
                sa.select(PortalUserCustomer, CustomerAccount, Customer)
                .outerjoin(CustomerAccount, PortalUserCustomer.customer_account_id == CustomerAccount.customer_account_id)
                .outerjoin(Customer, CustomerAccount.customer_id == Customer.customer_id)
                .where(
                    PortalUserCustomer.portal_user_id == principal.portal_user_id,
                    PortalUserCustomer.is_active == sa.true(),
                )
            ).all()
            accounts = []
            for link, account, customer in links:
                accounts.append({
                    "customer_account_id": link.customer_account_id,
                    "account_number": account.account_number if account else None,
                    "customer_id": account.customer_id if account else None,
                    "customer_number": customer.customer_number if customer else None,
                    "display_name": customer.get_display_name() if customer else None,
                    "role": _enum_value(link.role),
                    "is_primary": bool(link.is_primary),
                })
            return Response({
                "portal_user_id": principal.portal_user_id,
                "email": principal.email,
                "first_name": principal.portal_user.first_name,
                "last_name": principal.portal_user.last_name,
                "phone": principal.portal_user.phone,
                "accounts": accounts,
            })
        finally:
            db.close()


PORTAL_FAQS = [
    {"id": "faq1", "question": "How do I make a payment?", "answer": "Navigate to the Payments section and click 'Make Payment'. You can pay via bank transfer or mobile money."},
    {"id": "faq2", "question": "How is Momentum calculated?", "answer": "You earn 1 Momentum for every KES 1,000 of qualifying confirmed payments. Momentum never expires."},
    {"id": "faq3", "question": "How do I raise a complaint?", "answer": "Go to Complaints and click 'Raise Complaint'. Fill in the details and submit. You will receive a reference number."},
    {"id": "faq4", "question": "How do I download my documents?", "answer": "Go to Documents, find the document you need, and click the download button. Documents are available based on your access permissions."},
    {"id": "faq5", "question": "How do I add another portal user?", "answer": "Go to Profile > Authorized Users and click 'Invite User'. You need MANAGE_PORTAL_USERS permission."},
]


class PortalFaqView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        return Response(PORTAL_FAQS)


class PortalSupportRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField(max_length=2000)


class PortalSupportRequestView(APIView):
    authentication_classes = [PortalJWTBearerAuthentication]
    permission_classes = [IsPortalAuthenticated]

    def post(self, request):
        principal = _portal_principal(request)
        serializer = PortalSupportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info(
            "Support request from portal user %s: subject=%s",
            principal.portal_user_id,
            serializer.validated_data["subject"],
        )
        return Response({"status": "submitted", "message": "Your support request has been received. We will respond within 24 hours."}, status=status.HTTP_201_CREATED)