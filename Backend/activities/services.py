import logging
from datetime import datetime, timezone

import sqlalchemy as sa

from activities.models import ActorType, Activity, ActivityNote, TimelineEvent
from common.db import SessionLocal

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ActivityService:
    @staticmethod
    def create(db, *, customer_id, activity_type, subject, description=None, status="OPEN",
               priority=None, due_at=None, assigned_to=None, actor_user_id):
        activity = Activity(
            customer_id=customer_id,
            activity_type=activity_type,
            subject=subject,
            description=description,
            status=status,
            priority=priority,
            due_at=due_at,
            assigned_to=assigned_to,
            created_by=actor_user_id,
        )
        db.add(activity)
        return activity

    @staticmethod
    def complete(db, activity, actor_user_id):
        activity.status = "COMPLETED"
        activity.completed_at = _utcnow()
        return activity


class NoteService:
    @staticmethod
    def create(db, *, customer_id, body, author_user_id, visibility="TEAM", activity_id=None):
        note = ActivityNote(
            customer_id=customer_id,
            activity_id=activity_id,
            author_user_id=author_user_id,
            visibility=visibility,
            body=body,
        )
        db.add(note)
        return note


class TimelineService:
    @staticmethod
    def record(
        db,
        *,
        customer_id,
        event_type,
        source_module,
        summary,
        actor_type=ActorType.SYSTEM,
        actor_user_id=None,
        actor_label=None,
        reference_type=None,
        reference_id=None,
        occurred_at=None,
    ):
        event = TimelineEvent(
            customer_id=customer_id,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            source_module=source_module,
            event_type=event_type,
            summary=summary,
            reference_type=reference_type,
            reference_id=reference_id,
            occurred_at=occurred_at or _utcnow(),
        )
        db.add(event)
        return event

    @staticmethod
    def record_from_domain_event(event):
        db = SessionLocal()
        try:
            db.add(
                TimelineEvent(
                    customer_id=event.customer_id,
                    actor_type=event.actor_type,
                    actor_user_id=event.actor_user_id,
                    source_module=event.source_module,
                    event_type=event.event_type,
                    summary=event.summary,
                    reference_type=event.reference_type,
                    reference_id=event.reference_id,
                    occurred_at=event.occurred_at,
                )
            )
            db.commit()
        except Exception:
            logger.exception("failed to persist timeline event %s", event.event_type)
        finally:
            db.close()
