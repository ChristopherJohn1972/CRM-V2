import sqlalchemy as sa
from sqlalchemy import JSON

from common.db import Base
from quotes.enums import (
    ApprovalStatus,
    ClientResponseDecision,
    DiscountType,
    QuoteEventType,
    QuoteItemType,
    QuoteStatus,
    QuoteTemplateStatus,
    QuoteType,
)


class QuoteNumberSequence(Base):
    __tablename__ = "quote_number_sequences"

    bucket = sa.Column(sa.String(50), primary_key=True)
    last_value = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))
    min_length = sa.Column(sa.Integer, nullable=False, server_default=sa.text("2"))
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class TaxRule(Base):
    __tablename__ = "tax_rules"

    tax_rule_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    name = sa.Column(sa.String(100), nullable=False)
    rate = sa.Column(sa.Numeric(5, 2), nullable=False, server_default=sa.text("0.00"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    effective_from = sa.Column(sa.Date)
    effective_until = sa.Column(sa.Date)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class PaymentTerm(Base):
    __tablename__ = "payment_terms"

    payment_term_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(100), nullable=False)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    due_days = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    description = sa.Column(sa.String(500))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    company_profile_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    legal_name = sa.Column(sa.String(255), nullable=False)
    display_name = sa.Column(sa.String(255))
    logo_url = sa.Column(sa.String(500))
    address = sa.Column(sa.String(500))
    phone = sa.Column(sa.String(50))
    email = sa.Column(sa.String(255))
    website = sa.Column(sa.String(255))
    tax_identifier = sa.Column(sa.String(100))
    registration_number = sa.Column(sa.String(100))
    default_currency = sa.Column(sa.String(10), nullable=False, server_default="KES")
    what_we_do = sa.Column(sa.Text)
    default_introduction = sa.Column(sa.Text)
    default_terms_and_conditions = sa.Column(sa.Text)
    default_footer = sa.Column(sa.Text)
    bank_name = sa.Column(sa.String(200))
    bank_account_number = sa.Column(sa.String(100))
    bank_branch = sa.Column(sa.String(200))
    bank_sort_code = sa.Column(sa.String(50))
    is_default = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class QuoteTemplate(Base):
    __tablename__ = "quote_templates"

    template_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(200), nullable=False)
    description = sa.Column(sa.String(500))
    template_type = sa.Column(
        sa.Enum(QuoteType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=QuoteType.PRODUCT.value,
    )
    status = sa.Column(
        sa.Enum(QuoteTemplateStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=QuoteTemplateStatus.ACTIVE.value,
    )
    current_version = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))
    is_default = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    content_config = sa.Column(JSON)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class QuoteTemplateVersion(Base):
    __tablename__ = "quote_template_versions"

    template_version_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    template_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quote_templates.template_id", ondelete="CASCADE"),
        nullable=False,
    )
    version = sa.Column(sa.Integer, nullable=False)
    content_config = sa.Column(JSON, nullable=False)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("template_id", "version", name="uq_template_version"),
    )


class Quote(Base):
    __tablename__ = "quotes"

    quote_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_number = sa.Column(sa.String(50), nullable=False, unique=True)
    sequence_value = sa.Column(sa.BigInteger, nullable=False)
    revision = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    quote_type = sa.Column(
        sa.Enum(QuoteType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    title = sa.Column(sa.String(255))
    customer_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = sa.Column(
        sa.Enum(QuoteStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=QuoteStatus.DRAFT.value,
    )
    currency = sa.Column(sa.String(10), nullable=False, server_default="KES")
    quote_date = sa.Column(sa.Date, nullable=False)
    valid_until = sa.Column(sa.Date)
    subtotal = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    discount_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    discount_type = sa.Column(
        sa.Enum(DiscountType, values_callable=lambda e: [x.value for x in e]),
    )
    discount_value = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    tax_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    additional_charges = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    grand_total = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    notes = sa.Column(sa.Text)
    internal_notes = sa.Column(sa.Text)
    terms_and_conditions = sa.Column(sa.Text)
    payment_term_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("payment_terms.payment_term_id", ondelete="SET NULL")
    )
    template_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("quote_templates.template_id", ondelete="SET NULL")
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
    sent_at = sa.Column(sa.DateTime)
    viewed_at = sa.Column(sa.DateTime)
    accepted_at = sa.Column(sa.DateTime)
    rejected_at = sa.Column(sa.DateTime)
    expired_at = sa.Column(sa.DateTime)
    cancelled_at = sa.Column(sa.DateTime)
    version = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    deleted_at = sa.Column(sa.DateTime)
    deleted_by = sa.Column(sa.BigInteger)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class QuoteItem(Base):
    __tablename__ = "quote_items"

    item_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type = sa.Column(
        sa.Enum(QuoteItemType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=QuoteItemType.CUSTOM.value,
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


class QuoteVersion(Base):
    __tablename__ = "quote_versions"

    version_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="CASCADE"),
        nullable=False,
    )
    revision = sa.Column(sa.Integer, nullable=False)
    snapshot = sa.Column(JSON, nullable=False)
    template_version_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("quote_template_versions.template_version_id")
    )
    company_profile_snapshot = sa.Column(JSON)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("quote_id", "revision", name="uq_quote_version"),
    )


class QuoteDocument(Base):
    __tablename__ = "quote_documents"

    document_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="CASCADE"),
        nullable=False,
    )
    quote_version_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("quote_versions.version_id")
    )
    document_type = sa.Column(
        sa.String(20), nullable=False, server_default="PDF"
    )
    file_name = sa.Column(sa.String(255), nullable=False)
    storage_key = sa.Column(sa.String(500))
    file_size_bytes = sa.Column(sa.BigInteger)
    content_hash = sa.Column(sa.String(128))
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class QuoteApproval(Base):
    __tablename__ = "quote_approvals"

    approval_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="CASCADE"),
        nullable=False,
    )
    approver_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False
    )
    status = sa.Column(
        sa.Enum(ApprovalStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default=ApprovalStatus.PENDING.value,
    )
    reason = sa.Column(sa.String(500))
    requested_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    decided_at = sa.Column(sa.DateTime)


class QuoteEvent(Base):
    __tablename__ = "quote_events"

    event_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    actor_portal_user_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("portal_users.portal_user_id", ondelete="SET NULL")
    )
    actor_type = sa.Column(
        sa.String(20), nullable=False, server_default="INTERNAL_USER"
    )
    event_type = sa.Column(sa.String(50), nullable=False)
    description = sa.Column(sa.String(500))
    metadata_ = sa.Column(JSON)
    occurred_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class QuotePortalAccess(Base):
    __tablename__ = "quote_portal_access"

    portal_access_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_account_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("customer_accounts.customer_account_id", ondelete="CASCADE"),
        nullable=False,
    )
    visibility = sa.Column(
        sa.String(20), nullable=False, server_default="VISIBLE"
    )
    published_at = sa.Column(sa.DateTime)
    revoked_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint(
            "quote_id", "customer_account_id", name="uq_portal_access_quote_account"
        ),
    )


class QuoteClientResponse(Base):
    __tablename__ = "quote_client_responses"

    response_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    quote_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("quotes.quote_id", ondelete="CASCADE"),
        nullable=False,
    )
    portal_user_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("portal_users.portal_user_id", ondelete="SET NULL"),
        nullable=False,
    )
    customer_account_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey("customer_accounts.customer_account_id", ondelete="CASCADE"),
        nullable=False,
    )
    decision = sa.Column(
        sa.Enum(ClientResponseDecision, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    comment = sa.Column(sa.Text)
    responded_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
