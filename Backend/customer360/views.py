import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.client import AccountingDataUnavailable, build_gateway
from clients.access import get_customer_for_request
from common.db import SessionLocal
from common.exceptions import PermissionDeniedError
from customer360.serializers import Customer360Serializer
from customer360.services import Customer360Service

logger = logging.getLogger(__name__)

PERMISSION_360_VIEW = "customer360.view"


class Customer360View(APIView):
    def get(self, request, customer_id):
        principal = request.user
        if not principal.has_permission(PERMISSION_360_VIEW):
            raise PermissionDeniedError()
        db = SessionLocal()
        try:
            customer = get_customer_for_request(db, request, customer_id)
            summary = Customer360Service.build_summary(db, customer)

            accounting = None
            try:
                accounting = {
                    "available": True,
                    "data": build_gateway(settings).fetch_summary(
                        customer.customer_id, customer.customer_number
                    ),
                }
            except AccountingDataUnavailable as exc:
                accounting = {
                    "available": False,
                    "reason": exc.reason,
                    "message": "Financial data could not be loaded from the accounting module.",
                }
            except Exception:
                logger.exception("unexpected accounting integration failure")
                accounting = {
                    "available": False,
                    "reason": "accounting_error",
                    "message": "Financial data could not be loaded from the accounting module.",
                }

            summary["accounting"] = accounting

            permissions = {
                "can_edit": principal.has_permission("clients.customer.update"),
                "can_delete": principal.has_permission("clients.customer.delete"),
                "can_change_status": principal.has_permission("clients.customer.status.change"),
                "can_manage_portal": principal.has_permission("portal.user.manage"),
            }
            summary["permissions"] = permissions

            return Response(Customer360Serializer(summary).data)
        finally:
            db.close()
