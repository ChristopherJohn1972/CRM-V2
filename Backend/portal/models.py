import sqlalchemy as sa

from common.db import Base
from portal.enums import (
    ComplaintStatus,
    CustomerAccountStatus,
    NotificationType,
    PaymentStatus,
    PortalPermissionEffect,
    PortalRelationshipType,
    PortalUserStatus,
    RedemptionStatus,
    RewardStatus,
)


class CustomerAccount(Base):
    """Portal identity layer: links a Customer to an account_number.

    The account_number is the public portal identifier. Multiple portal users
    (real people) authenticate against a single customer account.
    """
    __tablename__ = "customer_accounts"

    customer_account_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    account_number = sa.Column(sa.String(50), nullable=False, unique=True)
    status = sa.Column(
        sa.Enum(CustomerAccountStatus), nullable=False, server_default=CustomerAccountStatus.ACTIVE.value
    )
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PortalUser(Base):
    """A real human being who authenticates to the portal.

    Email is the login identifier. Multiple portal users can be linked to
    the same customer account with different roles.
    """
    __tablename__ = "portal_users"

    portal_user_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    email = sa.Column(sa.String(255), nullable=False, unique=True)
    first_name = sa.Column(sa.String(100), nullable=False)
    last_name = sa.Column(sa.String(100), nullable=False)
    phone = sa.Column(sa.String(50))
    status = sa.Column(
        sa.Enum(PortalUserStatus), nullable=False, server_default=PortalUserStatus.PENDING.value
    )
    email_verified_at = sa.Column(sa.DateTime)
    last_login_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PortalAuthenticationCredential(Base):
    __tablename__ = "portal_authentication_credentials"

    portal_credential_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    password_hash = sa.Column(sa.String(255), nullable=False)
    password_changed_at = sa.Column(sa.DateTime)
    password_expires_at = sa.Column(sa.DateTime)
    failed_login_attempts = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    locked_until = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PortalPermission(Base):
    __tablename__ = "portal_permissions"

    portal_permission_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(150), nullable=False, unique=True)
    code = sa.Column(sa.String(150), nullable=False, unique=True)
    resource = sa.Column(sa.String(100), nullable=False)
    action = sa.Column(sa.String(100), nullable=False)
    description = sa.Column(sa.String(255))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PortalUserPermission(Base):
    __tablename__ = "portal_user_permissions"

    portal_user_permission_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="CASCADE"), nullable=False
    )
    portal_permission_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_permissions.portal_permission_id", ondelete="CASCADE"), nullable=False
    )
    effect = sa.Column(
        sa.Enum(PortalPermissionEffect), nullable=False, server_default=PortalPermissionEffect.ALLOW.value
    )
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("portal_user_id", "portal_permission_id", name="uq_portal_user_permission"),
    )


class PortalUserCustomer(Base):
    """Links a portal user (person) to a customer account with a role.

    A person can be linked to multiple customer accounts if needed.
    The role determines what the person can do within that account.
    """
    __tablename__ = "portal_user_customers"

    portal_user_customer_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="CASCADE"), nullable=False
    )
    customer_account_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customer_accounts.customer_account_id", ondelete="CASCADE"), nullable=False
    )
    role = sa.Column(
        sa.Enum(PortalRelationshipType), nullable=False, server_default=PortalRelationshipType.CONTACT.value
    )
    is_primary = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("portal_user_id", "customer_account_id", name="uq_portal_user_customer_account"),
    )


class PortalSession(Base):
    __tablename__ = "portal_sessions"

    portal_session_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="CASCADE"), nullable=False
    )
    session_token_hash = sa.Column(sa.String(255), nullable=False, unique=True)
    ip_address = sa.Column(sa.String(45))
    user_agent = sa.Column(sa.String(500))
    expires_at = sa.Column(sa.DateTime, nullable=False)
    revoked_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PortalPasswordResetToken(Base):
    __tablename__ = "portal_password_reset_tokens"

    token_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="CASCADE"), nullable=False
    )
    token_hash = sa.Column(sa.String(255), nullable=False, unique=True)
    expires_at = sa.Column(sa.DateTime, nullable=False)
    consumed_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Payment(Base):
    __tablename__ = "payments"

    payment_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    amount = sa.Column(sa.Numeric(15, 2), nullable=False)
    payment_date = sa.Column(sa.Date, nullable=False)
    reference = sa.Column(sa.String(50), nullable=False, unique=True)
    payment_method = sa.Column(sa.String(50))
    status = sa.Column(
        sa.Enum(PaymentStatus), nullable=False, server_default=PaymentStatus.PENDING.value
    )
    description = sa.Column(sa.String(255))
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    invoice_number = sa.Column(sa.String(50), nullable=False, unique=True)
    invoice_date = sa.Column(sa.Date, nullable=False)
    due_date = sa.Column(sa.Date)
    total_amount = sa.Column(sa.Numeric(15, 2), nullable=False)
    amount_paid = sa.Column(sa.Numeric(15, 2), nullable=False, server_default=sa.text("0.00"))
    status = sa.Column(sa.String(20), nullable=False, server_default="OUTSTANDING")
    description = sa.Column(sa.String(255))
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    receipt_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    payment_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("payments.payment_id", ondelete="CASCADE"), nullable=False
    )
    receipt_number = sa.Column(sa.String(50), nullable=False, unique=True)
    issued_at = sa.Column(sa.DateTime, nullable=False)
    file_name = sa.Column(sa.String(255))
    storage_key = sa.Column(sa.String(500))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="SET NULL")
    )
    complaint_number = sa.Column(sa.String(50), nullable=False, unique=True)
    subject = sa.Column(sa.String(255), nullable=False)
    category = sa.Column(sa.String(100))
    description = sa.Column(sa.Text)
    priority = sa.Column(sa.String(20), nullable=False, server_default="MEDIUM")
    status = sa.Column(
        sa.Enum(ComplaintStatus), nullable=False, server_default=ComplaintStatus.SUBMITTED.value
    )
    assigned_to = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    preferred_contact = sa.Column(sa.String(20), nullable=False, server_default="PORTAL")
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"

    message_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    complaint_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False
    )
    portal_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="SET NULL"))
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    sender_type = sa.Column(sa.String(20), nullable=False)
    message = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ComplaintAttachment(Base):
    __tablename__ = "complaint_attachments"

    attachment_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    complaint_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False
    )
    complaint_message_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("complaint_messages.message_id", ondelete="SET NULL")
    )
    file_name = sa.Column(sa.String(255), nullable=False)
    mime_type = sa.Column(sa.String(120))
    size_bytes = sa.Column(sa.BigInteger)
    storage_key = sa.Column(sa.String(500), nullable=False)
    uploaded_by = sa.Column(sa.BigInteger)
    uploader_type = sa.Column(sa.String(20), nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ComplaintStatusHistory(Base):
    __tablename__ = "complaint_status_history"

    history_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    complaint_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False
    )
    old_status = sa.Column(sa.String(30))
    new_status = sa.Column(sa.String(30), nullable=False)
    changed_by = sa.Column(sa.BigInteger)
    changer_type = sa.Column(sa.String(20), nullable=False)
    note = sa.Column(sa.String(255))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="CASCADE"), nullable=False
    )
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="SET NULL"))
    type = sa.Column(
        sa.Enum(NotificationType), nullable=False
    )
    title = sa.Column(sa.String(255), nullable=False)
    body = sa.Column(sa.Text)
    reference_type = sa.Column(sa.String(50))
    reference_id = sa.Column(sa.BigInteger)
    is_read = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Reward(Base):
    __tablename__ = "rewards"

    reward_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(200), nullable=False)
    description = sa.Column(sa.Text)
    required_momentum = sa.Column(sa.Integer, nullable=False)
    status = sa.Column(
        sa.Enum(RewardStatus), nullable=False, server_default=RewardStatus.ACTIVE.value
    )
    redemption_limit = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))
    available_from = sa.Column(sa.Date)
    available_until = sa.Column(sa.Date)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class RewardRedemption(Base):
    __tablename__ = "reward_redemptions"

    redemption_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    reward_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("rewards.reward_id", ondelete="CASCADE"), nullable=False
    )
    portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="CASCADE"), nullable=False
    )
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    momentum_used = sa.Column(sa.Integer, nullable=False)
    status = sa.Column(
        sa.Enum(RedemptionStatus), nullable=False, server_default=RedemptionStatus.PENDING.value
    )
    redeemed_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())