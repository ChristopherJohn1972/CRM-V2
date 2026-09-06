import sqlalchemy as sa

from common.base import TimestampMixin
from common.db import Base


class SmsStatus:
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class Direction:
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class SmsMessage(Base, TimestampMixin):
    __tablename__ = "sms_messages"

    sms_message_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="SET NULL"))
    provider = sa.Column(sa.String(50), nullable=False, server_default="internal")
    provider_message_id = sa.Column(sa.String(255))
    direction = sa.Column(sa.String(20), nullable=False, server_default=Direction.OUTBOUND)
    from_number = sa.Column(sa.String(50))
    to_number = sa.Column(sa.String(50), nullable=False)
    body = sa.Column(sa.Text, nullable=False)
    status = sa.Column(sa.String(20), nullable=False, server_default=SmsStatus.QUEUED)
    failure_reason = sa.Column(sa.String(500))
    attempts = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    provider_reference = sa.Column(sa.String(255))
    sent_at = sa.Column(sa.DateTime)
    delivered_at = sa.Column(sa.DateTime)
    last_attempt_at = sa.Column(sa.DateTime)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class EmailMessage(Base, TimestampMixin):
    __tablename__ = "email_messages"

    email_message_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="SET NULL"))
    provider = sa.Column(sa.String(50), nullable=False, server_default="internal")
    provider_message_id = sa.Column(sa.String(255))
    message_id = sa.Column(sa.String(255))
    direction = sa.Column(sa.String(20), nullable=False, server_default=Direction.OUTBOUND)
    from_address = sa.Column(sa.String(255))
    to_address = sa.Column(sa.String(255), nullable=False)
    cc_address = sa.Column(sa.String(500))
    bcc_address = sa.Column(sa.String(500))
    subject = sa.Column(sa.String(500))
    body = sa.Column(sa.Text)
    status = sa.Column(sa.String(20), nullable=False, server_default=SmsStatus.QUEUED)
    failure_reason = sa.Column(sa.String(500))
    attempts = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    provider_reference = sa.Column(sa.String(255))
    sent_at = sa.Column(sa.DateTime)
    delivered_at = sa.Column(sa.DateTime)
    last_attempt_at = sa.Column(sa.DateTime)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class CallLog(Base, TimestampMixin):
    __tablename__ = "call_logs"

    call_log_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="SET NULL"))
    direction = sa.Column(sa.String(20), nullable=False, server_default=Direction.OUTBOUND)
    phone_number = sa.Column(sa.String(50))
    staff_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    started_at = sa.Column(sa.DateTime)
    ended_at = sa.Column(sa.DateTime)
    duration_seconds = sa.Column(sa.Integer)
    outcome = sa.Column(sa.String(100))
    notes = sa.Column(sa.Text)


class CommunicationProviderEvent(Base):
    __tablename__ = "communication_provider_events"

    provider_event_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    provider = sa.Column(sa.String(50), nullable=False)
    event_type = sa.Column(sa.String(100), nullable=False)
    provider_message_id = sa.Column(sa.String(255))
    status = sa.Column(sa.String(20))
    raw_event = sa.Column(sa.JSON)
    received_at = sa.Column(sa.DateTime, nullable=False)
    processed = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("0"))
