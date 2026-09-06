import secrets

import sqlalchemy as sa
from django.core.management.base import BaseCommand, CommandError

from common.db import SessionLocal
from iam.models import (
    AuthenticationCredential,
    Role,
    RoleAccessPolicy,
    User,
    UserAccessPolicy,
    UserRole,
)
from iam.services import hash_password

# Backend Specification sections 22-24: development/test identities used to
# validate the Rights & Authorization Matrix. Emails use the reserved test
# domain *.test. Credentials are generated at runtime and printed once so they
# never live in source code or migrations.
TEST_ACCOUNTS = [
    {
        "username": "test.admin",
        "email": "test.admin@crm-v2.test",
        "first_name": "Test",
        "last_name": "System Admin",
        "role_code": "SYSTEM_ADMINISTRATOR",
    },
    {
        "username": "test.manager",
        "email": "test.manager@crm-v2.test",
        "first_name": "Test",
        "last_name": "CRM Manager",
        "role_code": "CRM_MANAGER",
    },
    {
        "username": "test.accountmanager",
        "email": "test.accountmanager@crm-v2.test",
        "first_name": "Test",
        "last_name": "Account Manager",
        "role_code": "ACCOUNT_MANAGER",
    },
    {
        "username": "test.support",
        "email": "test.support@crm-v2.test",
        "first_name": "Test",
        "last_name": "Customer Service",
        "role_code": "CUSTOMER_SERVICE",
    },
]


class Command(BaseCommand):
    help = "Create the four test accounts (roles must be seeded via 005)."

    def handle(self, *args, **options):
        db = SessionLocal()
        try:
            for account in TEST_ACCOUNTS:
                role = db.execute(
                    sa.select(Role).where(Role.code == account["role_code"])
                ).scalar_one_or_none()
                if role is None:
                    raise CommandError(
                        f"Role {account['role_code']} is not seeded. "
                        "Run deploy/apply_sql.py deploy/sql/005_seed_portal_test_roles.sql first."
                    )

                existing = db.execute(
                    sa.select(User).where(User.username == account["username"])
                ).scalar_one_or_none()
                if existing:
                    self.stdout.write(
                        self.style.WARNING(f"User {account['username']} already exists; skipping.")
                    )
                    continue

                password = secrets.token_urlsafe(16)
                user = User(
                    username=account["username"],
                    email=account["email"],
                    first_name=account["first_name"],
                    last_name=account["last_name"],
                    status="ACTIVE",
                )
                db.add(user)
                db.flush()
                db.add(
                    AuthenticationCredential(
                        user_id=user.user_id,
                        password_hash=hash_password(password),
                    )
                )
                db.add(UserRole(user_id=user.user_id, role_id=role.role_id))

                policies = db.execute(
                    sa.select(RoleAccessPolicy).where(
                        RoleAccessPolicy.role_id == role.role_id
                    )
                ).scalars().all()
                for rp in policies:
                    db.add(
                        UserAccessPolicy(
                            user_id=user.user_id, access_policy_id=rp.access_policy_id
                        )
                    )

                db.commit()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {user.username} <{user.email}> "
                        f"(user_id={user.user_id}, role={role.code})"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(f"  temporary password: {password}")
                )
        finally:
            db.close()