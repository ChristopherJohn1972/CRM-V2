import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON

from common.db import Base
from referrals.enums import ReferralCodeStatus, ReferralEventType


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    code = sa.Column(sa.String(100), nullable=False, unique=True)
    referrer_customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="SET NULL"))
    status = sa.Column(sa.Enum(ReferralCodeStatus), nullable=False, server_default=ReferralCodeStatus.ACTIVE.value)
    max_referrals = sa.Column(sa.Integer)
    referral_count = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    expires_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ReferralEvent(Base):
    __tablename__ = "referral_events"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    referral_code_id = sa.Column(sa.BigInteger, sa.ForeignKey("referral_codes.id", ondelete="CASCADE"), nullable=False)
    referred_customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    event_type = sa.Column(sa.Enum(ReferralEventType), nullable=False)
    metadata_ = sa.Column("metadata", JSON)
    occurred_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ReferralQualification(Base):
    __tablename__ = "referral_qualifications"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    referral_id = sa.Column(sa.BigInteger, sa.ForeignKey("referral_events.id", ondelete="CASCADE"), nullable=False)
    order_id = sa.Column(sa.BigInteger, sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"), nullable=False)
    amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    qualified_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    reward_issued = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    reward_amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
