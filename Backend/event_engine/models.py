import sqlalchemy as sa
from sqlalchemy import JSON

from common.db import Base
from event_engine.enums import EventOutboxStatus


class EventOutbox(Base):
    __tablename__ = "event_outbox"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    event_id = sa.Column(sa.String(36), nullable=False, unique=True)
    event_type = sa.Column(sa.String(200), nullable=False)
    aggregate_type = sa.Column(sa.String(100), nullable=False)
    aggregate_id = sa.Column(sa.String(100), nullable=False)
    payload = sa.Column(JSON, nullable=False)
    status = sa.Column(sa.Enum(EventOutboxStatus), nullable=False, server_default=EventOutboxStatus.PENDING.value)
    idempotency_key = sa.Column(sa.String(255), nullable=False, unique=True)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    processed_at = sa.Column(sa.DateTime)
    retry_count = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    last_error = sa.Column(sa.Text)


class EventIdempotency(Base):
    __tablename__ = "event_idempotency"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    idempotency_key = sa.Column(sa.String(255), nullable=False, unique=True)
    event_type = sa.Column(sa.String(200), nullable=False)
    result_payload = sa.Column(JSON)
    processed_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    expires_at = sa.Column(sa.DateTime, nullable=False)
