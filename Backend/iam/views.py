import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common import audit
from common.db import SessionLocal
from common.exceptions import APIError
from iam.models import AuthenticationCredential, Role, User, UserRole, UserStatus
from iam.permissions import IsAuthenticated
from iam.serializers import (
    ForgotPasswordRequestSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    MeSerializer,
    RegisterRequestSerializer,
    ResetPasswordRequestSerializer,
)
from iam.services import (
    authenticate,
    create_reset_token,
    create_session,
    get_user_by_credentials,
    hash_password,
    issue_access_token,
    reset_password,
    revoke_session,
)

logger = logging.getLogger(__name__)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        db = SessionLocal()
        try:
            user = authenticate(
                db,
                serializer.validated_data["username"],
                serializer.validated_data["password"],
            )
            if user is None:
                audit.record_audit(
                    db,
                    actor_user_id=None,
                    action="login.failed",
                    resource_type="users",
                    description=f"Failed login for {serializer.validated_data['username']}",
                    request=request,
                )
                db.commit()
                raise APIError("Invalid username or password.", status_code=401, error_code="invalid_credentials")

            user_session = create_session(
                db,
                user,
                request.META.get("REMOTE_ADDR"),
                request.META.get("HTTP_USER_AGENT", ""),
            )
            token = issue_access_token(user.user_id, user_session.session_id)

            from iam.permissions import UserPrincipal

            principal = UserPrincipal(db, user)
            data = LoginResponseSerializer(
                {
                    "token": token,
                    "token_type": "Bearer",
                    "expires_in": settings.JWT_ACCESS_TTL_MINUTES * 60,
                    "user": {
                        "user_id": user.user_id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "department_id": user.department_id,
                        "team_id": user.team_id,
                        "permissions": principal.get_permissions(),
                        "role_codes": principal.get_role_codes(),
                        "scope": principal.effective_scope("clients.customer"),
                    },
                }
            ).data
            audit.record_audit(
                db,
                actor_user_id=user.user_id,
                action="login.success",
                resource_type="users",
                resource_id=user.user_id,
                description=f"User {user.username} logged in",
                request=request,
            )
            db.commit()
            return Response(data, status=status.HTTP_200_OK)
        finally:
            db.close()


class LogoutView(APIView):
    def post(self, request):
        principal = getattr(request, "user", None)
        payload = getattr(request, "auth", None)
        db = SessionLocal()
        try:
            from iam.services import decode_access_token

            if payload:
                token_payload = decode_access_token(payload)
                revoke_session(db, int(token_payload["sid"]))
                audit.record_audit(
                    db,
                    actor_user_id=principal.user_id if principal else None,
                    action="logout",
                    resource_type="users",
                    resource_id=principal.user_id if principal else None,
                    description="User logged out",
                    request=request,
                )
                db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        principal = getattr(request, "user", None)
        data = MeSerializer(
            {
                "user_id": principal.user_id,
                "username": principal.username,
                "email": principal.email,
                "first_name": principal.user.first_name,
                "last_name": principal.user.last_name,
                "department_id": principal.department_id,
                "team_id": principal.team_id,
                "permissions": principal.get_permissions(),
                "role_codes": principal.get_role_codes(),
                "scope": principal.effective_scope("clients.customer"),
            }
        ).data
        return Response(data)


DEFAULT_REGISTRATION_ROLE = "SALES_REP"


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        db = SessionLocal()
        try:
            existing = db.execute(
                sa.select(User).where(
                    (User.username == data["username"]) | (User.email == data["email"])
                )
            ).scalar_one_or_none()
            if existing:
                if existing.username == data["username"]:
                    raise APIError(
                        "Username is already taken.",
                        status_code=409,
                        error_code="username_taken",
                        field_errors={"username": "Username is already taken."},
                    )
                raise APIError(
                    "Email is already registered.",
                    status_code=409,
                    error_code="email_taken",
                    field_errors={"email": "Email is already registered."},
                )

            user = User(
                username=data["username"],
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                status=UserStatus.ACTIVE.value,
            )
            db.add(user)
            db.flush()

            db.add(
                AuthenticationCredential(
                    user_id=user.user_id,
                    password_hash=hash_password(data["password"]),
                )
            )

            role = db.execute(
                sa.select(Role).where(Role.code == DEFAULT_REGISTRATION_ROLE)
            ).scalar_one_or_none()
            if role:
                db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

            audit.record_audit(
                db,
                actor_user_id=user.user_id,
                action="user.registered",
                resource_type="users",
                resource_id=user.user_id,
                description=f"New user registered: {user.username}",
                request=request,
            )
            db.commit()

            return Response(
                {
                    "message": "Account created successfully. You can now sign in.",
                    "user_id": user.user_id,
                },
                status=status.HTTP_201_CREATED,
            )
        finally:
            db.close()


class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]

        db = SessionLocal()
        try:
            user = get_user_by_credentials(db, username)
            reset_token = None
            if user is not None and user.status == UserStatus.ACTIVE.value:
                reset_token = create_reset_token(db, user.user_id)

            audit.record_audit(
                db,
                actor_user_id=user.user_id if user else None,
                action="password.reset_requested",
                resource_type="users",
                resource_id=user.user_id if user else None,
                description=f"Password reset requested for {username}",
                request=request,
            )
            db.commit()

            data = {
                "detail": "If an account exists for that username, a reset token has been delivered out-of-band.",
            }
            if reset_token and settings.DEBUG:
                data["debug_reset_token"] = reset_token
            return Response(data, status=status.HTTP_200_OK)
        finally:
            db.close()


class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        db = SessionLocal()
        try:
            user = reset_password(db, data["token"], data["new_password"])

            audit.record_audit(
                db,
                actor_user_id=user.user_id,
                action="password.reset",
                resource_type="users",
                resource_id=user.user_id,
                description=f"User {user.username} reset their password",
                request=request,
            )
            db.commit()
            return Response(
                {"detail": "Password has been reset successfully."},
                status=status.HTTP_200_OK,
            )
        finally:
            db.close()
