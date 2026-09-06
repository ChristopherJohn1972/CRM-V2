import logging
import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from common.exceptions import ConflictError, NotFoundError
from event_engine.enums import EventOutboxStatus
from event_engine.models import EventIdempotency, EventOutbox

logger = logging.getLogger(__name__)


class EventIngestionService:
    MAX_RETRIES = 5
    IDEMPOTENCY_TTL_HOURS = 72

    @staticmethod
    def ingest(
        db,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
        idempotency_key: str = None,
    ) -> EventOutbox:
        if idempotency_key is None:
            idempotency_key = f"{event_type}:{aggregate_type}:{aggregate_id}:{uuid.uuid4().hex[:16]}"

        existing = db.execute(
            sa.select(EventOutbox).where(EventOutbox.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing:
            return existing

        idem_record = db.execute(
            sa.select(EventIdempotency).where(EventIdempotency.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if idem_record:
            return None

        outbox = EventOutbox(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=payload,
            status=EventOutboxStatus.PENDING.value,
            idempotency_key=idempotency_key,
        )
        db.add(outbox)
        db.flush()

        idem = EventIdempotency(
            idempotency_key=idempotency_key,
            event_type=event_type,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=EventIngestionService.IDEMPOTENCY_TTL_HOURS),
        )
        db.add(idem)
        db.flush()

        return outbox


class EventProcessingService:
    @staticmethod
    def process_pending(db, batch_size: int = 50):
        stmt = (
            sa.select(EventOutbox)
            .where(EventOutbox.status == EventOutboxStatus.PENDING.value)
            .order_by(EventOutbox.created_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        rows = db.execute(stmt).scalars().all()

        for outbox_event in rows:
            outbox_event.status = EventOutboxStatus.PROCESSING.value
            db.flush()

            try:
                from common.events import EventBus
                from common.events import DomainEvent

                event = DomainEvent(
                    event_type=outbox_event.event_type,
                    source_module=outbox_event.aggregate_type,
                    summary=f"Outbox event: {outbox_event.event_type}",
                    payload=outbox_event.payload,
                )
                EventBus.publish(event)

                outbox_event.status = EventOutboxStatus.PROCESSED.value
                outbox_event.processed_at = datetime.now(timezone.utc)
                db.flush()
            except Exception as exc:
                logger.exception("Failed to process outbox event %s", outbox_event.event_id)
                outbox_event.retry_count += 1
                outbox_event.last_error = str(exc)[:2000]
                if outbox_event.retry_count >= EventIngestionService.MAX_RETRIES:
                    outbox_event.status = EventOutboxStatus.FAILED.value
                db.flush()

        return len(rows)

    @staticmethod
    def retry_failed(db, event_id: str):
        outbox_event = db.execute(
            sa.select(EventOutbox).where(
                EventOutbox.event_id == event_id,
                EventOutbox.status == EventOutboxStatus.FAILED.value,
            )
        ).scalar_one_or_none()
        if outbox_event is None:
            raise NotFoundError("Failed event not found.")

        outbox_event.status = EventOutboxStatus.PENDING.value
        outbox_event.retry_count = 0
        outbox_event.last_error = None
        db.flush()
        return outbox_event

    @staticmethod
    def cleanup_expired(db, days: int = 30):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        db.execute(
            sa.delete(EventIdempotency).where(EventIdempotency.expires_at < datetime.now(timezone.utc))
        )
        db.execute(
            sa.delete(EventOutbox).where(
                EventOutbox.status == EventOutboxStatus.PROCESSED.value,
                EventOutbox.processed_at < cutoff,
            )
        )
        db.flush()
