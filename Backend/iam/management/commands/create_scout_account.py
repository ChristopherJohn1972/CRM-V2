"""
Management command: create_scout_account

Creates the APPLICATION_SCOUT role (if not present) and the scout evaluation
user with the specified password. The role is granted least-privilege
permissions matching the security specification.
"""

import secrets

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

SCOUT_USERNAME = "scout"
SCOUT_EMAIL = "scout@crm-v2.test"
SCOUT_ROLE_CODE = "APPLICATION_SCOUT"

# Least-privilege permissions for the Scout evaluation role
SCOUT_PERMISSIONS = [
    # Clients
    "clients.customer.read",
    "clients.customer.create",
    "clients.customer.update",
    "clients.contact.create",
    "clients.contact.update",
    "clients.relationship.create",
    "clients.relationship.read",
    "clients.address.write",
    # Activities
    "activities.activity.read",
    "activities.activity.create",
    "activities.activity.update",
    "activities.note.read",
    "activities.note.create",
    "activities.note.update",
    # Communications (read only)
    "communications.sms.read",
    "communications.email.read",
    "communications.call.read",
    # Documents
    "documents.document.read",
    "documents.document.create",
    "documents.document.download",
    # Accounting
    "accounting.summary.read",
    "accounting.transactions.read",
    # Customer360
    "customer360.view",
    # Quotes
    "quotes.quote.read",
    "quotes.quote.create",
    "quotes.quote.update",
    "quotes.quote.calculate",
    "quotes.quote.preview",
    "quotes.quote.download_pdf",
    # Sales Orders
    "sales_order.sales_order.read",
    "sales_order.sales_order.create",
    "sales_order.sales_order.update",
    "sales_order.sales_order.calculate",
    "sales_order.payment.read",
    "sales_order.receipt.read",
    # Campaigns
    "campaign.view",
    "campaign.create",
    "campaign.edit",
    # Leads
    "lead.view",
    "lead.create",
    "lead.edit",
    "lead.assign",
]


class Command(BaseCommand):
    help = "Create the Scout evaluation account with least-privilege role."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="Scout#$123",
            help="Password for the scout account (default: Scout#$123)",
        )
        parser.add_argument(
            "--email",
            default=SCOUT_EMAIL,
            help="Email for the scout account",
        )
        parser.add_argument(
            "--first-name",
            default="CRM",
            help="First name",
        )
        parser.add_argument(
            "--last-name",
            default="Scout",
            help="Last name",
        )
        parser.add_argument(
            "--regenerate-password",
            action="store_true",
            help="Generate a random password and print it (ignores --password)",
        )

    def handle(self, *args, **options):
        db = SessionLocal()
        try:
            # ── Step 1: Create or verify the APPLICATION_SCOUT role ──────
            role = db.execute(
                sa.select(Role).where(Role.code == SCOUT_ROLE_CODE)
            ).scalar_one_or_none()

            if role is None:
                role = Role(
                    name="Application Scout",
                    code=SCOUT_ROLE_CODE,
                    description="Evaluation-only role with least-privilege business access.",
                    is_system_role=False,
                    is_active=True,
                )
                db.add(role)
                db.flush()
                self.stdout.write(self.style.SUCCESS(f"Created role {SCOUT_ROLE_CODE} (role_id={role.role_id})"))
            else:
                self.stdout.write(self.style.WARNING(f"Role {SCOUT_ROLE_CODE} already exists (role_id={role.role_id})"))

            # ── Step 2: Grant permissions ───────────────────────────────
            existing_perms = {
                rp.permission_id
                for rp in db.execute(
                    sa.select(RolePermission).where(RolePermission.role_id == role.role_id)
                ).scalars().all()
            }

            granted = 0
            for perm_code in SCOUT_PERMISSIONS:
                perm = db.execute(
                    sa.select(Permission).where(Permission.code == perm_code)
                ).scalar_one_or_none()
                if perm is None:
                    self.stdout.write(self.style.WARNING(f"  Permission not found: {perm_code}"))
                    continue
                if perm.permission_id not in existing_perms:
                    db.add(RolePermission(role_id=role.role_id, permission_id=perm.permission_id))
                    granted += 1

            if granted:
                self.stdout.write(self.style.SUCCESS(f"Granted {granted} new permissions to {SCOUT_ROLE_CODE}"))

            # ── Step 3: Grant ALL scope ─────────────────────────────────
            policy = db.execute(
                sa.select(AccessPolicy).where(AccessPolicy.code == "GLOBAL_ALL")
            ).scalar_one_or_none()
            if policy:
                existing_policies = {
                    rap.access_policy_id
                    for rap in db.execute(
                        sa.select(RoleAccessPolicy).where(RoleAccessPolicy.role_id == role.role_id)
                    ).scalars().all()
                }
                if policy.access_policy_id not in existing_policies:
                    db.add(RoleAccessPolicy(role_id=role.role_id, access_policy_id=policy.access_policy_id))
                    self.stdout.write(self.style.SUCCESS(f"Granted GLOBAL_ALL scope to {SCOUT_ROLE_CODE}"))

            # ── Step 4: Create or update the scout user ─────────────────
            user = db.execute(
                sa.select(User).where(User.username == SCOUT_USERNAME)
            ).scalar_one_or_none()

            if options["regenerate_password"]:
                password = secrets.token_urlsafe(16)
            else:
                password = options["password"]

            if user is None:
                user = User(
                    username=SCOUT_USERNAME,
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
                        password_hash=hash_password(password),
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created user '{SCOUT_USERNAME}' (user_id={user.user_id})")
                )
            else:
                self.stdout.write(self.style.WARNING(f"User '{SCOUT_USERNAME}' already exists (user_id={user.user_id})"))
                # Update credential
                cred = db.execute(
                    sa.select(AuthenticationCredential).where(
                        AuthenticationCredential.user_id == user.user_id
                    )
                ).scalar_one_or_none()
                if cred:
                    cred.password_hash = hash_password(password)
                    self.stdout.write(self.style.SUCCESS("  Updated password hash"))
                else:
                    db.add(
                        AuthenticationCredential(
                            user_id=user.user_id,
                            password_hash=hash_password(password),
                        )
                    )
                    self.stdout.write(self.style.SUCCESS("  Created new credential"))

            # ── Step 5: Assign role ─────────────────────────────────────
            existing_role = db.execute(
                sa.select(UserRole).where(
                    UserRole.user_id == user.user_id,
                    UserRole.role_id == role.role_id,
                )
            ).scalar_one_or_none()
            if not existing_role:
                db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
                self.stdout.write(self.style.SUCCESS(f"Assigned {SCOUT_ROLE_CODE} to {SCOUT_USERNAME}"))

            # ── Step 6: Grant user-level ALL scope ──────────────────────
            if policy:
                existing_user_policy = db.execute(
                    sa.select(UserAccessPolicy).where(
                        UserAccessPolicy.user_id == user.user_id,
                        UserAccessPolicy.access_policy_id == policy.access_policy_id,
                    )
                ).scalar_one_or_none()
                if not existing_user_policy:
                    db.add(UserAccessPolicy(user_id=user.user_id, access_policy_id=policy.access_policy_id))
                    self.stdout.write(self.style.SUCCESS(f"Granted GLOBAL_ALL scope to {SCOUT_USERNAME}"))

            db.commit()

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS(f"Scout account ready:"))
            self.stdout.write(self.style.SUCCESS(f"  Username:  {SCOUT_USERNAME}"))
            self.stdout.write(self.style.SUCCESS(f"  Email:     {options['email']}"))
            self.stdout.write(self.style.SUCCESS(f"  Password:  {password}"))
            self.stdout.write(self.style.SUCCESS(f"  Role:      {SCOUT_ROLE_CODE}"))
            self.stdout.write(self.style.SUCCESS(f"  Scope:     ALL (GLOBAL_ALL)"))
            self.stdout.write(self.style.SUCCESS("=" * 60))
            if options["regenerate_password"]:
                self.stdout.write(self.style.WARNING("  ^ SAVE THIS PASSWORD — it will not be shown again"))

        finally:
            db.close()
