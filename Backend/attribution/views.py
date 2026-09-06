import logging
import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from iam.permissions import UserPrincipal
from attribution.models import AttributionEvent, AttributionResult
from attribution.serializers import (
    AttributionEventReadSerializer,
    AttributionEventWriteSerializer,
    AttributionResultReadSerializer,
)
from attribution.services import AttributionAnalyticsService, AttributionComputationService, AttributionTrackingService

logger = logging.getLogger(__name__)

PERMISSION_ATTRIBUTION_VIEW = "attribution.view"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError(f"Missing required permission: {code}")


class AttributionTouchpointView(APIView):
    def post(self, request):
        principal = _principal(request)
        if principal is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        serializer = AttributionEventWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            ae = AttributionTrackingService.record_touchpoint(
                session, payload, principal.user_id, request=request
            )
            return Response(
                {"id": ae.id, "event_type": ae.event_type},
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class AttributionComputeView(APIView):
    def post(self, request):
        principal = _principal(request)
        if principal is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        order_id = request.data.get("order_id")
        customer_id = request.data.get("customer_id")
        order_amount = request.data.get("order_amount", 0)

        if not order_id or not customer_id:
            from common.exceptions import ValidationError_
            raise ValidationError_("order_id and customer_id are required.")

        session = SessionLocal()
        try:
            results = AttributionComputationService.compute_for_order(
                session, order_id, customer_id, order_amount, request=request
            )
            data = [AttributionResultReadSerializer(r).data for r in results]
            return Response({"results": data}, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class AttributionRevenueByCampaignView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_ATTRIBUTION_VIEW)

        session = SessionLocal()
        try:
            results = AttributionAnalyticsService.revenue_by_campaign(session)
            data = [
                {
                    "campaign_id": row.campaign_id,
                    "total_revenue": float(row.total_revenue or 0),
                    "order_count": row.order_count,
                }
                for row in results
            ]
            return Response({"results": data})
        finally:
            session.close()


class AttributionTouchpointListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_ATTRIBUTION_VIEW)

        session = SessionLocal()
        try:
            stmt = sa.select(AttributionEvent).order_by(sa.desc(AttributionEvent.touch_point_at))

            customer_id = request.query_params.get("customer_id")
            if customer_id:
                stmt = stmt.where(AttributionEvent.customer_id == int(customer_id))

            campaign_id = request.query_params.get("campaign_id")
            if campaign_id:
                stmt = stmt.where(AttributionEvent.campaign_id == int(campaign_id))

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
            offset = (page_number - 1) * page_size

            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            rows = session.execute(stmt.limit(page_size).offset(offset)).scalars().all()
            data = [AttributionEventReadSerializer(row).data for row in rows]

            return Response({
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": data,
            })
        finally:
            session.close()
