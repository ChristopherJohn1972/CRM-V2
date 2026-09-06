import logging

import sqlalchemy as sa
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.models import Customer
from common.db import SessionLocal
from iam.permissions import UserPrincipal
from sales_orders.access import can_access_order, scope_order_queryset
from sales_orders.models import (
    OrderPayment,
    Receipt,
    SalesOrder,
    SalesOrderEvent,
    SalesOrderItem,
)
from sales_orders.serializers import (
    CalculationRequestSerializer,
    CalculationResponseSerializer,
    OrderActionSerializer,
    PaymentReadSerializer,
    PaymentWriteSerializer,
    ReceiptReadSerializer,
    ReceiptVoidSerializer,
    SalesOrderItemReadSerializer,
    SalesOrderItemWriteSerializer,
    SalesOrderReadSerializer,
    SalesOrderUpdateSerializer,
    SalesOrderWriteSerializer,
)
from sales_orders.services import (
    PaymentService,
    QuoteConversionService,
    ReceiptService,
    ReceiptVerificationService,
    SalesOrderCalculationService,
    SalesOrderService,
    SalesOrderWorkflowService,
)

logger = logging.getLogger(__name__)

PERMISSION_SO_READ = "sales_order.sales_order.read"
PERMISSION_SO_CREATE = "sales_order.sales_order.create"
PERMISSION_SO_UPDATE = "sales_order.sales_order.update"
PERMISSION_SO_DELETE = "sales_order.sales_order.delete"
PERMISSION_SO_CALCULATE = "sales_order.sales_order.calculate"
PERMISSION_SO_WORKFLOW = "sales_order.sales_order.workflow"
PERMISSION_SO_CONVERT = "quotes.quote.convert_to_order"
PERMISSION_PAYMENT_READ = "sales_order.payment.read"
PERMISSION_PAYMENT_RECORD = "sales_order.payment.record"
PERMISSION_PAYMENT_CONFIRM = "sales_order.payment.confirm"
PERMISSION_PAYMENT_REVERSE = "sales_order.payment.reverse"
PERMISSION_RECEIPT_READ = "sales_order.receipt.read"
PERMISSION_RECEIPT_VOID = "sales_order.receipt.void"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError(f"Missing required permission: {code}")


def _get_order(db, request, order_id):
    from common.exceptions import NotFoundError
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise NotFoundError("Sales order not found.")
    if not can_access_order(db, _principal(request), order):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError()
    return order


def _get_item(db, order, item_id):
    from common.exceptions import NotFoundError
    item = db.get(SalesOrderItem, item_id)
    if item is None or item.order_id != order.order_id:
        raise NotFoundError("Sales order item not found.")
    return item


def _get_payment(db, payment_id):
    from common.exceptions import NotFoundError
    payment = db.get(OrderPayment, payment_id)
    if payment is None:
        raise NotFoundError("Payment not found.")
    return payment


def _get_receipt(db, receipt_id):
    from common.exceptions import NotFoundError
    receipt = db.get(Receipt, receipt_id)
    if receipt is None:
        raise NotFoundError("Receipt not found.")
    return receipt


# ---------------------------------------------------------------------------
# Order CRUD Views
# ---------------------------------------------------------------------------

class SalesOrderListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_READ)

        session = SessionLocal()
        try:
            stmt = sa.select(SalesOrder)
            stmt = scope_order_queryset(session, principal, stmt)
            stmt = stmt.where(SalesOrder.deleted_at.is_(None))

            search = request.query_params.get("search")
            if search:
                like = f"%{search}%"
                stmt = stmt.where(
                    sa.or_(
                        SalesOrder.order_number.like(like),
                    )
                )

            order_status = request.query_params.get("status")
            if order_status:
                stmt = stmt.where(SalesOrder.status == order_status)

            customer_id = request.query_params.get("customer_id")
            if customer_id:
                stmt = stmt.where(SalesOrder.customer_id == int(customer_id))

            source = request.query_params.get("source")
            if source:
                stmt = stmt.where(SalesOrder.source == source)

            stmt = stmt.order_by(sa.desc(SalesOrder.order_id))
            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            try:
                page_number = int(request.query_params.get(paginator.page_query_param, 1))
            except (TypeError, ValueError):
                page_number = 1
            page_number = max(1, page_number)

            rows = session.execute(
                stmt.limit(page_size).offset((page_number - 1) * page_size)
            ).scalars().all()

            data = []
            for order in rows:
                items = session.execute(
                    sa.select(SalesOrderItem)
                    .where(SalesOrderItem.order_id == order.order_id)
                    .order_by(SalesOrderItem.sort_order)
                ).scalars().all()
                order_data = SalesOrderReadSerializer(order).data
                order_data["items"] = SalesOrderItemReadSerializer(items, many=True).data
                data.append(order_data)

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
        _require_permission(principal, PERMISSION_SO_CREATE)

        serializer = SalesOrderWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            order = SalesOrderService.create_order(
                session, payload, principal.user_id, request=request
            )

            items = session.execute(
                sa.select(SalesOrderItem)
                .where(SalesOrderItem.order_id == order.order_id)
                .order_by(SalesOrderItem.sort_order)
            ).scalars().all()

            data = SalesOrderReadSerializer(order).data
            data["items"] = SalesOrderItemReadSerializer(items, many=True).data
            return Response(data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class SalesOrderDetailView(APIView):
    def get(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_READ)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            items = session.execute(
                sa.select(SalesOrderItem)
                .where(SalesOrderItem.order_id == order.order_id)
                .order_by(SalesOrderItem.sort_order)
            ).scalars().all()

            data = SalesOrderReadSerializer(order).data
            data["items"] = SalesOrderItemReadSerializer(items, many=True).data
            return Response(data)
        finally:
            session.close()

    def patch(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_UPDATE)

        serializer = SalesOrderUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            order = SalesOrderService.update_order(
                session, order, payload, principal.user_id, request=request
            )
            data = SalesOrderReadSerializer(order).data
            items = session.execute(
                sa.select(SalesOrderItem)
                .where(SalesOrderItem.order_id == order.order_id)
                .order_by(SalesOrderItem.sort_order)
            ).scalars().all()
            data["items"] = SalesOrderItemReadSerializer(items, many=True).data
            return Response(data)
        finally:
            session.close()

    def delete(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_DELETE)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            SalesOrderService.delete_order(
                session, order, principal.user_id, request=request
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Order Item Views
# ---------------------------------------------------------------------------

class SalesOrderItemListView(APIView):
    def post(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_UPDATE)

        serializer = SalesOrderItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item_data = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            item = SalesOrderService.add_item(
                session, order, item_data, principal.user_id, request=request
            )
            return Response(SalesOrderItemReadSerializer(item).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class SalesOrderItemDetailView(APIView):
    def patch(self, request, order_id, item_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_UPDATE)

        serializer = SalesOrderItemWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item_data = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            item = _get_item(session, order, item_id)
            item = SalesOrderService.update_item(
                session, order, item, item_data, principal.user_id, request=request
            )
            return Response(SalesOrderItemReadSerializer(item).data)
        finally:
            session.close()

    def delete(self, request, order_id, item_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_UPDATE)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            item = _get_item(session, order, item_id)
            SalesOrderService.remove_item(
                session, order, item, principal.user_id, request=request
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Calculation View
# ---------------------------------------------------------------------------

class SalesOrderCalculationView(APIView):
    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_CALCULATE)

        serializer = CalculationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        items_data = [dict(item) for item in data["items"]]
        order_discount = None
        if data.get("order_discount_type"):
            order_discount = {
                "discount_type": data["order_discount_type"],
                "discount_value": data.get("order_discount_value", 0),
            }

        result = SalesOrderCalculationService.calculate_order_state(
            items_data,
            adjustments_data=data.get("adjustments", []),
            order_discount=order_discount,
            additional_charges=data.get("additional_charges", 0),
            currency=data.get("currency", "KES"),
        )

        for line in result["lines"]:
            for k, v in line.items():
                line[k] = str(v)
        result["subtotal"] = str(result["subtotal"])
        result["total_discount"] = str(result["total_discount"])
        result["total_tax"] = str(result["total_tax"])
        result["additional_charges"] = str(result["additional_charges"])
        result["grand_total"] = str(result["grand_total"])

        return Response(result)


# ---------------------------------------------------------------------------
# Workflow Views
# ---------------------------------------------------------------------------

class SalesOrderConfirmView(APIView):
    def post(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_WORKFLOW)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            order = SalesOrderWorkflowService.confirm(
                session, order, principal.user_id, request=request
            )
            return Response(SalesOrderReadSerializer(order).data)
        finally:
            session.close()


class SalesOrderCancelView(APIView):
    def post(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_WORKFLOW)

        reason = request.data.get("reason")

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            order = SalesOrderWorkflowService.cancel(
                session, order, principal.user_id,
                reason=reason, request=request,
            )
            return Response(SalesOrderReadSerializer(order).data)
        finally:
            session.close()


class SalesOrderSubmitApprovalView(APIView):
    def post(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_WORKFLOW)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            order = SalesOrderWorkflowService.submit_for_approval(
                session, order, principal.user_id, request=request
            )
            return Response(SalesOrderReadSerializer(order).data)
        finally:
            session.close()


class SalesOrderApproveView(APIView):
    def post(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_WORKFLOW)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            order = SalesOrderWorkflowService.approve(
                session, order, principal.user_id, request=request
            )
            return Response(SalesOrderReadSerializer(order).data)
        finally:
            session.close()


class SalesOrderProcessingView(APIView):
    def post(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_WORKFLOW)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            order = SalesOrderWorkflowService.mark_processing(
                session, order, principal.user_id, request=request
            )
            return Response(SalesOrderReadSerializer(order).data)
        finally:
            session.close()


class SalesOrderFulfilledView(APIView):
    def post(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_WORKFLOW)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)
            order = SalesOrderWorkflowService.mark_fulfilled(
                session, order, principal.user_id, request=request
            )
            return Response(SalesOrderReadSerializer(order).data)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Activity View
# ---------------------------------------------------------------------------

class SalesOrderActivityView(APIView):
    def get(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_READ)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)

            events = session.execute(
                sa.select(SalesOrderEvent)
                .where(SalesOrderEvent.order_id == order.order_id)
                .order_by(sa.desc(SalesOrderEvent.occurred_at))
            ).scalars().all()

            data = []
            for event in events:
                data.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "actor_user_id": event.actor_user_id,
                    "actor_type": event.actor_type,
                    "description": event.description,
                    "metadata_": event.metadata_,
                    "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
                })

            return Response(data)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Payment Views
# ---------------------------------------------------------------------------

class PaymentListByOrderView(APIView):
    def get(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_PAYMENT_READ)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)

            payments = session.execute(
                sa.select(OrderPayment)
                .where(OrderPayment.order_id == order.order_id)
                .order_by(sa.desc(OrderPayment.created_at))
            ).scalars().all()

            data = PaymentReadSerializer(payments, many=True).data
            return Response(data)
        finally:
            session.close()


class PaymentListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_PAYMENT_READ)

        session = SessionLocal()
        try:
            stmt = sa.select(OrderPayment)

            order_id = request.query_params.get("order_id")
            if order_id:
                stmt = stmt.where(OrderPayment.order_id == int(order_id))

            customer_id = request.query_params.get("customer_id")
            if customer_id:
                stmt = stmt.where(OrderPayment.customer_id == int(customer_id))

            stmt = stmt.order_by(sa.desc(OrderPayment.created_at))

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            try:
                page_number = int(request.query_params.get(paginator.page_query_param, 1))
            except (TypeError, ValueError):
                page_number = 1
            page_number = max(1, page_number)

            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            rows = session.execute(
                stmt.limit(page_size).offset((page_number - 1) * page_size)
            ).scalars().all()

            data = PaymentReadSerializer(rows, many=True).data
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
        _require_permission(principal, PERMISSION_PAYMENT_RECORD)

        serializer = PaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            payment = PaymentService.record_payment(
                session, payload, principal.user_id, request=request
            )
            return Response(PaymentReadSerializer(payment).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class PaymentConfirmView(APIView):
    def post(self, request, payment_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_PAYMENT_CONFIRM)

        session = SessionLocal()
        try:
            payment = _get_payment(session, payment_id)
            receipt = PaymentService.confirm_payment(
                session, payment, principal.user_id, request=request
            )
            from sales_orders.serializers import ReceiptReadSerializer
            return Response(ReceiptReadSerializer(receipt).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class PaymentReverseView(APIView):
    def post(self, request, payment_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_PAYMENT_REVERSE)

        reason = request.data.get("reason")

        session = SessionLocal()
        try:
            payment = _get_payment(session, payment_id)
            payment = PaymentService.reverse_payment(
                session, payment, principal.user_id,
                reason=reason, request=request,
            )
            return Response(PaymentReadSerializer(payment).data)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Receipt Views
# ---------------------------------------------------------------------------

class ReceiptListView(APIView):
    def get(self, request, order_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_RECEIPT_READ)

        session = SessionLocal()
        try:
            order = _get_order(session, request, order_id)

            receipts = session.execute(
                sa.select(Receipt)
                .where(Receipt.order_id == order.order_id)
                .order_by(sa.desc(Receipt.created_at))
            ).scalars().all()

            data = ReceiptReadSerializer(receipts, many=True).data
            return Response(data)
        finally:
            session.close()


class ReceiptDetailView(APIView):
    def get(self, request, receipt_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_RECEIPT_READ)

        session = SessionLocal()
        try:
            receipt = _get_receipt(session, receipt_id)
            return Response(ReceiptReadSerializer(receipt).data)
        finally:
            session.close()


class ReceiptVoidView(APIView):
    def post(self, request, receipt_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_RECEIPT_VOID)

        serializer = ReceiptVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = SessionLocal()
        try:
            receipt = _get_receipt(session, receipt_id)
            ReceiptService.void_receipt(
                session, receipt, principal.user_id,
                reason=serializer.validated_data.get("reason"),
                request=request,
            )
            return Response(ReceiptReadSerializer(receipt).data)
        finally:
            session.close()


class ReceiptPdfView(APIView):
    def get(self, request, receipt_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_RECEIPT_READ)

        session = SessionLocal()
        try:
            receipt = _get_receipt(session, receipt_id)
            from sales_orders.services import SalesOrderCalculationService
            order = session.get(SalesOrder, receipt.order_id)
            payment = session.get(OrderPayment, receipt.payment_id)
            customer = session.get(Customer, receipt.customer_id)

            html_content = _render_receipt_html(receipt, order, payment, customer)
            return HttpResponse(html_content, content_type="text/html")
        finally:
            session.close()


class ReceiptVerifyView(APIView):
    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            from common.exceptions import ValidationError_
            raise ValidationError_("token query parameter is required.")

        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT")

        session = SessionLocal()
        try:
            result = ReceiptVerificationService.verify(
                session, token, ip_address=ip_address, user_agent=user_agent
            )
            return Response(result)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Quote Conversion View
# ---------------------------------------------------------------------------

class QuoteConvertToOrderView(APIView):
    def post(self, request, quote_id):
        from common.exceptions import NotFoundError
        from quotes.models import Quote
        from quotes.access import can_access_quote

        principal = _principal(request)
        _require_permission(principal, PERMISSION_SO_CONVERT)

        session = SessionLocal()
        try:
            quote = session.get(Quote, quote_id)
            if quote is None:
                raise NotFoundError("Quote not found.")
            if not can_access_quote(session, principal, quote):
                from common.exceptions import PermissionDeniedError
                raise PermissionDeniedError()

            order = QuoteConversionService.convert_quote_to_order(
                session, quote, principal.user_id, request=request
            )

            items = session.execute(
                sa.select(SalesOrderItem)
                .where(SalesOrderItem.order_id == order.order_id)
                .order_by(SalesOrderItem.sort_order)
            ).scalars().all()

            data = SalesOrderReadSerializer(order).data
            data["items"] = SalesOrderItemReadSerializer(items, many=True).data
            return Response(data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# HTML Receipt Renderer
# ---------------------------------------------------------------------------

def _render_receipt_html(receipt, order, payment, customer):
    company = receipt.company_profile_snapshot or {}
    company_name = company.get("legal_name") or company.get("display_name") or "CRM V2"
    company_address = company.get("address") or ""
    company_phone = company.get("phone") or ""
    company_email = company.get("email") or ""
    company_website = company.get("website") or ""

    customer_name = "N/A"
    if customer:
        customer_name = getattr(customer, "business_name", None) or getattr(customer, "full_name", None) or "N/A"

    order_number = order.order_number if order else "N/A"
    order_date = order.order_date.isoformat() if order and order.order_date else "N/A"
    payment_method = payment.payment_method if payment else "N/A"
    payment_reference = payment.payment_reference if payment else "N/A"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Receipt {receipt.receipt_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }}
        .receipt {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
        .receipt-header {{ background: linear-gradient(135deg, #1a5276 0%, #2e86c1 100%); color: white; padding: 30px; text-align: center; }}
        .receipt-header h1 {{ font-size: 28px; margin-bottom: 5px; }}
        .receipt-header .subtitle {{ font-size: 14px; opacity: 0.9; }}
        .receipt-body {{ padding: 30px; }}
        .receipt-meta {{ display: flex; justify-content: space-between; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #eee; }}
        .receipt-meta .left {{ text-align: left; }}
        .receipt-meta .right {{ text-align: right; }}
        .receipt-meta .label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .receipt-meta .value {{ font-size: 14px; font-weight: 600; margin-bottom: 8px; }}
        .receipt-details {{ margin-bottom: 25px; }}
        .receipt-details h3 {{ font-size: 16px; color: #333; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #2e86c1; }}
        .details-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .detail-item {{ padding: 8px 0; }}
        .detail-item .label {{ font-size: 12px; color: #666; }}
        .detail-item .value {{ font-size: 14px; font-weight: 500; }}
        .amount-box {{ background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
        .amount-box .amount {{ font-size: 36px; font-weight: 700; color: #1a5276; }}
        .amount-box .currency {{ font-size: 14px; color: #666; }}
        .verification {{ text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; }}
        .verification .token {{ font-family: monospace; font-size: 12px; color: #666; word-break: break-all; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; }}
        @media print {{ body {{ background: white; padding: 0; }} .receipt {{ box-shadow: none; border-radius: 0; }} }}
    </style>
</head>
<body>
    <div class="receipt">
        <div class="receipt-header">
            <h1>{company_name}</h1>
            <div class="subtitle">PAYMENT RECEIPT</div>
        </div>
        <div class="receipt-body">
            <div class="receipt-meta">
                <div class="left">
                    <div class="label">Receipt Number</div>
                    <div class="value">{receipt.receipt_number}</div>
                    <div class="label">Date Issued</div>
                    <div class="value">{receipt.issued_at.strftime('%d %B %Y') if receipt.issued_at else 'N/A'}</div>
                </div>
                <div class="right">
                    <div class="label">Order Reference</div>
                    <div class="value">{order_number}</div>
                    <div class="label">Order Date</div>
                    <div class="value">{order_date}</div>
                </div>
            </div>

            <div class="receipt-details">
                <h3>Payment Details</h3>
                <div class="details-grid">
                    <div class="detail-item">
                        <div class="label">Customer</div>
                        <div class="value">{customer_name}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">Payment Method</div>
                        <div class="value">{payment_method}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">Payment Reference</div>
                        <div class="value">{payment_reference}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">Status</div>
                        <div class="value">{receipt.status}</div>
                    </div>
                </div>
            </div>

            <div class="amount-box">
                <div class="currency">{receipt.currency}</div>
                <div class="amount">{receipt.amount:,.2f}</div>
            </div>

            <div class="verification">
                <div class="label">Verification Token</div>
                <div class="token">{receipt.verification_token}</div>
            </div>
        </div>
        <div class="footer">
            <p>{company_name}</p>
            {f'<p>{company_address}</p>' if company_address else ''}
            {f'<p>Phone: {company_phone}</p>' if company_phone else ''}
            {f'<p>Email: {company_email}</p>' if company_email else ''}
            {f'<p>Website: {company_website}</p>' if company_website else ''}
            <p style="margin-top: 10px;">This is an official receipt issued by {company_name}.</p>
        </div>
    </div>
</body>
</html>"""
