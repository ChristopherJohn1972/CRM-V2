import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON

from common.db import Base
from sales_orders.enums import (
    AdjustmentType,
    DiscountType,
    OrderItemType,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentOverallStatus,
    PaymentStatus,
    ReceiptStatus,
    ReceiptTemplateStatus,
)


# ---------------------------------------------------------------------------
# Number Sequences
# ---------------------------------------------------------------------------

class SONumberSequence(Base):
    __tablename__ = "so_number_sequences"

    bucket = sa.Column(sa.String(50), primary_key=True)
    last_value = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))
    min_length = sa.Column(sa.Integer, nullable=False, server_default=sa.text("4"))
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ReceiptNumberSequence(Base):
    __tablename__ = "receipt_number_sequences"

    bucket = sa.Column(sa.String(50), primary_key=True)
    last_value = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))
    min_length = sa.Column(sa.Integer, nullable=False, server_default=sa.text("4"))
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Sales Order
# ---------------------------------------------------------------------------

class SalesOrder(Base):
    __tablename__ = "sales_orders"

    order_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    order_number = sa.Column(sa.String(50), nullable=False, unique=True)
    sequence_value = sa.Column(sa.BigInteger, nullable=False)
    customer_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False,
    )
    source = sa.Column(
        sa.Enum(OrderSource, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=OrderSource.DIRECT.value,
    )
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="SET NULL"),
    )
    status = sa.Column(
        sa.Enum(OrderStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=OrderStatus.DRAFT.value,
    )
    order_date = sa.Column(sa.Date, nullable=False)
    expected_delivery_date = sa.Column(sa.Date)
    currency = sa.Column(sa.String(10), nullable=False, server_default="KES")

    subtotal = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    discount_type = sa.Column(
        sa.Enum(DiscountType, values_callable=lambda e: [x.value for x in e]),
    )
    discount_value = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    discount_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    tax_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    additional_charges = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    grand_total = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    amount_paid = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    balance_due = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    payment_status = sa.Column(
        sa.Enum(PaymentOverallStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=PaymentOverallStatus.UNPAID.value,
    )

    notes = sa.Column(sa.Text)
    internal_notes = sa.Column(sa.Text)
    terms_and_conditions = sa.Column(sa.Text)
    payment_term_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("payment_terms.payment_term_id", ondelete="SET NULL")
    )
    company_profile_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("company_profiles.company_profile_id", ondelete="SET NULL")
    )
    owner_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False
    )
    assigned_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    assigned_team_id = sa.Column(sa.BigInteger, sa.ForeignKey("teams.team_id", ondelete="SET NULL"))

    approved_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    approved_at = sa.Column(sa.DateTime)
    confirmed_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    confirmed_at = sa.Column(sa.DateTime)
    cancelled_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    cancelled_at = sa.Column(sa.DateTime)
    cancellation_reason = sa.Column(sa.Text)

    created_by = sa.Column(
        sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False
    )
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    deleted_at = sa.Column(sa.DateTime)
    deleted_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    version = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Sales Order Items
# ---------------------------------------------------------------------------

class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    item_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    order_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type = sa.Column(
        sa.Enum(OrderItemType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=OrderItemType.CUSTOM.value,
    )
    reference_id = sa.Column(sa.String(100))
    sku = sa.Column(sa.String(100))
    description = sa.Column(sa.String(500), nullable=False)
    quantity = sa.Column(sa.Numeric(12, 2), nullable=False, server_default=sa.text("1.00"))
    unit_price = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    discount_type = sa.Column(
        sa.Enum(DiscountType, values_callable=lambda e: [x.value for x in e]),
    )
    discount_value = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    discount_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    tax_code = sa.Column(sa.String(50))
    tax_rate = sa.Column(sa.Numeric(5, 2), nullable=False, server_default=sa.text("0.00"))
    tax_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    gross_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    net_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    line_total = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    sort_order = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    unit_of_measure = sa.Column(sa.String(50))
    notes = sa.Column(sa.String(500))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Order Adjustments
# ---------------------------------------------------------------------------

class OrderAdjustment(Base):
    __tablename__ = "order_adjustments"

    adjustment_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    order_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    adjustment_type = sa.Column(
        sa.Enum(AdjustmentType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    description = sa.Column(sa.String(255), nullable=False)
    rate = sa.Column(sa.Numeric(5, 2))
    amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    is_taxable = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    sort_order = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Order Events
# ---------------------------------------------------------------------------

class SalesOrderEvent(Base):
    __tablename__ = "sales_order_events"

    event_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    order_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    actor_type = sa.Column(sa.String(20), nullable=False, server_default="INTERNAL_USER")
    event_type = sa.Column(sa.String(50), nullable=False)
    description = sa.Column(sa.String(500))
    metadata_ = sa.Column("metadata", JSON)
    occurred_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Order Documents
# ---------------------------------------------------------------------------

class SalesOrderDocument(Base):
    __tablename__ = "sales_order_documents"

    document_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    order_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type = sa.Column(sa.String(20), nullable=False, server_default="PDF")
    file_name = sa.Column(sa.String(255), nullable=False)
    storage_key = sa.Column(sa.String(500))
    file_size_bytes = sa.Column(sa.BigInteger)
    content_hash = sa.Column(sa.String(128))
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Order Portal Access
# ---------------------------------------------------------------------------

class SalesOrderPortalAccess(Base):
    __tablename__ = "sales_order_portal_access"

    portal_access_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    order_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_account_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("customer_accounts.customer_account_id", ondelete="CASCADE"),
        nullable=False,
    )
    visibility = sa.Column(sa.String(20), nullable=False, server_default="VISIBLE")
    published_at = sa.Column(sa.DateTime)
    revoked_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint(
            "order_id", "customer_account_id", name="uq_so_portal_access_order_account"
        ),
    )


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class OrderPayment(Base):
    __tablename__ = "order_payments"

    payment_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    payment_reference = sa.Column(sa.String(100), unique=True)
    order_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False,
    )
    amount = sa.Column(sa.Numeric(18, 2), nullable=False)
    currency = sa.Column(sa.String(10), nullable=False, server_default="KES")
    payment_method = sa.Column(
        sa.Enum(PaymentMethod, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    status = sa.Column(
        sa.Enum(PaymentStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=PaymentStatus.PENDING.value,
    )
    gateway_reference = sa.Column(sa.String(255))
    notes = sa.Column(sa.Text)
    received_at = sa.Column(sa.DateTime)
    confirmed_at = sa.Column(sa.DateTime)
    confirmed_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    reversed_at = sa.Column(sa.DateTime)
    reversed_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    reversal_reason = sa.Column(sa.Text)
    idempotency_key = sa.Column(sa.String(255), unique=True)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------

class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    receipt_number = sa.Column(sa.String(50), nullable=False, unique=True)
    payment_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("order_payments.payment_id", ondelete="CASCADE"),
        nullable=False,
    )
    order_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False,
    )
    amount = sa.Column(sa.Numeric(18, 2), nullable=False)
    currency = sa.Column(sa.String(10), nullable=False, server_default="KES")
    status = sa.Column(
        sa.Enum(ReceiptStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=ReceiptStatus.VALID.value,
    )
    verification_token = sa.Column(sa.String(255), nullable=False, unique=True)
    template_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("receipt_templates.template_id", ondelete="SET NULL")
    )
    template_version_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("receipt_template_versions.template_version_id", ondelete="SET NULL")
    )
    company_profile_snapshot = sa.Column(JSON)
    issued_at = sa.Column(sa.DateTime, nullable=False)
    voided_at = sa.Column(sa.DateTime)
    voided_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    void_reason = sa.Column(sa.Text)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


# ---------------------------------------------------------------------------
# Receipt Templates
# ---------------------------------------------------------------------------

class ReceiptTemplate(Base):
    __tablename__ = "receipt_templates"

    template_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(200), nullable=False)
    description = sa.Column(sa.String(500))
    status = sa.Column(
        sa.Enum(ReceiptTemplateStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=ReceiptTemplateStatus.ACTIVE.value,
    )
    current_version = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))
    is_default = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    content_config = sa.Column(JSON)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ReceiptTemplateVersion(Base):
    __tablename__ = "receipt_template_versions"

    template_version_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    template_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("receipt_templates.template_id", ondelete="CASCADE"),
        nullable=False,
    )
    version = sa.Column(sa.Integer, nullable=False)
    content_config = sa.Column(JSON, nullable=False)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("template_id", "version", name="uq_receipt_template_version"),
    )


# ---------------------------------------------------------------------------
# Receipt Verification Log
# ---------------------------------------------------------------------------

class ReceiptVerification(Base):
    __tablename__ = "receipt_verifications"

    verification_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    receipt_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("receipts.receipt_id", ondelete="CASCADE"),
        nullable=False,
    )
    verification_token = sa.Column(sa.String(255), nullable=False)
    ip_address = sa.Column(sa.String(45))
    user_agent = sa.Column(sa.String(500))
    result = sa.Column(sa.String(20), nullable=False)
    verified_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
