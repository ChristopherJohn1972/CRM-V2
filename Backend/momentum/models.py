import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON

from common.db import Base
from momentum.enums import MomentumEntryType, MomentumTriggerType


class MomentumRule(Base):
    __tablename__ = "momentum_rules"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(150), nullable=False)
    code = sa.Column(sa.String(100), nullable=False, unique=True)
    trigger_type = sa.Column(sa.Enum(MomentumTriggerType), nullable=False)
    config = sa.Column(JSON, nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    valid_from = sa.Column(sa.DateTime, nullable=False)
    valid_until = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class MomentumRuleVersion(Base):
    __tablename__ = "momentum_rules_versions"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    rule_id = sa.Column(sa.BigInteger, sa.ForeignKey("momentum_rules.id", ondelete="CASCADE"), nullable=False)
    version = sa.Column(sa.Integer, nullable=False)
    config = sa.Column(JSON, nullable=False)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class MomentumLedger(Base):
    __tablename__ = "momentum_ledger"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    entry_type = sa.Column(sa.Enum(MomentumEntryType), nullable=False)
    points = sa.Column(sa.Integer, nullable=False)
    balance_after = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    source_type = sa.Column(sa.String(50), nullable=False)
    source_id = sa.Column(sa.String(100))
    rule_id = sa.Column(sa.BigInteger, sa.ForeignKey("momentum_rules.id", ondelete="SET NULL"))
    description = sa.Column(sa.String(500))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class MomentumSnapshot(Base):
    __tablename__ = "momentum_snapshots"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    balance = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    snapshot_date = sa.Column(sa.Date, nullable=False)
    period_start = sa.Column(sa.Date, nullable=False)
    period_end = sa.Column(sa.Date, nullable=False)
