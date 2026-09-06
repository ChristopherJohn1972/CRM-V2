import logging

import sqlalchemy as sa
from sqlalchemy import func

from common.db import Base

logger = logging.getLogger(__name__)


class TimestampMixin:
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeletedMixin:
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("true"))


def utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
