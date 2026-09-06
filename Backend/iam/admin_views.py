import logging
import secrets

import sqlalchemy as sa
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common import audit
from common.db import SessionLocal
from common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnprocessableEntityError,
    ValidationError_,
)
from iam.access_services import (
    effective_access,
    effective_scope,
    rights_preview_for_roles,
)
from iam.admin_serializers import (
    DirectPermissionSerializer,
    OperatorDetailSerializer,
    OperatorReadSerializer,
    OperatorUpdateSerializer,
    OperatorWriteSerializer,
    RoleAssignSerializer,
    RoleReadSerializer,
    RoleWriteSerializer,
)
from iam.models import (
    AccessPolicy,
    AccessScope,
    AuthenticationCredential,
    Department,
    Permission,
    Role,
    RoleAccessPolicy,
    RolePermission,
    Team,
    User,
    UserAccessPolicy,
    UserPermission,
    UserRole,
    UserStatus,
)
from iam.services import hash_password

logger = logging.getLogger(__name__)


def _principal(request):
    from iam.permissions import UserPrincipal

    p = getattr(request, "user", None)
    if not isinstance(p, UserPrincipal):
        raise PermissionDeniedError("Authentication required.")
    return p


def _require(request, permission_code):
    principal = _principal(request)
    if not principal.has_permission(permission_code):
        raise PermissionDeniedError(f"Missing required permission: {permission_code}")
    return principal


def _get_user(db, operator_id):
    operator = db.get(User, int(operator_id))
    if operator is None:
        raise NotFoundError("Operator not found.")
    return operator


def _role_codes_for(db, user_id):
    ur = UserRole.__table__
    role = Role.__table__
    rows = db.execute(
        sa.select(role.c.code)
        .select_from(ur.join(role, ur.c.role_id == role.c.role_id))
        .where(ur.c.user_id == user_id)
    ).scalars().all()
    return sorted(rows)


def _direct_permission_rows(db, user_id):
    perm = Permission.__table__
    up = UserPermission.__table__
    rows = db.execute(
        sa.select(perm.c.code, up.c.effect, up.c.reason)
        .select_from(up.join(perm, up.c.permission_id == perm.c.permission_id))
        .where(up.c.user_id == user_id)
        .order_by(perm.c.code)
    ).fetchall()
    return [
        {"permission_code": r.code, "effect": r.effect, "reason": r.reason} for r in rows
    ]


class OperatorListView(APIView):
    def get(self, request):
        _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            operators = db.execute(sa.select(User).order_by(User.username)).scalars().all()
            data = []
            for op in operators:
                data.append(
                    OperatorReadSerializer(
                        {
                            "user_id": op.user_id,
                            "username": op.username,
                            "email": op.email,
                            "first_name": op.first_name,
                            "last_name": op.last_name,
                            "phone": op.phone,
                            "department_id": op.department_id,
                            "team_id": op.team_id,
                            "status": op.status,
                            "role_codes": _role_codes_for(db, op.user_id),
                            "is_active": op.status == UserStatus.ACTIVE.value,
                        }
                    ).data
                )
            return Response({"count": len(data), "operators": data})
        finally:
            db.close()

    def post(self, request):
        principal = _require(request, "iam.user.manage")
        serializer = OperatorWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        role_codes = payload.pop("role_codes", [])

        db = SessionLocal()
        try:
            existing = db.execute(
                sa.select(User).where(
                    (User.username == payload["username"]) | (User.email == payload["email"])
                )
            ).scalar_one_or_none()
            if existing:
                raise ValidationError_(
                    "A user with that username or email already exists.",
                    {"username": "Username or email already in use."},
                )

            _validate_roles(db, role_codes)
            _validate_department_team(db, payload)

            operator = User(**payload)
            db.add(operator)
            db.flush()

            temp_password = secrets.token_urlsafe(16)
            db.add(
                AuthenticationCredential(
                    user_id=operator.user_id,
                    password_hash=hash_password(temp_password),
                )
            )

            for code in role_codes:
                role = db.execute(sa.select(Role).where(Role.code == code)).scalar_one()
                db.add(UserRole(user_id=operator.user_id, role_id=role.role_id, assigned_by=principal.user_id))

            role_ids = [r.role_id for r in _roles(db, role_codes)]
            preview = rights_preview_for_roles(db, role_ids)

            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="operator.created",
                resource_type="users",
                resource_id=operator.user_id,
                description=f"Operator {operator.username} created with roles {role_codes}",
                request=request,
            )
            db.commit()
            db.refresh(operator)
            return Response(
                {
                    "operator": OperatorReadSerializer(_operator_dict(db, operator)).data,
                    "rights_preview": preview,
                    "temporary_password": temp_password,
                },
                status=status.HTTP_201_CREATED,
            )
        finally:
            db.close()


class OperatorDetailView(APIView):
    def get(self, request, operator_id):
        _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            return Response(_operator_detail_dict(db, operator))
        finally:
            db.close()

    def patch(self, request, operator_id):
        principal = _require(request, "iam.user.manage")
        serializer = OperatorUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            for key, value in serializer.validated_data.items():
                setattr(operator, key, value)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="operator.updated",
                resource_type="users",
                resource_id=operator.user_id,
                description=f"Operator {operator.username} updated",
                request=request,
            )
            db.commit()
            db.refresh(operator)
            return Response(_operator_detail_dict(db, operator))
        finally:
            db.close()


class OperatorRolesView(APIView):
    def put(self, request, operator_id):
        principal = _require(request, "iam.user.manage")
        serializer = RoleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_codes = serializer.validated_data["role_codes"]
        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            _validate_roles(db, role_codes)

            db.execute(sa.delete(UserRole).where(UserRole.user_id == operator.user_id))
            for code in role_codes:
                role = db.execute(sa.select(Role).where(Role.code == code)).scalar_one()
                db.add(UserRole(user_id=operator.user_id, role_id=role.role_id, assigned_by=principal.user_id))

            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="operator.roles.changed",
                resource_type="users",
                resource_id=operator.user_id,
                description=f"Operator {operator.username} roles set to {role_codes}",
                request=request,
            )
            db.commit()
            role_ids = [r.role_id for r in _roles(db, role_codes)]
            return Response(
                {
                    "role_codes": role_codes,
                    "rights_preview": rights_preview_for_roles(db, role_ids),
                }
            )
        finally:
            db.close()


class OperatorDirectPermissionView(APIView):
    def get(self, request, operator_id):
        _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            return Response({"direct_permissions": _direct_permission_rows(db, operator.user_id)})
        finally:
            db.close()

    def post(self, request, operator_id):
        principal = _require(request, "iam.user.manage")
        serializer = DirectPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permission_code = serializer.validated_data["permission_code"]
        effect = serializer.validated_data["effect"]
        reason = serializer.validated_data.get("reason", "")

        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            permission = db.execute(
                sa.select(Permission).where(
                    Permission.code == permission_code, Permission.is_active == sa.true()
                )
            ).scalar_one_or_none()
            if permission is None:
                raise ValidationError_(f"Unknown permission: {permission_code}", {"permission_code": "Unknown permission."})

            row = db.execute(
                sa.select(UserPermission).where(
                    UserPermission.user_id == operator.user_id,
                    UserPermission.permission_id == permission.permission_id,
                )
            ).scalar_one_or_none()
            if row is None:
                row = UserPermission(
                    user_id=operator.user_id,
                    permission_id=permission.permission_id,
                    effect=effect,
                    assigned_by=principal.user_id,
                    reason=reason,
                )
                db.add(row)
            else:
                row.effect = effect
                row.assigned_by = principal.user_id
                row.reason = reason

            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="operator.direct_permission.set",
                resource_type="user_permissions",
                resource_id=operator.user_id,
                description=f"Direct {effect} {permission_code} for {operator.username}",
                request=request,
            )
            db.commit()
            return Response(
                {"permission_code": permission_code, "effect": effect, "reason": reason}
            )
        finally:
            db.close()

    def delete(self, request, operator_id, permission_code):
        principal = _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            permission = db.execute(
                sa.select(Permission).where(Permission.code == permission_code)
            ).scalar_one_or_none()
            if permission is None:
                raise NotFoundError("Permission not found.")
            row = db.execute(
                sa.select(UserPermission).where(
                    UserPermission.user_id == operator.user_id,
                    UserPermission.permission_id == permission.permission_id,
                )
            ).scalar_one_or_none()
            if row:
                db.delete(row)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="operator.direct_permission.revoked",
                resource_type="user_permissions",
                resource_id=operator.user_id,
                description=f"Revoked direct permission {permission_code} for {operator.username}",
                request=request,
            )
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class OperatorAccessReviewView(APIView):
    def get(self, request, operator_id):
        _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            _get_user(db, operator_id)
            result = effective_access(db, operator_id)
            if result is None:
                raise NotFoundError("Operator not found.")
            return Response(_deref_enums(result))
        finally:
            db.close()


class RoleListView(APIView):
    def post(self, request):
        principal = _require(request, "iam.role.manage")
        serializer = RoleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        db = SessionLocal()
        try:
            payload = _normalize_role_payload(db, dict(serializer.validated_data))
            if payload.get("is_system_role"):
                raise UnprocessableEntityError(
                    "System roles are managed by the platform and cannot be "
                    "created through the API.",
                    {"is_system_role": "Not permitted."},
                )
            code = payload["code"] or _slug_role_code(payload["name"])
            payload["code"] = code
            existing = db.execute(
                sa.select(Role).where((Role.code == code) | (Role.name == payload["name"]))
            ).scalar_one_or_none()
            if existing:
                raise ConflictError("Role code or name already exists.", error_code="role_conflict")

            permission_codes = payload.pop("permission_codes", [])
            access_policy_codes = payload.pop("access_policy_codes", [])

            role = Role(**payload)
            db.add(role)
            db.flush()
            _validate_role_permissions(db, permission_codes)
            _set_role_permissions(db, principal.user_id, role, permission_codes)
            _set_role_policies(db, principal.user_id, role, access_policy_codes)

            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="role.created",
                resource_type="roles",
                resource_id=role.role_id,
                description=f"Role {role.code} created",
                request=request,
            )
            db.commit()
            return Response(_role_dict(db, role), status=status.HTTP_201_CREATED)
        finally:
            db.close()

    def get(self, request):
        _require(request, "iam.role.manage")
        db = SessionLocal()
        try:
            roles = db.execute(sa.select(Role).order_by(Role.code)).scalars().all()
            counts = _operator_counts_by_role(db)
            data = [_role_dict(db, r, operator_counts=counts) for r in roles]
            return Response({"count": len(data), "roles": data})
        finally:
            db.close()


class RoleDetailView(APIView):
    def get(self, request, role_id):
        _require(request, "iam.role.manage")
        db = SessionLocal()
        try:
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")
            return Response(_role_dict(db, role))
        finally:
            db.close()

    def patch(self, request, role_id):
        principal = _require(request, "iam.role.manage")
        serializer = RoleWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        db = SessionLocal()
        try:
            provided = dict(request.data)
            rights_given = "rights" in provided or "permission_codes" in provided
            policies_given = "scope" in provided or "access_policy_codes" in provided
            payload = _normalize_role_payload(db, dict(serializer.validated_data))
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")

            is_system_role = bool(role.is_system_role)
            if is_system_role:
                if "code" in payload and payload.get("code") and payload["code"] != role.code:
                    raise UnprocessableEntityError(
                        "System role code is immutable.",
                        {"code": "Immutable for system roles."},
                    )
                if "is_active" in payload and payload["is_active"] is False:
                    _guard_role_deactivation(db, role)
            if "is_system_role" in payload and payload["is_system_role"] != is_system_role:
                raise UnprocessableEntityError(
                    "The system-role flag is immutable.",
                    {"is_system_role": "Immutable; cannot be converted."},
                )

            code = payload.get("code") or None
            if code:
                dup = db.execute(
                    sa.select(Role).where(
                        (Role.code == code) & (Role.role_id != role.role_id)
                    )
                ).scalar_one_or_none()
                if dup:
                    raise ConflictError("Role code already exists.", error_code="role_conflict")
                role.code = code

            if "name" in payload:
                dup = db.execute(
                    sa.select(Role).where(
                        (Role.name == payload["name"]) & (Role.role_id != role.role_id)
                    )
                ).scalar_one_or_none()
                if dup:
                    raise ConflictError("Role name already exists.", error_code="role_conflict")

            for key in ("name", "description", "is_active", "is_system_role"):
                if key in payload:
                    setattr(role, key, payload[key])

            if rights_given:
                _validate_role_permissions(db, payload["permission_codes"])
                _set_role_permissions(db, principal.user_id, role, payload["permission_codes"])
            if policies_given:
                _validate_role_policies(db, payload["access_policy_codes"])
                _set_role_policies(db, principal.user_id, role, payload["access_policy_codes"])

            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="role.updated",
                resource_type="roles",
                resource_id=role.role_id,
                description=f"Role {role.code} updated",
                request=request,
            )
            db.commit()
            return Response(_role_dict(db, role))
        finally:
            db.close()


class RightsCatalogueView(APIView):
    def get(self, request):
        _require(request, "iam.permission.audit")
        db = SessionLocal()
        try:
            stmt = sa.select(Permission)
            filters = {}
            for key, col in (("resource", Permission.resource), ("action", Permission.action)):
                value = request.query_params.get(key)
                if value:
                    filters[key] = value
                    stmt = stmt.where(col == value)
            code = request.query_params.get("code")
            if code:
                filters["code"] = code
                stmt = stmt.where(Permission.code.like(f"%{code}%"))
            status_param = request.query_params.get("status")
            if status_param == "INACTIVE":
                filters["status"] = "INACTIVE"
                stmt = stmt.where(Permission.is_active == sa.false())
            elif status_param == "ALL":
                filters["status"] = "ALL"
            else:
                filters.setdefault("status", "ACTIVE")
                stmt = stmt.where(Permission.is_active == sa.true())
            rows = db.execute(stmt.order_by(Permission.resource, Permission.action)).scalars().all()
            return Response(
                {
                    "count": len(rows),
                    "filters": filters,
                    "permissions": [
                        {
                            "permission_id": p.permission_id,
                            "code": p.code,
                            "name": p.name,
                            "resource": p.resource,
                            "action": p.action,
                            "description": p.description,
                            "is_active": bool(p.is_active),
                        }
                        for p in rows
                    ],
                }
            )
        finally:
            db.close()


class ScopeListView(APIView):
    def get(self, request):
        _require(request, "iam.role.manage")
        from iam.admin_serializers import SCOPE_MEANINGS

        return Response(
            {
                "scopes": [
                    {"code": code, "meaning": meaning} for code, meaning in SCOPE_MEANINGS.items()
                ]
            }
        )


class RightsDetailView(APIView):
    def get(self, request, permission_id):
        _require(request, "iam.permission.audit")
        db = SessionLocal()
        try:
            permission = db.execute(
                sa.select(Permission).where(
                    Permission.permission_id == int(permission_id),
                    Permission.is_active == sa.true(),
                )
            ).scalar_one_or_none()
            if permission is None:
                raise NotFoundError("Right not found.")
            return Response({
                "permission_id": permission.permission_id,
                "code": permission.code,
                "name": permission.name,
                "resource": permission.resource,
                "action": permission.action,
                "description": permission.description,
                "is_active": bool(permission.is_active),
            })
        finally:
            db.close()


class RoleRightsView(APIView):
    """Role rights batch operations.

    GET    /api/roles/{id}/rights        — authoritative assigned-right list
    PUT    /api/roles/{id}/rights        — replace the complete selection (sync)
    POST   /api/roles/{id}/rights        — add one or many rights (idempotent)
    DELETE /api/roles/{id}/rights        — remove one or many rights
    """

    def get(self, request, role_id):
        _require(request, "iam.role.manage")
        db = SessionLocal()
        try:
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")
            return Response(_role_dict(db, role))
        finally:
            db.close()

    def put(self, request, role_id):
        principal = _require(request, "iam.role.manage")
        db = SessionLocal()
        try:
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")
            codes = _parse_role_rights(db, request.data)
            _validate_role_permissions(db, codes)
            _set_role_permissions(db, principal.user_id, role, codes)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="role.rights.replaced",
                resource_type="roles",
                resource_id=role.role_id,
                description=f"Role {role.code} rights set to {len(codes)} permissions",
                request=request,
            )
            db.commit()
            return Response(_role_dict(db, role))
        finally:
            db.close()

    def post(self, request, role_id):
        principal = _require(request, "iam.role.manage")
        db = SessionLocal()
        try:
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")
            codes = _parse_role_rights(db, request.data)
            if not codes:
                raise UnprocessableEntityError(
                    "No rights to add.",
                    {"rights": "Supply at least one right code or right_id."},
                )
            _validate_role_permissions(db, codes)
            rp = RolePermission.__table__
            perm = Permission.__table__
            existing = set(
                db.execute(
                    sa.select(perm.c.code)
                    .select_from(rp.join(perm, rp.c.permission_id == perm.c.permission_id))
                    .where(rp.c.role_id == role.role_id)
                ).scalars().all()
            )
            to_add = [c for c in codes if c not in existing]
            if to_add:
                perms = db.execute(
                    sa.select(Permission).where(
                        Permission.code.in_(to_add),
                        Permission.is_active == sa.true(),
                    )
                ).scalars().all()
                for p in perms:
                    db.add(RolePermission(role_id=role.role_id, permission_id=p.permission_id))
                db.flush()
                audit.record_audit(
                    db,
                    actor_user_id=principal.user_id,
                    action="role.rights.added",
                    resource_type="roles",
                    resource_id=role.role_id,
                    description=f"Role {role.code} rights added: {to_add}",
                    metadata={"added": to_add},
                    request=request,
                )
            db.commit()
            return Response(_role_dict(db, role))
        finally:
            db.close()

    def delete(self, request, role_id):
        principal = _require(request, "iam.role.manage")
        db = SessionLocal()
        try:
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")
            codes = _parse_role_rights(db, request.data)
            if not codes:
                raise UnprocessableEntityError(
                    "No rights to remove.",
                    {"rights": "Supply at least one right code or right_id."},
                )
            _validate_role_permissions(db, codes)
            perm = Permission.__table__
            rp = RolePermission.__table__
            deleted = db.execute(
                sa.delete(RolePermission).where(
                    rp.c.role_id == role.role_id,
                    rp.c.permission_id.in_(
                        sa.select(perm.c.permission_id).where(perm.c.code.in_(codes))
                    ),
                )
            ).rowcount
            if deleted:
                audit.record_audit(
                    db,
                    actor_user_id=principal.user_id,
                    action="role.rights.removed",
                    resource_type="roles",
                    resource_id=role.role_id,
                    description=f"Role {role.code} rights removed: {codes}",
                    metadata={"removed": codes},
                    request=request,
                )
            db.commit()
            return Response(_role_dict(db, role))
        finally:
            db.close()


class RoleOperatorsView(APIView):
    def get(self, request, role_id):
        _require(request, "iam.role.manage")
        db = SessionLocal()
        try:
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")
            ur = UserRole.__table__
            rows = db.execute(
                sa.select(User)
                .select_from(ur.join(User, ur.c.user_id == User.user_id))
                .where(ur.c.role_id == role.role_id)
                .order_by(User.username)
            ).scalars().all()
            return Response(
                {
                    "role_id": role.role_id,
                    "operators": [
                        {
                            "user_id": u.user_id,
                            "username": u.username,
                            "email": u.email,
                            "status": u.status.value if hasattr(u.status, "value") else u.status,
                        }
                        for u in rows
                    ],
                }
            )
        finally:
            db.close()


class OperatorAssignRoleView(APIView):
    """POST /api/operators/{id}/roles — assign one role (idempotent)."""

    def post(self, request, operator_id):
        principal = _require(request, "iam.user.manage")
        serializer = RoleAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role_codes = serializer.validated_data["role_codes"]

        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            _validate_roles(db, role_codes)
            for code in role_codes:
                role = db.execute(sa.select(Role).where(Role.code == code)).scalar_one()
                existing = db.execute(
                    sa.select(UserRole).where(
                        UserRole.user_id == operator.user_id,
                        UserRole.role_id == role.role_id,
                    )
                ).scalar_one_or_none()
                if existing is None:
                    db.add(
                        UserRole(
                            user_id=operator.user_id,
                            role_id=role.role_id,
                            assigned_by=principal.user_id,
                        )
                    )
                    audit.record_audit(
                        db,
                        actor_user_id=principal.user_id,
                        action="operator.role.assigned",
                        resource_type="user_roles",
                        resource_id=operator.user_id,
                        description=f"Operator {operator.username} assigned role {code}",
                        request=request,
                    )
            db.commit()
            role_ids = [r.role_id for r in _roles(db, role_codes)]
            return Response(
                {
                    "role_codes": role_codes,
                    "rights_preview": rights_preview_for_roles(db, role_ids),
                }
            )
        finally:
            db.close()


class OperatorRemoveRoleView(APIView):
    """DELETE /api/operators/{id}/roles/{role_id} — remove one role."""

    def delete(self, request, operator_id, role_id):
        principal = _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            role = db.get(Role, int(role_id))
            if role is None:
                raise NotFoundError("Role not found.")
            row = db.execute(
                sa.select(UserRole).where(
                    UserRole.user_id == operator.user_id,
                    UserRole.role_id == role.role_id,
                )
            ).scalar_one_or_none()
            if row:
                db.delete(row)
                audit.record_audit(
                    db,
                    actor_user_id=principal.user_id,
                    action="operator.role.removed",
                    resource_type="user_roles",
                    resource_id=operator.user_id,
                    description=f"Operator {operator.username} removed from role {role.code}",
                    request=request,
                )
                db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class OperatorEffectiveRightsView(APIView):
    """GET /api/operators/{id}/effective-rights — rights inherited from active roles."""

    def get(self, request, operator_id):
        _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            operator = _get_user(db, operator_id)
            result = effective_access(db, operator.user_id)
            if result is None:
                raise NotFoundError("Operator not found.")
            rights = [
                {
                    "permission_id": p["permission_id"],
                    "code": p["code"],
                    "name": p["name"],
                    "resource": p["resource"],
                    "action": p["action"],
                }
                for p in result["permissions"]
                if p["effective"] == "ALLOW"
                and any(s.get("source") == "role" for s in p["sources"])
            ]
            return Response(
                {
                    "user_id": operator.user_id,
                    "username": operator.username,
                    "roles": [r["code"] for r in result["roles"]],
                    "rights": rights,
                    "scope": result["scope"],
                }
            )
        finally:
            db.close()


class OperatorEffectiveAccessView(APIView):
    """GET /api/operators/{id}/effective-access — full permissions + visibility scope."""

    def get(self, request, operator_id):
        _require(request, "iam.user.manage")
        db = SessionLocal()
        try:
            _get_user(db, operator_id)
            result = effective_access(db, operator_id)
            if result is None:
                raise NotFoundError("Operator not found.")
            return Response(_deref_enums(result))
        finally:
            db.close()


class MePermissionsView(APIView):
    """GET /api/me/permissions — current operator's effective grants."""

    def get(self, request):
        principal = _principal(request)
        db = SessionLocal()
        try:
            result = effective_access(db, principal.user_id)
            if result is None:
                raise NotFoundError("Operator not found.")
            allowed = [
                {
                    "permission_id": p["permission_id"],
                    "code": p["code"],
                    "resource": p["resource"],
                    "action": p["action"],
                }
                for p in result["permissions"]
                if p["effective"] == "ALLOW"
            ]
            return Response(
                {
                    "user_id": result["user_id"],
                    "username": result["username"],
                    "permissions": allowed,
                    "scope": result["scope"],
                    "roles": [r["code"] for r in result["roles"]],
                }
            )
        finally:
            db.close()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _operator_dict(db, operator):
    return {
        "user_id": operator.user_id,
        "username": operator.username,
        "email": operator.email,
        "first_name": operator.first_name,
        "last_name": operator.last_name,
        "phone": operator.phone,
        "department_id": operator.department_id,
        "team_id": operator.team_id,
        "status": operator.status,
        "role_codes": _role_codes_for(db, operator.user_id),
        "is_active": operator.status == UserStatus.ACTIVE.value,
        "created_at": operator.created_at,
        "updated_at": operator.updated_at,
    }


def _operator_detail_dict(db, operator):
    ur = UserRole.__table__
    role = Role.__table__
    roles = db.execute(
        sa.select(Role)
        .select_from(ur.join(role, ur.c.role_id == role.c.role_id))
        .where(ur.c.user_id == operator.user_id)
        .order_by(role.c.code)
    ).scalars().all()
    data = OperatorDetailSerializer(
        {
            **_operator_dict(db, operator),
            "roles": [
                {
                    "role_id": r.role_id,
                    "code": r.code,
                    "name": r.name,
                    "description": r.description,
                }
                for r in roles
            ],
            "direct_permissions": _direct_permission_rows(db, operator.user_id),
        }
    ).data
    _codes, scope = effective_scope(db, operator.user_id)
    data["effective_scope"] = scope
    return data


def _validate_roles(db, role_codes):
    if not role_codes:
        return
    active_codes = set(
        db.execute(sa.select(Role.code).where(Role.is_active == sa.true())).scalars().all()
    )
    for code in role_codes:
        if code not in active_codes:
            raise ValidationError_(f"Unknown or inactive role: {code}", {"role_codes": f"Unknown role: {code}"})


def _validate_department_team(db, payload):
    department_id = payload.get("department_id")
    team_id = payload.get("team_id")
    if department_id is not None:
        department = db.get(Department, department_id)
        if department is None:
            raise ValidationError_("Department not found.", {"department_id": "Unknown department."})
    if team_id is not None:
        team = db.get(Team, team_id)
        if team is None:
            raise ValidationError_("Team not found.", {"team_id": "Unknown team."})


def _roles(db, role_codes):
    if not role_codes:
        return []
    return db.execute(sa.select(Role).where(Role.code.in_(role_codes))).scalars().all()


def _role_dict(db, role, operator_counts=None, permission_codes=None, scope_codes=None, scopes=None):
    if permission_codes is None:
        rp = RolePermission.__table__
        perm = Permission.__table__
        permission_codes = db.execute(
            sa.select(perm.c.code)
            .select_from(rp.join(perm, rp.c.permission_id == perm.c.permission_id))
            .where(rp.c.role_id == role.role_id)
            .order_by(perm.c.code)
        ).scalars().all()
    if scope_codes is None or scopes is None:
        rap = RoleAccessPolicy.__table__
        ap = AccessPolicy.__table__
        stats = db.execute(
            sa.select(ap.c.code, ap.c.scope)
            .select_from(rap.join(ap, rap.c.access_policy_id == ap.c.access_policy_id))
            .where(rap.c.role_id == role.role_id)
        ).all()
        scope_codes = [row.code for row in stats]
        scopes = [row.scope for row in stats]
    from iam.access_services import SCOPE_RANKING

    effective_scope = max(scopes, key=lambda s: SCOPE_RANKING.get(s, 0)) if scopes else "NONE"
    if operator_counts is None:
        ur = UserRole.__table__
        operator_counts = {
            row.role_id: row.n for row in db.execute(
                sa.select(ur.c.role_id, sa.func.count().label("n"))
                .where(ur.c.role_id == role.role_id)
                .group_by(ur.c.role_id)
            ).all()
        }
    return RoleReadSerializer(
        {
            "role_id": role.role_id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_active": bool(role.is_active),
            "is_system_role": bool(role.is_system_role),
            "permission_codes": sorted(set(permission_codes)),
            "scope_codes": sorted(set(scope_codes)),
            "effective_scope": effective_scope,
            "operator_count": operator_counts.get(role.role_id, 0),
            "created_at": role.created_at,
            "updated_at": role.updated_at,
        }
    ).data


def _operator_counts_by_role(db):
    ur = UserRole.__table__
    return {
        row.role_id: row.n
        for row in db.execute(
            sa.select(ur.c.role_id, sa.func.count().label("n"))
            .group_by(ur.c.role_id)
        ).all()
    }


def _policy_codes_for_scope(db, scope):
    """Resolve a single scope value to the active access-policy code(s)."""
    if scope is None or scope == AccessScope.NONE.value:
        return []
    return list(
        db.execute(
            sa.select(AccessPolicy.code).where(
                AccessPolicy.scope == scope, AccessPolicy.is_active == sa.true()
            )
        ).scalars().all()
    )


_ADMIN_ROLE_PERMISSION = "iam.role.manage"


def _platform_admin_roles_other_than(db, exclude_role_id):
    rp = RolePermission.__table__
    perm = Permission.__table__
    role = Role.__table__
    return set(
        db.execute(
            sa.select(rp.c.role_id)
            .select_from(
                rp.join(perm, rp.c.permission_id == perm.c.permission_id).join(
                    role, rp.c.role_id == role.c.role_id
                )
            )
            .where(
                role.c.is_active == sa.true(),
                role.c.role_id != exclude_role_id,
                perm.c.code == _ADMIN_ROLE_PERMISSION,
            )
        ).scalars().all()
    )


def _guard_role_deactivation(db, role):
    """Reject deactivating the last active role that keeps platform role/rights
    administration available (system roles must never strand admin access)."""
    others = _platform_admin_roles_other_than(db, role.role_id)
    if not others:
        raise UnprocessableEntityError(
            f"Role {role.code} cannot be deactivated: it is the last active "
            "role granting platform administration.",
            {"is_active": "Required system administration must remain available."},
        )


def _slug_role_code(name):
    code = "".join(c if c.isalnum() else "_" for c in name.upper())
    while "__" in code:
        code = code.replace("__", "_")
    return code.strip("_")[:100]


def _normalize_role_payload(db, validated):
    """Merge the spec-friendly aliases (rights/scope/status) into the internal
    contract (permission_codes/access_policy_codes/is_active) and drop aliases."""
    payload = dict(validated)

    if "status" in payload and payload["status"] is not None:
        payload["is_active"] = payload["status"] == "ACTIVE"
    payload.pop("status", None)

    rights = payload.get("rights", [])
    permission_codes = payload.get("permission_codes", [])
    merged = list(dict.fromkeys(rights or permission_codes))
    payload["permission_codes"] = merged
    payload.pop("rights", None)

    policy_codes = payload.get("access_policy_codes", [])
    if not policy_codes:
        policy_codes = _policy_codes_for_scope(db, payload.get("scope"))
    payload["access_policy_codes"] = policy_codes
    payload.pop("scope", None)

    payload["code"] = payload.get("code") or ""
    return payload


def _parse_role_rights(db, data):
    """Resolve right codes (rights/permission_codes) and/or right_ids into a
    single canonical, deduplicated list of permission codes.

    Every supplied ID must belong to an active right (422 otherwise). Returns
    an empty list when the request body carries no rights.
    """
    codes = data.get("rights", data.get("permission_codes", []))
    if codes is None:
        codes = []
    if not isinstance(codes, list):
        raise UnprocessableEntityError(
            "Rights must be a list of permission codes.",
            {"rights": "Expected a list of codes."},
        )
    raw_ids = data.get("right_ids", [])
    if raw_ids:
        if not isinstance(raw_ids, list) or not all(isinstance(i, int) for i in raw_ids):
            raise UnprocessableEntityError(
                "right_ids must be a list of integer right IDs.",
                {"right_ids": "Expected a list of integer IDs."},
            )
        rows = db.execute(
            sa.select(Permission.permission_id, Permission.code).where(
                Permission.permission_id.in_(raw_ids),
                Permission.is_active == sa.true(),
            )
        ).all()
        by_id = {row.permission_id: row.code for row in rows}
        missing = [i for i in raw_ids if i not in by_id]
        if missing:
            raise UnprocessableEntityError(
                "Unknown or inactive right IDs.",
                {"right_ids": f"Unknown or inactive: {missing}"},
            )
        codes = list(codes) + [by_id[i] for i in raw_ids]
    return list(dict.fromkeys(c for c in codes if c and isinstance(c, str)))


def _validate_role_permissions(db, permission_codes):
    """Reject unknown or inactive rights before any mutation (422)."""
    if not permission_codes:
        return
    active = set(
        db.execute(
            sa.select(Permission.code).where(
                Permission.code.in_(permission_codes),
                Permission.is_active == sa.true(),
            )
        ).scalars().all()
    )
    invalid = [c for c in permission_codes if c not in active]
    if invalid:
        raise UnprocessableEntityError(
            "Role contains unknown or inactive rights.",
            {"permission_codes": f"Unknown or inactive: {', '.join(invalid)}"},
        )


def _validate_role_policies(db, access_policy_codes):
    if not access_policy_codes:
        return
    active = set(
        db.execute(
            sa.select(AccessPolicy.code).where(AccessPolicy.code.in_(access_policy_codes))
        ).scalars().all()
    )
    unknown = [c for c in access_policy_codes if c not in active]
    if unknown:
        raise UnprocessableEntityError(
            "Role references unknown access policies.",
            {"access_policy_codes": f"Unknown: {', '.join(unknown)}"},
        )


def _set_role_permissions(db, actor_user_id, role, permission_codes):
    db.execute(sa.delete(RolePermission).where(RolePermission.role_id == role.role_id))
    if not permission_codes:
        return
    perms = db.execute(
        sa.select(Permission).where(
            Permission.code.in_(permission_codes), Permission.is_active == sa.true()
        )
    ).scalars().all()
    for p in perms:
        db.add(RolePermission(role_id=role.role_id, permission_id=p.permission_id))


def _set_role_policies(db, actor_user_id, role, access_policy_codes):
    db.execute(sa.delete(RoleAccessPolicy).where(RoleAccessPolicy.role_id == role.role_id))
    if not access_policy_codes:
        return
    policies = db.execute(
        sa.select(AccessPolicy).where(
            AccessPolicy.code.in_(access_policy_codes), AccessPolicy.is_active == sa.true()
        )
    ).scalars().all()
    for p in policies:
        db.add(RoleAccessPolicy(role_id=role.role_id, access_policy_id=p.access_policy_id))


def _deref_enums(value):
    """Recursively stringify enum members so JSON serialization is safe."""
    import enum

    if isinstance(value, dict):
        return {k: _deref_enums(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deref_enums(i) for i in value]
    if isinstance(value, tuple):
        return [_deref_enums(i) for i in value]
    return value.value if isinstance(value, enum.Enum) else value