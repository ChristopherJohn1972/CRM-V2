import sqlalchemy as sa
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from activities.models import Activity, ActivityNote, TimelineEvent
from activities.serializers import (
    ActivitySerializer,
    ActivityWriteSerializer,
    NoteSerializer,
    NoteWriteSerializer,
    TimelineEventSerializer,
)
from activities.services import ActivityService, NoteService
from clients.access import get_customer_for_request
from common import audit
from common.db import SessionLocal
from common.events import DomainEvent, EventBus
from common.exceptions import NotFoundError, PermissionDeniedError
from iam.models import User

PERMISSION_ACTIVITY_READ = "activities.activity.read"
PERMISSION_ACTIVITY_CREATE = "activities.activity.create"
PERMISSION_ACTIVITY_UPDATE = "activities.activity.update"
PERMISSION_ACTIVITY_COMPLETE = "activities.activity.complete"
PERMISSION_NOTE_READ = "activities.note.read"
PERMISSION_NOTE_CREATE = "activities.note.create"
PERMISSION_NOTE_UPDATE = "activities.note.update"
PERMISSION_NOTE_DELETE = "activities.note.delete"


def _page(request, db, query, total, page_size):
    try:
        page_number = int(request.query_params.get("page", 1))
    except (TypeError, ValueError):
        page_number = 1
    page_number = max(1, page_number)
    rows = (
        db.execute(query.limit(page_size).offset((page_number - 1) * page_size))
        .scalars()
        .all()
    )
    return rows, total, page_number


class CustomerActivityListView(APIView):
    def get(self, request, customer_id):
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_ACTIVITY_READ)
            base = sa.select(Activity).where(Activity.customer_id == customer_id)
            total = db.execute(sa.select(sa.func.count()).select_from(base.subquery())).scalar()
            stmt = base.order_by(sa.desc(Activity.created_at))
            page_size = int(request.query_params.get("page_size", 20))
            rows, _, page_number = _page(request, db, stmt, total, page_size)
            data = ActivitySerializer(rows, many=True).data
            return Response({"count": total, "page": page_number, "page_size": page_size, "results": data})
        finally:
            db.close()

    def post(self, request, customer_id):
        principal = request.user
        serializer = ActivityWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_ACTIVITY_CREATE)
            activity = ActivityService.create(
                db,
                customer_id=customer_id,
                actor_user_id=principal.user_id,
                **serializer.validated_data,
            )
            db.add(activity)
            db.flush()
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="activity.created",
                resource_type="activities",
                resource_id=activity.activity_id,
                description=f"Activity '{activity.subject}' created for customer {customer_id}",
                request=request,
            )
            db.commit()
            db.refresh(activity)
            EventBus.publish(
                DomainEvent(
                    event_type="ActivityCreated",
                    customer_id=customer_id,
                    source_module="activities",
                    actor_user_id=principal.user_id,
                    actor_type="INTERNAL_USER",
                    summary=f"Activity '{activity.subject}' created",
                    reference_type="activities",
                    reference_id=activity.activity_id,
                )
            )
            return Response(ActivitySerializer(activity).data, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class CustomerActivityDetailView(APIView):
    action = None

    def _get(self, db, request, customer_id, activity_id):
        get_customer_for_request(db, request, customer_id, permission=PERMISSION_ACTIVITY_READ)
        activity = db.get(Activity, activity_id)
        if activity is None or activity.customer_id != customer_id:
            raise NotFoundError("Activity not found.")
        return activity

    def patch(self, request, customer_id, activity_id):
        principal = request.user
        serializer = ActivityWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            activity = self._get(db, request, customer_id, activity_id)
            if not principal.has_permission(PERMISSION_ACTIVITY_UPDATE):
                raise PermissionDeniedError()
            for key, value in serializer.validated_data.items():
                setattr(activity, key, value)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="activity.updated",
                resource_type="activities",
                resource_id=activity.activity_id,
                description=f"Activity {activity_id} updated",
                request=request,
            )
            db.commit()
            db.refresh(activity)
            return Response(ActivitySerializer(activity).data)
        finally:
            db.close()

    def post(self, request, customer_id, activity_id):
        if self.action != "complete":
            from rest_framework import status as _status

            return Response(
                {"detail": "Method not allowed."},
                status=_status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        principal = request.user
        db = SessionLocal()
        try:
            activity = self._get(db, request, customer_id, activity_id)
            if not principal.has_permission(PERMISSION_ACTIVITY_COMPLETE):
                raise PermissionDeniedError()
            ActivityService.complete(db, activity, principal.user_id)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="activity.completed",
                resource_type="activities",
                resource_id=activity.activity_id,
                description=f"Activity {activity_id} completed",
                request=request,
            )
            db.commit()
            db.refresh(activity)
            return Response(ActivitySerializer(activity).data)
        finally:
            db.close()


class CustomerNoteListView(APIView):
    def get(self, request, customer_id):
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_NOTE_READ)
            rows = db.execute(
                sa.select(ActivityNote)
                .where(ActivityNote.customer_id == customer_id)
                .order_by(sa.desc(ActivityNote.created_at))
            ).scalars().all()
            user_map = _load_users(db, [n.author_user_id for n in rows])
            return Response(NoteSerializer(rows, many=True, context={"user_map": user_map}).data)
        finally:
            db.close()

    def post(self, request, customer_id):
        principal = request.user
        serializer = NoteWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_NOTE_CREATE)
            note = NoteService.create(
                db,
                customer_id=customer_id,
                author_user_id=principal.user_id,
                **serializer.validated_data,
            )
            db.add(note)
            db.commit()
            db.refresh(note)
            return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class CustomerNoteDetailView(APIView):
    def _get(self, db, request, customer_id, note_id):
        get_customer_for_request(db, request, customer_id, permission=PERMISSION_NOTE_READ)
        note = db.get(ActivityNote, note_id)
        if note is None or note.customer_id != customer_id:
            raise NotFoundError("Note not found.")
        return note

    def patch(self, request, customer_id, note_id):
        principal = request.user
        serializer = NoteWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            note = self._get(db, request, customer_id, note_id)
            if not principal.has_permission(PERMISSION_NOTE_UPDATE):
                raise PermissionDeniedError()
            for key, value in serializer.validated_data.items():
                setattr(note, key, value)
            db.commit()
            db.refresh(note)
            return Response(NoteSerializer(note).data)
        finally:
            db.close()

    def delete(self, request, customer_id, note_id):
        principal = request.user
        db = SessionLocal()
        try:
            note = self._get(db, request, customer_id, note_id)
            if not principal.has_permission(PERMISSION_NOTE_DELETE):
                raise PermissionDeniedError()
            db.delete(note)
            db.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            db.close()


class CustomerTimelineView(APIView):
    def get(self, request, customer_id):
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id, permission=PERMISSION_ACTIVITY_READ)
            base = sa.select(TimelineEvent).where(TimelineEvent.customer_id == customer_id)
            total = db.execute(sa.select(sa.func.count()).select_from(base.subquery())).scalar()
            stmt = base.order_by(sa.desc(TimelineEvent.occurred_at))
            page_size = int(request.query_params.get("page_size", 30))
            rows, _, page_number = _page(request, db, stmt, total, page_size)
            user_map = _load_users(db, [row.actor_user_id for row in rows])
            data = TimelineEventSerializer(rows, many=True, context={"user_map": user_map}).data
            return Response({"count": total, "page": page_number, "page_size": page_size, "results": data})
        finally:
            db.close()


def _load_users(db, user_ids):
    ids = {i for i in user_ids if i is not None}
    if not ids:
        return {}
    users = db.execute(sa.select(User).where(User.user_id.in_(ids))).scalars().all()
    return {u.user_id: u for u in users}
