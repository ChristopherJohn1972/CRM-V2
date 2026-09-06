import logging
import sqlalchemy as sa
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from iam.permissions import UserPrincipal
from event_engine.models import EventOutbox
from event_engine.services import EventProcessingService

logger = logging.getLogger(__name__)

PERMISSION_EVENT_OUTBOX_MANAGE = "event.outbox.manage"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError(f"Missing required permission: {code}")


class EventOutboxProcessView(APIView):
    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_EVENT_OUTBOX_MANAGE)

        batch_size = request.data.get("batch_size", 50)
        session = SessionLocal()
        try:
            processed = EventProcessingService.process_pending(session, batch_size=batch_size)
            session.commit()
            return Response({"processed": processed})
        finally:
            session.close()


class EventOutboxRetryView(APIView):
    def post(self, request, event_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_EVENT_OUTBOX_MANAGE)

        session = SessionLocal()
        try:
            event = EventProcessingService.retry_failed(session, event_id)
            session.commit()
            return Response({"event_id": event.event_id, "status": event.status})
        finally:
            session.close()


class EventOutboxListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_EVENT_OUTBOX_MANAGE)

        session = SessionLocal()
        try:
            status_filter = request.query_params.get("status", "PENDING")
            stmt = (
                sa.select(EventOutbox)
                .where(EventOutbox.status == status_filter)
                .order_by(sa.desc(EventOutbox.created_at))
                .limit(100)
            )
            rows = session.execute(stmt).scalars().all()
            data = [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "aggregate_type": e.aggregate_type,
                    "aggregate_id": e.aggregate_id,
                    "status": e.status,
                    "retry_count": e.retry_count,
                    "last_error": e.last_error,
                    "created_at": str(e.created_at),
                }
                for e in rows
            ]
            return Response({"results": data})
        finally:
            session.close()
