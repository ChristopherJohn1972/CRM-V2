import logging
import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from iam.permissions import UserPrincipal
from leads.access import can_access_lead, scope_lead_queryset
from leads.models import Lead, LeadFollowUp, LeadQualification
from leads.serializers import (
    LeadConsentWriteSerializer,
    LeadFollowUpReadSerializer,
    LeadFollowUpWriteSerializer,
    LeadQualifySerializer,
    LeadReadSerializer,
    LeadUpdateSerializer,
    LeadWriteSerializer,
)
from leads.services import (
    LeadConsentService,
    LeadFollowUpService,
    LeadQualificationService,
    LeadService,
)

logger = logging.getLogger(__name__)

PERMISSION_LEAD_VIEW = "lead.view"
PERMISSION_LEAD_CREATE = "lead.create"
PERMISSION_LEAD_EDIT = "lead.edit"
PERMISSION_LEAD_ASSIGN = "lead.assign"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError(f"Missing required permission: {code}")


def _get_lead(db, request, lead_id):
    from common.exceptions import NotFoundError, PermissionDeniedError
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError("Lead not found.")
    if not can_access_lead(db, _principal(request), lead):
        raise PermissionDeniedError()
    return lead


class LeadListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_VIEW)

        session = SessionLocal()
        try:
            stmt = sa.select(Lead)
            stmt = scope_lead_queryset(session, principal, stmt)

            search = request.query_params.get("search")
            if search:
                stmt = stmt.where(
                    sa.or_(
                        Lead.first_name.ilike(f"%{search}%"),
                        Lead.last_name.ilike(f"%{search}%"),
                        Lead.email.ilike(f"%{search}%"),
                        Lead.company.ilike(f"%{search}%"),
                    )
                )

            status_filter = request.query_params.get("status")
            if status_filter:
                stmt = stmt.where(Lead.status == status_filter)

            assigned_to = request.query_params.get("assigned_to")
            if assigned_to:
                stmt = stmt.where(Lead.assigned_user_id == int(assigned_to))

            stmt = stmt.order_by(sa.desc(Lead.lead_id))

            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
            offset = (page_number - 1) * page_size

            rows = session.execute(stmt.limit(page_size).offset(offset)).scalars().all()
            data = [LeadReadSerializer(row).data for row in rows]

            return Response({
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": data,
            })
        finally:
            session.close()

    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_CREATE)

        serializer = LeadWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            lead = LeadService.create_lead(
                session, payload, principal.user_id, request=request
            )
            return Response(
                LeadReadSerializer(lead).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class LeadDetailView(APIView):
    def get(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_VIEW)

        session = SessionLocal()
        try:
            lead = _get_lead(session, request, lead_id)
            return Response(LeadReadSerializer(lead).data)
        finally:
            session.close()

    def put(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_EDIT)

        serializer = LeadUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            lead = LeadService.update_lead(
                session, lead_id, payload, principal.user_id, request=request
            )
            return Response(LeadReadSerializer(lead).data)
        finally:
            session.close()

    def delete(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_EDIT)

        session = SessionLocal()
        try:
            LeadService.delete_lead(
                session, lead_id, principal.user_id, request=request
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


class LeadTransitionView(APIView):
    def post(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_EDIT)

        new_status = request.data.get("status")
        if not new_status:
            from common.exceptions import ValidationError_
            raise ValidationError_("Status is required.")

        session = SessionLocal()
        try:
            lead = LeadService.transition_lead(
                session, lead_id, new_status, principal.user_id, request=request
            )
            return Response(LeadReadSerializer(lead).data)
        finally:
            session.close()


class LeadQualifyView(APIView):
    def post(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_EDIT)

        serializer = LeadQualifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            qual = LeadQualificationService.qualify_lead(
                session, lead_id, payload, principal.user_id, request=request
            )
            return Response(
                {"id": qual.id, "score": qual.score, "qualified_at": str(qual.qualified_at)},
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class LeadFollowUpListView(APIView):
    def get(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_VIEW)

        session = SessionLocal()
        try:
            _get_lead(session, request, lead_id)
            stmt = sa.select(LeadFollowUp).where(LeadFollowUp.lead_id == lead_id)
            stmt = stmt.order_by(sa.desc(LeadFollowUp.scheduled_at))
            rows = session.execute(stmt).scalars().all()
            data = [LeadFollowUpReadSerializer(row).data for row in rows]
            return Response({"results": data})
        finally:
            session.close()

    def post(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_EDIT)

        serializer = LeadFollowUpWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            fu = LeadFollowUpService.create_follow_up(
                session, lead_id, payload, principal.user_id, request=request
            )
            return Response(
                LeadFollowUpReadSerializer(fu).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class LeadFollowUpCompleteView(APIView):
    def put(self, request, lead_id, follow_up_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_EDIT)

        session = SessionLocal()
        try:
            fu = LeadFollowUpService.complete_follow_up(
                session, lead_id, follow_up_id, dict(request.data), principal.user_id, request=request
            )
            return Response(LeadFollowUpReadSerializer(fu).data)
        finally:
            session.close()


class LeadConsentView(APIView):
    def post(self, request, lead_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_LEAD_EDIT)

        serializer = LeadConsentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            consent = LeadConsentService.record_consent(
                session, lead_id, payload, principal.user_id, request=request
            )
            return Response(
                {"id": consent.id, "consent_type": consent.consent_type, "granted": consent.granted},
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()
