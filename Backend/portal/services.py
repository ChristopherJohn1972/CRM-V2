import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import sqlalchemy as sa
from django.conf import settings

from common.exceptions import APIError, ValidationError_
from iam.services import hash_password, verify_password
from portal.enums import (
    CustomerAccountStatus,
    PORTAL_RELATIONSHIP_RANK,
    PortalPermissionEffect,
    PortalRelationshipType,
    PortalUserStatus,
)
from portal.models import (
    CustomerAccount,
    PortalAuthenticationCredential,
    PortalPasswordResetToken,
    PortalPermission,
    PortalSession,
    PortalUser,
    PortalUserCustomer,
    PortalUserPermission,
)

logger = logging.getLogger(__name__)


def _lockout_attempts():
    return getattr(settings, "PORTAL_LOCKOUT_ATTEMPTS", 5)


def _lockout_minutes():
    return getattr(settings, "PORTAL_LOCKOUT_MINUTES", 15)


RESET_TOKEN_TTL_MINUTES = 30
PASSWORD_EXPIRY_DAYS = 90


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_portal_access_token(portal_user_id, portal_session_id) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(portal_user_id),
        "sid": str(portal_session_id),
        "typ": "portal",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_portal_access_token(token: str):
    from iam.services import decode_access_token

    payload = decode_access_token(token)
    if payload.get("typ", "") != "portal":
        raise APIError("Unsupported token type for this endpoint.", status_code=401, error_code="token_invalid")
    return payload


def generate_temp_password(length=16) -> str:
    """Cryptographically random onboarding password that must be changed."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def validate_password_policy(password: str):
    errors = {}
    if not password or len(password) < 10:
        errors["password"] = "Password must be at least 10 characters long."
    company_name = getattr(settings, "PORTAL_COMPANY_NAME", "CRM V2").strip().lower()
    if password and password.strip().lower() == company_name:
        errors["password"] = "Company name is not a valid password."
    if password and len(set(password)) < 4:
        errors["password"] = "Password must include at least 4 distinct characters."
    if errors:
        raise ValidationError_("Password does not meet the security policy.", errors)


def effective_relationship_rank(session, portal_user_id, customer_account_id):
    link = session.execute(
        sa.select(PortalUserCustomer).where(
            PortalUserCustomer.portal_user_id == portal_user_id,
            PortalUserCustomer.customer_account_id == customer_account_id,
            PortalUserCustomer.is_active == sa.true(),
        )
    ).scalar_one_or_none()
    if link is None:
        return None
    return PORTAL_RELATIONSHIP_RANK.get(link.role, 0)


class PortalAuthenticationService:
    """Login, temporary credentials, password lifecycle and lockout for clients."""

    @staticmethod
    def find_by_login(session, email: str, account_number: str):
        """Find a portal user by email linked to the given customer account.

        Returns (portal_user, customer_account) or (None, None).
        """
        customer_account = session.execute(
            sa.select(CustomerAccount).where(
                CustomerAccount.account_number == account_number,
                CustomerAccount.status == CustomerAccountStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        if customer_account is None:
            logger.warning(f"Portal find_by_login: No customer_account found for account_number={account_number}")
            return None, None

        link = session.execute(
            sa.select(PortalUserCustomer).where(
                PortalUserCustomer.customer_account_id == customer_account.customer_account_id,
                PortalUserCustomer.is_active == sa.true(),
            )
        ).scalar_one_or_none()
        if link is None:
            logger.warning(f"Portal find_by_login: No portal_user_customer link for customer_account_id={customer_account.customer_account_id}")
            return None, customer_account

        portal_user = session.get(PortalUser, link.portal_user_id)
        if portal_user is None or portal_user.email.lower() != email.lower():
            logger.warning(f"Portal find_by_login: Portal user mismatch. user_email={portal_user.email if portal_user else None}, input_email={email}")
            return None, customer_account

        return portal_user, customer_account

    @staticmethod
    def get_credential(session, portal_user_id):
        return session.execute(
            sa.select(PortalAuthenticationCredential).where(
                PortalAuthenticationCredential.portal_user_id == portal_user_id
            )
        ).scalar_one_or_none()

    @classmethod
    def issue_temp_credential(cls, session, portal_user, initial_password=None):
        """Set a temporary onboarding password (password must be changed on login).

        If *initial_password* is provided it is used instead of a random one.
        """
        temp = initial_password if initial_password else generate_temp_password()
        credential = cls.get_credential(session, portal_user.portal_user_id)
        if credential is None:
            credential = PortalAuthenticationCredential(portal_user_id=portal_user.portal_user_id)
            session.add(credential)
        credential.password_hash = hash_password(temp)
        credential.password_changed_at = None
        credential.password_expires_at = _utcnow() + timedelta(days=7)
        credential.failed_login_attempts = 0
        credential.locked_until = None
        session.flush()
        return temp

    @classmethod
    def must_change_password(cls, session, portal_user_id) -> bool:
        credential = cls.get_credential(session, portal_user_id)
        if credential is None:
            return True
        if credential.password_changed_at is None:
            return True
        if credential.password_expires_at and credential.password_expires_at <= _utcnow():
            return True
        return False

    @classmethod
    def login(cls, session, email: str, account_number: str, password: str):
        portal_user, customer_account = cls.find_by_login(session, email, account_number)
        if portal_user is None:
            logger.warning(f"Portal login: find_by_login returned portal_user=None, customer_account={'found' if customer_account else 'None'}")
            raise APIError("Invalid email or password.", status_code=401, error_code="invalid_credentials")
        if customer_account is None:
            logger.warning(f"Portal login: customer_account is None")
            raise APIError("Account not found or inactive.", status_code=401, error_code="account_not_found")

        credential = cls.get_credential(session, portal_user.portal_user_id)
        if credential is not None and credential.locked_until and credential.locked_until > _utcnow():
            logger.warning(f"Portal login: account locked")
            raise APIError("Account temporarily locked.", status_code=403, error_code="account_locked")

        if credential is None or not verify_password(password, credential.password_hash):
            logger.warning(f"Portal login: password mismatch. credential={'found' if credential else 'None'}")
            if credential is not None:
                cls._increment_failed_attempts(session, credential)
                session.commit()
            raise APIError("Invalid email or password.", status_code=401, error_code="invalid_credentials")

        if portal_user.status not in (PortalUserStatus.ACTIVE.value, PortalUserStatus.PENDING.value):
            raise APIError("Portal account is not active.", status_code=403, error_code="account_inactive")

        # First login with the issued temporary credential proves possession of
        # the onboarding password, so the account moves PENDING -> ACTIVE and the
        # client immediately sets a permanent password.
        if portal_user.status == PortalUserStatus.PENDING.value:
            portal_user.status = PortalUserStatus.ACTIVE.value

        credential.failed_login_attempts = 0
        credential.locked_until = None
        portal_user.last_login_at = _utcnow()
        session.flush()
        return portal_user, customer_account, cls.must_change_password(session, portal_user.portal_user_id)

    @staticmethod
    def _increment_failed_attempts(session, credential):
        credential.failed_login_attempts += 1
        if credential.failed_login_attempts >= _lockout_attempts():
            credential.locked_until = _utcnow() + timedelta(minutes=_lockout_minutes())

    @classmethod
    def change_password(cls, session, portal_user_id, current_password, new_password):
        credential = cls.get_credential(session, portal_user_id)
        if credential is None or not verify_password(current_password, credential.password_hash):
            raise APIError("Current password is incorrect.", status_code=400, error_code="current_password_incorrect")
        validate_password_policy(new_password)
        if current_password == new_password:
            raise ValidationError_("New password must differ from the current password.",
                                   {"new_password": "New password must differ from the current password."})
        credential.password_hash = hash_password(new_password)
        credential.password_changed_at = _utcnow()
        credential.password_expires_at = _utcnow() + timedelta(days=PASSWORD_EXPIRY_DAYS)
        credential.failed_login_attempts = 0
        credential.locked_until = None
        session.flush()
        return credential

    @classmethod
    def setup_password(cls, session, portal_user_id, new_password):
        credential = cls.get_credential(session, portal_user_id)
        if credential is None:
            raise APIError("No credential found.", status_code=400, error_code="no_credential")
        validate_password_policy(new_password)
        credential.password_hash = hash_password(new_password)
        credential.password_changed_at = _utcnow()
        credential.password_expires_at = _utcnow() + timedelta(days=PASSWORD_EXPIRY_DAYS)
        credential.failed_login_attempts = 0
        credential.locked_until = None
        session.flush()
        return credential

    @classmethod
    def create_reset_token(cls, session, portal_user_id) -> str:
        token = secrets.token_urlsafe(32)
        session.add(
            PortalPasswordResetToken(
                portal_user_id=portal_user_id,
                token_hash=_token_hash(token),
                expires_at=_utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
            )
        )
        session.flush()
        return token

    @classmethod
    def reset_password(cls, session, token, new_password):
        validate_password_policy(new_password)
        row = session.execute(
            sa.select(PortalPasswordResetToken).where(
                PortalPasswordResetToken.token_hash == _token_hash(token)
            )
        ).scalar_one_or_none()
        if row is None:
            raise APIError("Invalid password reset token.", status_code=400, error_code="invalid_reset_token")
        if row.consumed_at is not None:
            raise APIError("Password reset token has already been used.", status_code=400, error_code="reset_token_used")
        if row.expires_at <= _utcnow():
            raise APIError("Password reset token has expired.", status_code=400, error_code="reset_token_expired")

        portal_user = session.get(PortalUser, row.portal_user_id)
        if portal_user is None or portal_user.status == PortalUserStatus.DEACTIVATED.value:
            raise APIError("Portal account is not active.", status_code=403, error_code="account_inactive")

        credential = cls.get_credential(session, portal_user.portal_user_id)
        if credential is None:
            credential = PortalAuthenticationCredential(portal_user_id=portal_user.portal_user_id)
            session.add(credential)
        credential.password_hash = hash_password(new_password)
        credential.password_changed_at = _utcnow()
        credential.password_expires_at = _utcnow() + timedelta(days=PASSWORD_EXPIRY_DAYS)
        credential.failed_login_attempts = 0
        credential.locked_until = None
        row.consumed_at = _utcnow()
        session.flush()
        return portal_user


class PortalSessionService:
    @staticmethod
    def create_session(session, portal_user_id, ip_address, user_agent) -> PortalSession:
        token = secrets.token_urlsafe(32)
        portal_session = PortalSession(
            portal_user_id=portal_user_id,
            session_token_hash=_token_hash(token),
            ip_address=ip_address,
            user_agent=(user_agent or "")[:500],
            expires_at=_utcnow() + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES),
        )
        session.add(portal_session)
        session.flush()
        return portal_session, token

    @staticmethod
    def revoke(session, session_id):
        portal_session = session.get(PortalSession, session_id)
        if portal_session and portal_session.revoked_at is None:
            portal_session.revoked_at = _utcnow()


def _to_enum(value, enum_cls, field):
    if isinstance(value, enum_cls):
        return value.value
    if isinstance(value, str):
        return value
    raise ValidationError_(f"{field} is not a valid value.", {field: "Invalid value."})


class PortalUserService:
    @staticmethod
    def create(session, *, email, first_name, last_name, phone=None, customer_account_id=None, role=None) -> tuple:
        """Create a PENDING portal user with temporary onboarding credentials.

        Returns (PortalUser, temp_password). The caller reports the temporary
        password through the out-of-band channel; it is never stored in plaintext.
        """
        email = (email or "").strip().lower()
        if not email or not first_name or not last_name:
            raise ValidationError_("email, first_name and last_name are required.")
        existing = session.execute(
            sa.select(PortalUser).where(PortalUser.email == email)
        ).scalar_one_or_none()
        if existing:
            raise ValidationError_("A portal user with that email already exists.",
                                   {"email": "Email already in use."})

        portal_user = PortalUser(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            status=PortalUserStatus.PENDING.value,
        )
        session.add(portal_user)
        session.flush()
        temp = PortalAuthenticationService.issue_temp_credential(session, portal_user)

        if customer_account_id:
            session.add(
                PortalUserCustomer(
                    portal_user_id=portal_user.portal_user_id,
                    customer_account_id=int(customer_account_id),
                    role=_to_enum(role or "CONTACT", PortalRelationshipType, "role"),
                    is_primary=True,
                    is_active=True,
                )
            )
        session.flush()
        return portal_user, temp

    @staticmethod
    def set_status(session, portal_user, status):
        status = _to_enum(status, PortalUserStatus, "status")
        portal_user.status = status
        session.flush()
        return portal_user


def provision_portal_access(session, customer, initial_password=None) -> tuple:
    """Auto-provision portal access for a customer.

    Creates:
    1. A customer_account linking the customer to their account_number
    2. A portal user with the customer's email as the login identifier
    3. A link between the portal user and the customer account (OWNER role)

    The initial_password is a generated credential that must be changed on first login.
    Returns (portal_user, temp_password). Returns (None, None) if provisioning
    fails due to a constraint violation (e.g. duplicate email).
    """
    from sqlalchemy.exc import IntegrityError

    email = (customer.email or "").strip().lower()
    if not email:
        raise ValidationError_("Customer must have an email address for portal access.",
                               {"email": "Email is required for portal provisioning."})

    # Step 1: Ensure customer_account exists
    account_number = customer.customer_number
    customer_account = session.execute(
        sa.select(CustomerAccount).where(CustomerAccount.account_number == account_number)
    ).scalar_one_or_none()

    if customer_account is None:
        customer_account = CustomerAccount(
            customer_id=customer.customer_id,
            account_number=account_number,
            status=CustomerAccountStatus.ACTIVE.value,
        )
        session.add(customer_account)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            return None, None

    # Step 2: Create portal user
    if customer.is_individual:
        first_name = customer.first_name or ""
        last_name = customer.last_name or ""
        if not first_name and customer.legal_name:
            parts = customer.legal_name.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    else:
        first_name = customer.legal_name or ""
        last_name = ""

    existing = session.execute(
        sa.select(PortalUser).where(PortalUser.email == email)
    ).scalar_one_or_none()
    if existing:
        portal_user = existing
    else:
        portal_user = PortalUser(
            email=email,
            first_name=first_name or "Customer",
            last_name=last_name or "",
            phone=customer.phone,
            status=PortalUserStatus.PENDING.value,
        )
        session.add(portal_user)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            return None, None

    # Step 3: Link portal user to customer account
    existing_link = session.execute(
        sa.select(PortalUserCustomer).where(
            PortalUserCustomer.portal_user_id == portal_user.portal_user_id,
            PortalUserCustomer.customer_account_id == customer_account.customer_account_id,
        )
    ).scalar_one_or_none()

    if existing_link is None:
        session.add(
            PortalUserCustomer(
                portal_user_id=portal_user.portal_user_id,
                customer_account_id=customer_account.customer_account_id,
                role=PortalRelationshipType.OWNER.value,
                is_primary=True,
                is_active=True,
            )
        )

    # Step 4: Issue temporary credential
    pwd = initial_password if initial_password else None
    temp = PortalAuthenticationService.issue_temp_credential(session, portal_user, initial_password=pwd)

    session.flush()
    return portal_user, temp


class PortalCustomerAccessService:
    """Manage which customer accounts a portal user is explicitly linked to."""

    @staticmethod
    def link(session, portal_user_id, customer_account_id, role="CONTACT", is_primary=False, is_active=True):
        role = _to_enum(role, PortalRelationshipType, "role")
        link = session.execute(
            sa.select(PortalUserCustomer).where(
                PortalUserCustomer.portal_user_id == portal_user_id,
                PortalUserCustomer.customer_account_id == customer_account_id,
            )
        ).scalar_one_or_none()
        if link is None:
            link = PortalUserCustomer(
                portal_user_id=portal_user_id,
                customer_account_id=customer_account_id,
                role=role,
                is_primary=bool(is_primary),
                is_active=bool(is_active),
            )
            session.add(link)
        else:
            link.role = role
            link.is_primary = bool(is_primary)
            link.is_active = bool(is_active)

        if is_primary:
            session.execute(
                sa.update(PortalUserCustomer)
                .where(
                    PortalUserCustomer.portal_user_id == portal_user_id,
                    PortalUserCustomer.customer_account_id != customer_account_id,
                )
                .values(is_primary=False)
            )
        session.flush()
        return link

    @staticmethod
    def deactivate(session, portal_user_id, customer_account_id):
        link = session.execute(
            sa.select(PortalUserCustomer).where(
                PortalUserCustomer.portal_user_id == portal_user_id,
                PortalUserCustomer.customer_account_id == customer_account_id,
            )
        ).scalar_one_or_none()
        if link is None:
            raise APIError("Customer account is not linked to this portal user.", status_code=404, error_code="not_found")
        link.is_active = False
        link.is_primary = False
        session.flush()
        return link

    @staticmethod
    def set_primary(session, portal_user_id, customer_account_id):
        link = PortalCustomerAccessService.link(
            session, portal_user_id, customer_account_id, is_primary=True, is_active=True
        )
        return link


class PortalPermissionService:
    @staticmethod
    def grant(session, portal_user_id, permission_code, effect="ALLOW"):
        effect = effect if isinstance(effect, str) else effect.value
        if effect not in ("ALLOW", "DENY"):
            raise ValidationError_("effect must be ALLOW or DENY.", {"effect": "Invalid effect."})
        permission = session.execute(
            sa.select(PortalPermission).where(
                PortalPermission.code == permission_code,
                PortalPermission.is_active == sa.true(),
            )
        ).scalar_one_or_none()
        if permission is None:
            raise ValidationError_(f"Unknown portal permission: {permission_code}",
                                   {"permission_code": "Unknown permission code."})
        row = session.execute(
            sa.select(PortalUserPermission).where(
                PortalUserPermission.portal_user_id == portal_user_id,
                PortalUserPermission.portal_permission_id == permission.portal_permission_id,
            )
        ).scalar_one_or_none()
        if row is None:
            row = PortalUserPermission(
                portal_user_id=portal_user_id,
                portal_permission_id=permission.portal_permission_id,
                effect=effect,
            )
            session.add(row)
        else:
            row.effect = effect
        session.flush()
        return row

    @staticmethod
    def revoke(session, portal_user_id, permission_code):
        permission = session.execute(
            sa.select(PortalPermission).where(PortalPermission.code == permission_code)
        ).scalar_one_or_none()
        row = session.execute(
            sa.select(PortalUserPermission).where(
                PortalUserPermission.portal_user_id == portal_user_id,
                PortalUserPermission.portal_permission_id == permission.portal_permission_id,
            )
        ).scalar_one_or_none()
        if row is not None:
            session.delete(row)
            session.flush()

    @staticmethod
    def effective_permissions(session, portal_user_id) -> list:
        perm = PortalPermission.__table__
        up = PortalUserPermission.__table__
        rows = session.execute(
            sa.select(perm.c.code, up.c.effect)
            .select_from(up.join(perm, up.c.portal_permission_id == perm.c.portal_permission_id))
            .where(up.c.portal_user_id == portal_user_id, perm.c.is_active == sa.true())
        ).fetchall()
        allowed = set()
        denied = set()
        for code, effect in rows:
            if effect == "DENY":
                denied.add(code)
            else:
                allowed.add(code)
        return sorted(allowed - denied)


class PortalAuthorizationService:
    """Enforce the portal boundary: permission + active customer account link + role rank."""

    @staticmethod
    def authorize(session, principal, permission_code, customer_account_id=None, min_relationship=None, request=None):
        if principal is None or getattr(principal, "kind", None) != "portal":
            return False
        if not principal.has_permission(permission_code):
            return False
        if customer_account_id is not None and customer_account_id not in principal.customer_account_ids:
            return False
        if min_relationship:
            from portal.enums import PORTAL_RELATIONSHIP_RANK
            rank = PORTAL_RELATIONSHIP_RANK.get(min_relationship, 0)
            effective = principal.relationship_rank(customer_account_id) if customer_account_id is not None else 0
            if effective < rank:
                return False
        return True

    @staticmethod
    def authorize_or_deny(session, principal, permission_code, customer_account_id=None, min_relationship=None, request=None):
        from common.exceptions import PermissionDeniedError

        if not PortalAuthorizationService.authorize(
            session, principal, permission_code, customer_account_id, min_relationship, request
        ):
            raise PermissionDeniedError("Portal access denied.")
        return True


# ---------------------------------------------------------------------------
# Sequence helper
# ---------------------------------------------------------------------------

def _next_sequence_value(session, bucket: str, prefix: str, year: int) -> str:
    """Thread-safe sequence via SELECT ... FOR UPDATE."""
    row = session.execute(
        sa.text("SELECT `last_value`, `seq_year` FROM `portal_sequences` WHERE bucket = :b FOR UPDATE"),
        {"b": bucket},
    ).fetchone()
    if row is None:
        raise APIError(f"Unknown sequence bucket: {bucket}", status_code=500, error_code="internal_error")

    current_year, current_val = int(row[1]), int(row[0])
    if current_year != year:
        new_val = 1
        session.execute(
            sa.text("UPDATE `portal_sequences` SET `last_value` = 1, `seq_year` = :y WHERE bucket = :b"),
            {"y": year, "b": bucket},
        )
    else:
        new_val = current_val + 1
        session.execute(
            sa.text("UPDATE `portal_sequences` SET `last_value` = :v WHERE bucket = :b"),
            {"v": new_val, "b": bucket},
        )
    return f"{prefix}-{year}-{new_val:06d}"


# ---------------------------------------------------------------------------
# MomentumService — computed from qualifying payments, no ledger
# ---------------------------------------------------------------------------

class MomentumService:
    """Calculate Momentum from confirmed qualifying payments.

    Momentum = FLOOR(total_qualifying / 1000)
    Remainder = total_qualifying MOD 1000
    Next      = 1000 - remainder  (or 0 if remainder == 0)
    """

    QUALIFYING_STATUSES = ("CONFIRMED",)

    @classmethod
    def get_qualifying_total(cls, session, customer_id, date_from=None, date_to=None) -> float:
        from portal.models import Payment

        conditions = [
            Payment.customer_id == customer_id,
            Payment.status.in_(cls.QUALIFYING_STATUSES),
        ]
        if date_from:
            conditions.append(Payment.payment_date >= date_from)
        if date_to:
            conditions.append(Payment.payment_date <= date_to)

        result = session.execute(
            sa.select(sa.func.coalesce(sa.func.sum(Payment.amount), 0.0)).where(sa.and_(*conditions))
        ).scalar()
        return float(result)

    @classmethod
    def calculate_momentum(cls, session, customer_id) -> int:
        total = cls.get_qualifying_total(session, customer_id)
        return int(total // 1000)

    @classmethod
    def calculate_remainder(cls, session, customer_id) -> float:
        total = cls.get_qualifying_total(session, customer_id)
        return total % 1000

    @classmethod
    def calculate_next_momentum_requirement(cls, session, customer_id) -> float:
        remainder = cls.calculate_remainder(session, customer_id)
        if remainder == 0:
            return 0.0
        return 1000.0 - remainder

    @classmethod
    def get_summary(cls, session, customer_id) -> dict:
        total = cls.get_qualifying_total(session, customer_id)
        momentum = int(total // 1000)
        remainder = total % 1000
        next_required = 0.0 if remainder == 0 else 1000.0 - remainder
        return {
            "total_qualifying": total,
            "momentum": momentum,
            "remainder": remainder,
            "next_momentum_required": next_required,
            "never_expires": True,
        }

    @classmethod
    def get_payment_summary(cls, session, customer_id, date_from=None, date_to=None) -> dict:
        total = cls.get_qualifying_total(session, customer_id, date_from, date_to)
        momentum = int(total // 1000)
        remainder = total % 1000
        return {
            "total_qualifying": total,
            "momentum": momentum,
            "remainder": remainder,
        }


# ---------------------------------------------------------------------------
# ComplaintService
# ---------------------------------------------------------------------------

class ComplaintService:
    """Create, track and manage complaints with timeline."""

    @staticmethod
    def create(session, *, customer_id, portal_user_id=None, subject, category=None,
               description=None, priority="MEDIUM", preferred_contact="PORTAL") -> "Complaint":
        from datetime import datetime

        from portal.models import Complaint

        year = datetime.utcnow().year
        complaint_number = _next_sequence_value(session, "COMPLAINT", "CMP", year)

        complaint = Complaint(
            customer_id=customer_id,
            portal_user_id=portal_user_id,
            complaint_number=complaint_number,
            subject=subject,
            category=category,
            description=description,
            priority=priority,
            status="SUBMITTED",
            preferred_contact=preferred_contact,
        )
        session.add(complaint)
        session.flush()

        _record_complaint_status(session, complaint.complaint_id, None, "SUBMITTED",
                                 changed_by=portal_user_id, changer_type="PORTAL_USER",
                                 note="Complaint submitted")
        return complaint

    @staticmethod
    def add_message(session, complaint_id, *, sender_type, portal_user_id=None,
                    user_id=None, message: str):
        from portal.models import ComplaintMessage

        msg = ComplaintMessage(
            complaint_id=complaint_id,
            portal_user_id=portal_user_id,
            user_id=user_id,
            sender_type=sender_type,
            message=message,
        )
        session.add(msg)
        session.flush()
        return msg

    @staticmethod
    def add_attachment(session, complaint_id, *, file_name, storage_key,
                       uploaded_by=None, uploader_type="PORTAL_USER",
                       complaint_message_id=None, mime_type=None, size_bytes=None):
        from portal.models import ComplaintAttachment

        att = ComplaintAttachment(
            complaint_id=complaint_id,
            complaint_message_id=complaint_message_id,
            file_name=file_name,
            storage_key=storage_key,
            uploaded_by=uploaded_by,
            uploader_type=uploader_type,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        session.add(att)
        session.flush()
        return att

    @staticmethod
    def update_status(session, complaint_id, new_status, changed_by, changer_type, note=None):
        from portal.models import Complaint

        complaint = session.get(Complaint, complaint_id)
        if complaint is None:
            raise APIError("Complaint not found.", status_code=404, error_code="not_found")
        old_status = complaint.status
        complaint.status = new_status
        _record_complaint_status(session, complaint_id, old_status, new_status,
                                 changed_by=changed_by, changer_type=changer_type, note=note)
        session.flush()
        return complaint

    @staticmethod
    def get_timeline(session, complaint_id) -> list:
        from portal.models import ComplaintMessage, ComplaintStatusHistory

        status_rows = session.execute(
            sa.select(ComplaintStatusHistory)
            .where(ComplaintStatusHistory.complaint_id == complaint_id)
            .order_by(ComplaintStatusHistory.created_at)
        ).scalars().all()

        message_rows = session.execute(
            sa.select(ComplaintMessage)
            .where(ComplaintMessage.complaint_id == complaint_id)
            .order_by(ComplaintMessage.created_at)
        ).scalars().all()

        entries = []
        for s in status_rows:
            entries.append({
                "type": "status_change",
                "old_status": s.old_status,
                "new_status": s.new_status,
                "changed_by": s.changed_by,
                "changer_type": s.changer_type,
                "note": s.note,
                "created_at": s.created_at,
            })
        for m in message_rows:
            entries.append({
                "type": "message",
                "sender_type": m.sender_type,
                "portal_user_id": m.portal_user_id,
                "user_id": m.user_id,
                "message": m.message,
                "created_at": m.created_at,
            })
        entries.sort(key=lambda e: e["created_at"])
        return entries

    @staticmethod
    def list_for_customer(session, customer_id, portal_user_id=None) -> list:
        from portal.models import Complaint

        conditions = [Complaint.customer_id == customer_id]
        if portal_user_id:
            conditions.append(Complaint.portal_user_id == portal_user_id)
        return session.execute(
            sa.select(Complaint).where(sa.and_(*conditions)).order_by(sa.desc(Complaint.created_at))
        ).scalars().all()

    @staticmethod
    def count_open_for_customer(session, customer_id) -> int:
        from portal.models import Complaint

        result = session.execute(
            sa.select(sa.func.count(Complaint.complaint_id)).where(
                Complaint.customer_id == customer_id,
                Complaint.status.in_(["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS"]),
            )
        ).scalar()
        return int(result)


def _record_complaint_status(session, complaint_id, old_status, new_status,
                              changed_by=None, changer_type="SYSTEM", note=None):
    from portal.models import ComplaintStatusHistory

    entry = ComplaintStatusHistory(
        complaint_id=complaint_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        changer_type=changer_type,
        note=note,
    )
    session.add(entry)


# ---------------------------------------------------------------------------
# NotificationService
# ---------------------------------------------------------------------------

class NotificationService:
    @staticmethod
    def create(session, *, portal_user_id, notification_type, title, body=None,
               customer_id=None, reference_type=None, reference_id=None):
        from portal.models import Notification

        notif = Notification(
            portal_user_id=portal_user_id,
            customer_id=customer_id,
            type=notification_type,
            title=title,
            body=body,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        session.add(notif)
        session.flush()
        return notif

    @staticmethod
    def mark_read(session, notification_id, portal_user_id):
        from portal.models import Notification

        notif = session.get(Notification, notification_id)
        if notif is None or notif.portal_user_id != portal_user_id:
            raise APIError("Notification not found.", status_code=404, error_code="not_found")
        notif.is_read = True
        session.flush()
        return notif

    @staticmethod
    def mark_all_read(session, portal_user_id, customer_id=None):
        from portal.models import Notification

        conditions = [
            Notification.portal_user_id == portal_user_id,
            Notification.is_read == sa.false(),
        ]
        if customer_id:
            conditions.append(Notification.customer_id == customer_id)
        session.execute(
            sa.update(Notification).where(sa.and_(*conditions)).values(is_read=True)
        )
        session.flush()

    @staticmethod
    def list_for_user(session, portal_user_id, unread_only=False, customer_id=None):
        from portal.models import Notification

        conditions = [Notification.portal_user_id == portal_user_id]
        if unread_only:
            conditions.append(Notification.is_read == sa.false())
        if customer_id:
            conditions.append(Notification.customer_id == customer_id)
        return session.execute(
            sa.select(Notification)
            .where(sa.and_(*conditions))
            .order_by(sa.desc(Notification.created_at))
        ).scalars().all()

    @staticmethod
    def count_unread(session, portal_user_id) -> int:
        from portal.models import Notification

        return int(session.execute(
            sa.select(sa.func.count(Notification.notification_id)).where(
                Notification.portal_user_id == portal_user_id,
                Notification.is_read == sa.false(),
            )
        ).scalar())


# ---------------------------------------------------------------------------
# RewardService
# ---------------------------------------------------------------------------

class RewardService:
    @staticmethod
    def list_available(session, customer_momentum: int) -> list:
        from datetime import date

        from portal.models import Reward

        today = date.today()
        conditions = [
            Reward.status == "ACTIVE",
            Reward.required_momentum <= customer_momentum,
        ]
        return session.execute(
            sa.select(Reward).where(sa.and_(*conditions)).order_by(Reward.required_momentum)
        ).scalars().all()

    @staticmethod
    def list_all_active(session) -> list:
        from portal.models import Reward

        return session.execute(
            sa.select(Reward).where(Reward.status == "ACTIVE").order_by(Reward.required_momentum)
        ).scalars().all()

    @staticmethod
    def redeem(session, *, portal_user_id, customer_id, reward_id, customer_momentum: int):
        from datetime import datetime

        from portal.models import Reward, RewardRedemption

        reward = session.get(Reward, reward_id)
        if reward is None or reward.status != "ACTIVE":
            raise APIError("Reward not found or inactive.", status_code=404, error_code="not_found")

        if reward.required_momentum > customer_momentum:
            raise APIError("Insufficient Momentum for this reward.", status_code=400, error_code="insufficient_momentum")

        if reward.redemption_limit > 0:
            existing = session.execute(
                sa.select(sa.func.count(RewardRedemption.redemption_id)).where(
                    RewardRedemption.reward_id == reward_id,
                    RewardRedemption.portal_user_id == portal_user_id,
                    RewardRedemption.customer_id == customer_id,
                )
            ).scalar()
            if int(existing) >= reward.redemption_limit:
                raise APIError("Redemption limit reached for this reward.", status_code=400, error_code="redemption_limit")

        redemption = RewardRedemption(
            reward_id=reward_id,
            portal_user_id=portal_user_id,
            customer_id=customer_id,
            momentum_used=reward.required_momentum,
            status="PENDING",
            redeemed_at=datetime.utcnow(),
        )
        session.add(redemption)
        session.flush()
        return redemption

    @staticmethod
    def list_redemptions(session, portal_user_id, customer_id=None) -> list:
        from portal.models import RewardRedemption

        conditions = [RewardRedemption.portal_user_id == portal_user_id]
        if customer_id:
            conditions.append(RewardRedemption.customer_id == customer_id)
        return session.execute(
            sa.select(RewardRedemption)
            .where(sa.and_(*conditions))
            .order_by(sa.desc(RewardRedemption.created_at))
        ).scalars().all()

    @staticmethod
    def has_pending_redemption(session, portal_user_id, customer_id, reward_id) -> bool:
        from portal.models import RewardRedemption

        result = session.execute(
            sa.select(sa.func.count(RewardRedemption.redemption_id)).where(
                RewardRedemption.reward_id == reward_id,
                RewardRedemption.portal_user_id == portal_user_id,
                RewardRedemption.customer_id == customer_id,
                RewardRedemption.status == "PENDING",
            )
        ).scalar()
        return int(result) > 0