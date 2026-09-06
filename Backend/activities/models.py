import sqlalchemy as sa

from common.base import TimestampMixin
from common.db import Base


class ActivityType(Base):
    __tablename__ = "activity_types"

    activity_type_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True)
    name = sa.Column(sa.String(100), nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class ActivityStatus:
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Activity(Base, TimestampMixin):
    __tablename__ = "activities"

    activity_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    activity_type = sa.Column(sa.String(50), nullable=False)
    subject = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text)
    status = sa.Column(sa.String(20), nullable=False, server_default=ActivityStatus.OPEN)
    priority = sa.Column(sa.String(20))
    due_at = sa.Column(sa.DateTime)
    completed_at = sa.Column(sa.DateTime)
    assigned_to = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class NoteVisibility:
    PRIVATE = "PRIVATE"
    TEAM = "TEAM"
    PUBLIC = "PUBLIC"


class ActivityNote(Base, TimestampMixin):
    __tablename__ = "activity_notes"

    note_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    activity_id = sa.Column(sa.BigInteger, sa.ForeignKey("activities.activity_id", ondelete="CASCADE"))
    author_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    visibility = sa.Column(sa.String(20), nullable=False, server_default=NoteVisibility.TEAM)
    body = sa.Column(sa.Text, nullable=False)


class ActorType:
    INTERNAL_USER = "INTERNAL_USER"
    PORTAL_USER = "PORTAL_USER"
    SYSTEM = "SYSTEM"


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    event_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    customer_id = sa.Column(
        sa.BigInteger, sa.ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False
    )
    actor_type = sa.Column(sa.String(20), nullable=False, server_default=ActorType.SYSTEM)
    actor_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    actor_label = sa.Column(sa.String(255))
    source_module = sa.Column(sa.String(50), nullable=False)
    event_type = sa.Column(sa.String(100), nullable=False)
    summary = sa.Column(sa.String(500), nullable=False)
    reference_type = sa.Column(sa.String(100))
    reference_id = sa.Column(sa.BigInteger)
    occurred_at = sa.Column(sa.DateTime, nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
