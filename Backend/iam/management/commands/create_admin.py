import sqlalchemy as sa
from django.core.management.base import BaseCommand, CommandError

from common.db import SessionLocal
from iam.models import (
    AccessPolicy,
    AuthenticationCredential,
    Permission,
    Role,
    RoleAccessPolicy,
    RolePermission,
    User,
    UserAccessPolicy,
    UserRole,
)
from iam.services import hash_password

ALL_PERMISSIONS_QUERY = "ALL_PERMISSIONS"


class Command(BaseCommand):
    help = "Create an internal admin user with full access (bcrypt-hashed credential)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--first-name", default="Admin")
        parser.add_argument("--last-name", default="User")

    def handle(self, *args, **options):
        db = SessionLocal()
        try:
            existing = db.execute(
                sa.select(User).where(User.username == options["username"])
            ).scalar_one_or_none()
            if existing:
                raise CommandError("A user with this username already exists.")

            user = User(
                username=options["username"],
                email=options["email"],
                first_name=options["first_name"],
                last_name=options["last_name"],
                status="ACTIVE",
            )
            db.add(user)
            db.flush()

            db.add(
                AuthenticationCredential(
                    user_id=user.user_id,
                    password_hash=hash_password(options["password"]),
                )
            )

            role = db.execute(
                sa.select(Role).where(Role.code == "SUPER_ADMIN")
            ).scalar_one_or_none()
            if role is None:
                role = Role(
                    name="Super Admin",
                    code="SUPER_ADMIN",
                    description="System administrator with full access",
                    is_system_role=True,
                    is_active=True,
                )
                db.add(role)
                db.flush()
            db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

            policy = db.execute(
                sa.select(AccessPolicy).where(AccessPolicy.code == "GLOBAL_ALL")
            ).scalar_one_or_none()
            if policy is None:
                policy = AccessPolicy(
                    name="Global All",
                    code="GLOBAL_ALL",
                    scope="ALL",
                    description="Unrestricted access to all records",
                    is_active=True,
                )
                db.add(policy)
                db.flush()
            db.add(UserAccessPolicy(user_id=user.user_id, access_policy_id=policy.access_policy_id))

            permissions = db.execute(
                sa.select(Permission).where(Permission.is_active == sa.true())
            ).scalars().all()
            existing_links = {
                (rp.role_id, rp.permission_id)
                for rp in db.execute(
                    sa.select(RolePermission).where(
                        RolePermission.role_id == role.role_id
                    )
                ).scalars().all()
            }
            for permission in permissions:
                if (role.role_id, permission.permission_id) not in existing_links:
                    db.add(
                        RolePermission(
                            role_id=role.role_id, permission_id=permission.permission_id
                        )
                    )

            db.commit()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created admin user '{user.username}' (user_id={user.user_id}) with role '{role.code}'."
                )
            )
        finally:
            db.close()
