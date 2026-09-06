import logging
import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from iam.permissions import UserPrincipal
from referrals.models import ReferralCode, ReferralEvent, ReferralQualification
from referrals.serializers import (
    ReferralCodeReadSerializer,
    ReferralCodeWriteSerializer,
    ReferralEventReadSerializer,
    ReferralQualificationReadSerializer,
)
from referrals.services import (
    ReferralAntiAbuseService,
    ReferralCodeService,
    ReferralLifecycleService,
    ReferralQualificationService,
)

logger = logging.getLogger(__name__)

PERMISSION_REFERRAL_VIEW = "referral.view"
PERMISSION_REFERRAL_MANAGE = "referral.manage"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError(f"Missing required permission: {code}")


class ReferralCodeListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_REFERRAL_VIEW)

        session = SessionLocal()
        try:
            stmt = sa.select(ReferralCode).order_by(sa.desc(ReferralCode.id))

            customer_id = request.query_params.get("customer_id")
            if customer_id:
                stmt = stmt.where(ReferralCode.referrer_customer_id == int(customer_id))

            status_filter = request.query_params.get("status")
            if status_filter:
                stmt = stmt.where(ReferralCode.status == status_filter)

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
            offset = (page_number - 1) * page_size

            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            rows = session.execute(stmt.limit(page_size).offset(offset)).scalars().all()
            data = [ReferralCodeReadSerializer(row).data for row in rows]

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
        _require_permission(principal, PERMISSION_REFERRAL_MANAGE)

        serializer = ReferralCodeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        customer_id = payload.pop("customer_id", None)
        if not customer_id:
            from common.exceptions import ValidationError_
            raise ValidationError_("customer_id is required.")

        session = SessionLocal()
        try:
            rc = ReferralCodeService.create_code(
                session, customer_id, payload, principal.user_id, request=request
            )
            return Response(
                ReferralCodeReadSerializer(rc).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class ReferralCodeDetailView(APIView):
    def get(self, request, code_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_REFERRAL_VIEW)

        session = SessionLocal()
        try:
            rc = session.get(ReferralCode, code_id)
            if rc is None:
                from common.exceptions import NotFoundError
                raise NotFoundError("Referral code not found.")
            return Response(ReferralCodeReadSerializer(rc).data)
        finally:
            session.close()


class ReferralTrackView(APIView):
    def get(self, request, code):
        session = SessionLocal()
        try:
            rc = ReferralCodeService.validate_code(session, code)
            ReferralLifecycleService.record_event(
                session, rc.id, 0, "CODE_CLICKED", request=request
            )
            return Response({
                "code": rc.code,
                "referrer_customer_id": rc.referrer_customer_id,
                "status": rc.status,
            })
        finally:
            session.close()


class ReferralEventListView(APIView):
    def get(self, request, code_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_REFERRAL_VIEW)

        session = SessionLocal()
        try:
            stmt = (
                sa.select(ReferralEvent)
                .where(ReferralEvent.referral_code_id == code_id)
                .order_by(sa.desc(ReferralEvent.occurred_at))
            )
            rows = session.execute(stmt).scalars().all()
            data = [ReferralEventReadSerializer(row).data for row in rows]
            return Response({"results": data})
        finally:
            session.close()
