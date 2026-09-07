import sqlalchemy as sa
from sqlalchemy import JSON

from common.db import Base
from attribution.enums import AttributionEventType, AttributionModelType


class AttributionModel(Base):
    __tablename__ = "attribution_models"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(100), nullable=False)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    description = sa.Column(sa.Text)
    config = sa.Column(JSON)
    is_default = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class AttributionEvent(Base):
    __tablename__ = "attribution_events"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    source_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaign_sources.id", ondelete="SET NULL"))
    event_type = sa.Column(sa.Enum(AttributionEventType), nullable=False)
    touch_point_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    metadata_ = sa.Column("metadata", JSON)
    session_id = sa.Column(sa.String(255))


class AttributionResult(Base):
    __tablename__ = "attribution_results"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    order_id = sa.Column(sa.BigInteger, sa.ForeignKey("sales_orders.order_id", ondelete="CASCADE"), nullable=False)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    model_type = sa.Column(sa.Enum(AttributionModelType), nullable=False, server_default=AttributionModelType.LAST_TOUCH.value)
    attributed_revenue = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    attributed_weight = sa.Column(sa.Numeric(5, 4), nullable=False, server_default=sa.text("0.0000"))
    computed_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
