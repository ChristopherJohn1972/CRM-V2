import logging
import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from iam.permissions import UserPrincipal
from momentum.models import MomentumLedger, MomentumRule
from momentum.serializers import (
    MomentumBalanceReadSerializer,
    MomentumEntryReadSerializer,
    MomentumRuleReadSerializer,
    MomentumRuleWriteSerializer,
)
from momentum.services import MomentumLedgerService, MomentumRuleService

logger = logging.getLogger(__name__)

PERMISSION_MOMENTUM_VIEW = "momentum.view"
PERMISSION_MOMENTUM_MANAGE = "momentum.manage"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError(f"Missing required permission: {code}")


class MomentumBalanceView(APIView):
    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_MOMENTUM_VIEW)

        session = SessionLocal()
        try:
            balance = MomentumLedgerService.get_balance(session, customer_id)
            return Response({
                "customer_id": customer_id,
                "balance": balance,
            })
        finally:
            session.close()


class MomentumLedgerView(APIView):
    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_MOMENTUM_VIEW)

        session = SessionLocal()
        try:
            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
            offset = (page_number - 1) * page_size

            entries = MomentumLedgerService.get_ledger_entries(session, customer_id, limit=page_size, offset=offset)
            data = [MomentumEntryReadSerializer(e).data for e in entries]

            total = session.execute(
                sa.select(sa.func.count()).where(MomentumLedger.customer_id == customer_id)
            ).scalar()

            return Response({
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": data,
            })
        finally:
            session.close()


class MomentumEarnView(APIView):
    def post(self, request):
        principal = _principal(request)
        if principal is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        customer_id = request.data.get("customer_id")
        order_id = request.data.get("order_id")
        order_amount = request.data.get("order_amount", 0)

        if not customer_id or not order_id:
            from common.exceptions import ValidationError_
            raise ValidationError_("customer_id and order_id are required.")

        session = SessionLocal()
        try:
            entry = MomentumLedgerService.earn_for_purchase(
                session, customer_id, order_id, order_amount, request=request
            )
            if entry:
                return Response(
                    MomentumEntryReadSerializer(entry).data,
                    status=status.HTTP_201_CREATED,
                )
            return Response({"message": "No points earned for this purchase."})
        finally:
            session.close()


class MomentumAdjustView(APIView):
    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_MOMENTUM_MANAGE)

        customer_id = request.data.get("customer_id")
        points = request.data.get("points")
        description = request.data.get("description", "Manual adjustment")

        if not customer_id or points is None:
            from common.exceptions import ValidationError_
            raise ValidationError_("customer_id and points are required.")

        session = SessionLocal()
        try:
            entry = MomentumLedgerService.record_entry(
                session,
                customer_id=customer_id,
                entry_type="ADJUST",
                points=abs(points) if points >= 0 else -abs(points),
                source_type="MANUAL",
                description=description,
                user_id=principal.user_id,
                request=request,
            )
            return Response(
                MomentumEntryReadSerializer(entry).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class MomentumRuleListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_MOMENTUM_VIEW)

        session = SessionLocal()
        try:
            rules = MomentumRuleService.get_active_rules(session)
            data = [MomentumRuleReadSerializer(r).data for r in rules]
            return Response({"results": data})
        finally:
            session.close()

    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_MOMENTUM_MANAGE)

        serializer = MomentumRuleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            rule = MomentumRuleService.create_rule(
                session, payload, principal.user_id, request=request
            )
            return Response(
                MomentumRuleReadSerializer(rule).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class MomentumRuleDetailView(APIView):
    def put(self, request, rule_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_MOMENTUM_MANAGE)

        serializer = MomentumRuleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            rule = MomentumRuleService.update_rule(
                session, rule_id, payload, principal.user_id, request=request
            )
            return Response(MomentumRuleReadSerializer(rule).data)
        finally:
            session.close()
