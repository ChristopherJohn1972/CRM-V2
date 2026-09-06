import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.client import AccountingDataUnavailable, build_gateway
from clients.access import get_customer_for_request
from common.db import SessionLocal
from common.exceptions import PermissionDeniedError

logger = logging.getLogger(__name__)

PERMISSION_ACCOUNTING_SUMMARY = "accounting.summary.read"
PERMISSION_ACCOUNTING_TRANSACTIONS = "accounting.transactions.read"


def _gateway():
    return build_gateway(settings)


class CustomerAccountingSummaryView(APIView):
    def get(self, request, customer_id):
        principal = request.user
        if not principal.has_permission(PERMISSION_ACCOUNTING_SUMMARY):
            raise PermissionDeniedError()
        db = SessionLocal()
        try:
            customer = get_customer_for_request(db, request, customer_id)
            try:
                data = _gateway().fetch_summary(customer.customer_id, customer.customer_number)
                data = data or {}
                return Response({"available": True, "data": data})
            except AccountingDataUnavailable as exc:
                return Response(
                    {
                        "available": False,
                        "reason": exc.reason,
                        "message": "Financial data could not be loaded from the accounting module.",
                    }
                )
        finally:
            db.close()


class CustomerAccountingTransactionsView(APIView):
    def get(self, request, customer_id):
        principal = request.user
        if not principal.has_permission(PERMISSION_ACCOUNTING_TRANSACTIONS):
            raise PermissionDeniedError()
        db = SessionLocal()
        try:
            customer = get_customer_for_request(db, request, customer_id)
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            try:
                data = _gateway().fetch_transactions(
                    customer.customer_id, customer.customer_number, page, page_size
                )
                data = data or {}
                return Response({"available": True, "data": data})
            except AccountingDataUnavailable as exc:
                return Response(
                    {
                        "available": False,
                        "reason": exc.reason,
                        "message": "Financial data could not be loaded from the accounting module.",
                    }
                )
        finally:
            db.close()
