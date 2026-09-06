from enum import Enum

import sqlalchemy as sa

from common.db import Base


class AccessScope(str, Enum):
    NONE = "NONE"
    OWN = "OWN"
    ASSIGNED = "ASSIGNED"
    TEAM = "TEAM"
    DEPARTMENT = "DEPARTMENT"
    ALL = "ALL"


class PermissionEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class UserStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"
    SECURITY_LOCKED = "SECURITY_LOCKED"


class ActorType(str, Enum):
    INTERNAL_USER = "INTERNAL_USER"
    PORTAL_USER = "PORTAL_USER"
    SYSTEM = "SYSTEM"


class Department(Base):
    __tablename__ = "departments"

    department_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(100), nullable=False, unique=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    description = sa.Column(sa.String(255))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Team(Base):
    __tablename__ = "teams"

    team_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    department_id = sa.Column(sa.BigInteger, sa.ForeignKey("departments.department_id", ondelete="SET NULL"))
    name = sa.Column(sa.String(100), nullable=False, unique=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    description = sa.Column(sa.String(255))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class TeamMember(Base):
    __tablename__ = "team_members"

    team_member_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    team_id = sa.Column(sa.BigInteger, sa.ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    joined_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    left_at = sa.Column(sa.DateTime)
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))

    __table_args__ = (sa.UniqueConstraint("team_id", "user_id", name="uq_team_members"),)


class User(Base):
    __tablename__ = "users"

    user_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String(100), nullable=False, unique=True)
    email = sa.Column(sa.String(255), nullable=False, unique=True)
    first_name = sa.Column(sa.String(100), nullable=False)
    last_name = sa.Column(sa.String(100), nullable=False)
    phone = sa.Column(sa.String(50))
    department_id = sa.Column(sa.BigInteger, sa.ForeignKey("departments.department_id", ondelete="SET NULL"))
    team_id = sa.Column(sa.BigInteger, sa.ForeignKey("teams.team_id", ondelete="SET NULL"))
    status = sa.Column(sa.Enum(UserStatus), nullable=False, server_default=UserStatus.PENDING.value)
    last_login_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    def display_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class AuthenticationCredential(Base):
    __tablename__ = "authentication_credentials"

    credential_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    password_hash = sa.Column(sa.String(255), nullable=False)
    password_changed_at = sa.Column(sa.DateTime)
    password_expires_at = sa.Column(sa.DateTime)
    failed_login_attempts = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    locked_until = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_token_hash = sa.Column(sa.String(255), nullable=False, unique=True)
    ip_address = sa.Column(sa.String(45))
    user_agent = sa.Column(sa.String(500))
    expires_at = sa.Column(sa.DateTime, nullable=False)
    revoked_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Role(Base):
    __tablename__ = "roles"

    role_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(100), nullable=False, unique=True)
    code = sa.Column(sa.String(100), nullable=False, unique=True)
    description = sa.Column(sa.String(255))
    is_system_role = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("0"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Permission(Base):
    __tablename__ = "permissions"

    permission_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(150), nullable=False, unique=True)
    code = sa.Column(sa.String(150), nullable=False, unique=True)
    resource = sa.Column(sa.String(100), nullable=False)
    action = sa.Column(sa.String(100), nullable=False)
    description = sa.Column(sa.String(255))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_permission_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    role_id = sa.Column(sa.BigInteger, sa.ForeignKey("roles.role_id", ondelete="CASCADE"), nullable=False)
    permission_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("permissions.permission_id", ondelete="CASCADE"), nullable=False
    )
    granted_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions"),)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_role_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    role_id = sa.Column(sa.BigInteger, sa.ForeignKey("roles.role_id", ondelete="CASCADE"), nullable=False)
    assigned_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    assigned_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles"),)


class UserPermission(Base):
    __tablename__ = "user_permissions"

    user_permission_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    permission_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("permissions.permission_id", ondelete="CASCADE"), nullable=False
    )
    effect = sa.Column(sa.Enum(PermissionEffect), nullable=False, server_default=PermissionEffect.ALLOW.value)
    assigned_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    reason = sa.Column(sa.String(500))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (sa.UniqueConstraint("user_id", "permission_id", name="uq_user_permissions"),)


class AccessPolicy(Base):
    __tablename__ = "access_policies"

    access_policy_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(100), nullable=False, unique=True)
    code = sa.Column(sa.String(100), nullable=False, unique=True)
    scope = sa.Column(sa.Enum(AccessScope), nullable=False)
    description = sa.Column(sa.String(255))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class RoleAccessPolicy(Base):
    __tablename__ = "role_access_policies"

    role_access_policy_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    role_id = sa.Column(sa.BigInteger, sa.ForeignKey("roles.role_id", ondelete="CASCADE"), nullable=False)
    access_policy_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("access_policies.access_policy_id", ondelete="CASCADE"), nullable=False
    )
    granted_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (sa.UniqueConstraint("role_id", "access_policy_id", name="uq_role_access_policies"),)


class UserAccessPolicy(Base):
    __tablename__ = "user_access_policies"

    user_access_policy_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    access_policy_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("access_policies.access_policy_id", ondelete="CASCADE"), nullable=False
    )
    granted_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (sa.UniqueConstraint("user_id", "access_policy_id", name="uq_user_access_policies"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_log_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    actor_type = sa.Column(sa.Enum(ActorType), nullable=False, server_default=ActorType.INTERNAL_USER.value)
    actor_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    actor_portal_user_id = sa.Column(sa.BigInteger)
    action = sa.Column(sa.String(100), nullable=False)
    resource_type = sa.Column(sa.String(100))
    resource_id = sa.Column(sa.BigInteger)
    description = sa.Column(sa.String(500))
    ip_address = sa.Column(sa.String(45))
    user_agent = sa.Column(sa.String(500))
    metadata_ = sa.Column("metadata", sa.JSON)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token_hash = sa.Column(sa.String(255), nullable=False, unique=True)
    expires_at = sa.Column(sa.DateTime, nullable=False)
    consumed_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
