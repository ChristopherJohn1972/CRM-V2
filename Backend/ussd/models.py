import sqlalchemy as sa
from sqlalchemy import JSON

from common.db import Base
from ussd.enums import UssdSessionStatus, UssdMenuType


class UssdSession(Base):
    __tablename__ = "ussd_sessions"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    session_id = sa.Column(sa.String(100), nullable=False, unique=True)
    phone_number = sa.Column(sa.String(50), nullable=False)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="SET NULL"))
    current_menu = sa.Column(
        sa.Enum(UssdMenuType), nullable=False, server_default=UssdMenuType.MAIN.value
    )
    status = sa.Column(
        sa.Enum(UssdSessionStatus), nullable=False, server_default=UssdSessionStatus.ACTIVE.value
    )
    flow_data = sa.Column(JSON)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    expires_at = sa.Column(sa.DateTime, nullable=False)


class UssdTransaction(Base):
    __tablename__ = "ussd_transactions"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    session_id = sa.Column(sa.String(100), nullable=False)
    phone_number = sa.Column(sa.String(50), nullable=False)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="SET NULL"))
    flow_type = sa.Column(sa.String(50), nullable=False)
    input_text = sa.Column(sa.String(500))
    response_text = sa.Column(sa.Text)
    status = sa.Column(sa.String(20), nullable=False, server_default="INITIATED")
    metadata_ = sa.Column("metadata", JSON)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class UssdShortCode(Base):
    __tablename__ = "ussd_short_codes"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    short_code = sa.Column(sa.String(20), nullable=False, unique=True)
    description = sa.Column(sa.String(255))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    gateway_provider = sa.Column(sa.String(100))
    gateway_config = sa.Column(JSON)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
