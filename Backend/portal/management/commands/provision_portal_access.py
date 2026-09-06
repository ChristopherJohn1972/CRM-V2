"""Management command: provision portal access for existing customers.

Every active CRM customer must have a path to the shared portal.  This
command finds customers without a linked portal user and provisions one.

Usage:
    python manage.py provision_portal_access                       # dry-run
    python manage.py provision_portal_access --apply               # provision
    python manage.py provision_portal_access --reset 0001          # reset password for account 0001
    python manage.py provision_portal_access --reset 0001 --new-password mypass  # set custom password
"""

import logging

import sqlalchemy as sa
from django.core.management.base import BaseCommand

from clients.models import Customer
from common.db import SessionLocal
from iam.services import hash_password
from portal.models import CustomerAccount, PortalAuthenticationCredential, PortalUser, PortalUserCustomer
from portal.services import provision_portal_access

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Provision portal access for existing customers without a portal user."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Actually write changes (default is dry-run).",
        )
        parser.add_argument(
            "--reset",
            type=str,
            default=None,
            help="Reset password for a portal user by account number (e.g. 0001).",
        )
        parser.add_argument(
            "--new-password",
            type=str,
            default=None,
            help="Custom password to set (used with --reset). Defaults to generated password.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        reset_account = options["reset"]
        new_password = options["new_password"]
        session = SessionLocal()

        if reset_account:
            try:
                self._reset_password(session, reset_account, new_password, apply)
            finally:
                session.close()
            return
        try:
            customers = session.execute(
                sa.select(Customer).where(Customer.deleted_at.is_(None))
            ).scalars().all()

            provisioned = 0
            skipped = 0
            failed = 0

            for customer in customers:
                existing_account = session.execute(
                    sa.select(CustomerAccount).where(
                        CustomerAccount.customer_id == customer.customer_id,
                    )
                ).scalar_one_or_none()

                if existing_account:
                    existing_link = session.execute(
                        sa.select(PortalUserCustomer).where(
                            PortalUserCustomer.customer_account_id == existing_account.customer_account_id,
                            PortalUserCustomer.is_active == sa.true(),
                        )
                    ).scalar_one_or_none()
                    if existing_link:
                        skipped += 1
                        continue

                try:
                    if not customer.email:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  SKIP {customer.customer_number}: no email address"
                            )
                        )
                        skipped += 1
                        continue

                    if apply:
                        portal_user, temp_password = provision_portal_access(
                            session, customer
                        )
                        session.commit()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  OK {customer.customer_number} -> portal user "
                                f"{portal_user.email} (initial password: {temp_password})"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"  WOULD provision {customer.customer_number} "
                            f"({customer.get_display_name()})"
                        )
                    provisioned += 1
                except Exception as exc:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f"  FAIL {customer.customer_number}: {exc}")
                    )
                    logger.exception("Portal provision failed for %s", customer.customer_number)
                    session.rollback()

            mode = "APPLIED" if apply else "DRY RUN"
            self.stdout.write(self.style.NOTICE(
                f"\n{mode}: {provisioned} provisioned, {skipped} skipped, {failed} failed "
                f"(out of {len(customers)} total customers)"
            ))
        finally:
            session.close()

    def _reset_password(self, session, account_number, custom_password, apply):
        customer_account = session.execute(
            sa.select(CustomerAccount).where(CustomerAccount.account_number == account_number)
        ).scalar_one_or_none()
        if customer_account is None:
            self.stdout.write(self.style.ERROR(f"Customer account '{account_number}' not found."))
            return

        link = session.execute(
            sa.select(PortalUserCustomer).where(
                PortalUserCustomer.customer_account_id == customer_account.customer_account_id,
                PortalUserCustomer.is_active == sa.true(),
            )
        ).scalar_one_or_none()
        if link is None:
            self.stdout.write(self.style.ERROR(f"No portal user linked to account '{account_number}'."))
            return

        portal_user = session.get(PortalUser, link.portal_user_id)
        if portal_user is None:
            self.stdout.write(self.style.ERROR(f"Portal user not found for account '{account_number}'."))
            return

        credential = session.execute(
            sa.select(PortalAuthenticationCredential).where(
                PortalAuthenticationCredential.portal_user_id == portal_user.portal_user_id
            )
        ).scalar_one_or_none()
        if credential is None:
            self.stdout.write(self.style.ERROR(f"No credential found for '{account_number}'."))
            return

        if custom_password:
            password_to_set = custom_password
        else:
            from portal.services import generate_temp_password
            password_to_set = generate_temp_password()

        if apply:
            credential.password_hash = hash_password(password_to_set)
            credential.failed_login_attempts = 0
            credential.locked_until = None
            from datetime import datetime, timezone, timedelta
            credential.password_changed_at = None
            credential.password_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
            session.commit()
            self.stdout.write(self.style.SUCCESS(
                f"  OK {account_number} ({portal_user.email}) -> password reset (new password: {password_to_set})"
            ))
        else:
            self.stdout.write(
                f"  WOULD reset password for {account_number} ({portal_user.email}) to: {password_to_set}"
            )
