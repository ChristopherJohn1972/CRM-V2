import logging

import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.models import Customer
from common import audit
from common.db import SessionLocal
from common.events import DomainEvent, EventBus
from common.exceptions import NotFoundError, PermissionDeniedError, ValidationError_
from iam.permissions import UserPrincipal
from quotes.access import can_access_quote, scope_quote_queryset
from quotes.models import (
    Quote,
    QuoteApproval,
    QuoteDocument,
    QuoteEvent,
    QuoteItem,
    QuoteTemplate,
    TaxRule,
)
from quotes.serializers import (
    CalculationRequestSerializer,
    CalculationResponseSerializer,
    QuoteActionSerializer,
    QuoteItemWriteSerializer,
    QuoteReadSerializer,
    QuoteTemplateReadSerializer,
    QuoteTemplateWriteSerializer,
    QuoteUpdateSerializer,
    QuoteWriteSerializer,
)
from quotes.services import (
    QuoteCalculationService,
    QuoteDocumentService,
    QuoteEventService,
    QuoteService,
    QuoteTemplateService,
    QuoteWorkflowService,
)

logger = logging.getLogger(__name__)

PERMISSION_QUOTE_READ = "quotes.quote.read"
PERMISSION_QUOTE_CREATE = "quotes.quote.create"
PERMISSION_QUOTE_UPDATE = "quotes.quote.update"
PERMISSION_QUOTE_DELETE = "quotes.quote.delete"
PERMISSION_QUOTE_DUPLICATE = "quotes.quote.duplicate"
PERMISSION_QUOTE_CALCULATE = "quotes.quote.calculate"
PERMISSION_QUOTE_SUBMIT_APPROVAL = "quotes.quote.submit_approval"
PERMISSION_QUOTE_APPROVE = "quotes.quote.approve"
PERMISSION_QUOTE_REJECT = "quotes.quote.reject"
PERMISSION_QUOTE_SEND = "quotes.quote.send"
PERMISSION_QUOTE_PREVIEW = "quotes.quote.preview"
PERMISSION_QUOTE_DOWNLOAD_PDF = "quotes.quote.download_pdf"
PERMISSION_QUOTE_VIEW_AUDIT = "quotes.quote.view_audit"
PERMISSION_QUOTE_CONVERT = "quotes.quote.convert_to_order"
PERMISSION_QUOTE_MANAGE_TEMPLATES = "quotes.quote.manage_templates"
PERMISSION_QUOTE_MANAGE_TAX = "quotes.quote.manage_tax_rules"
PERMISSION_QUOTE_MANAGE_PAYMENT_TERMS = "quotes.quote.manage_payment_terms"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        raise PermissionDeniedError(f"Missing required permission: {code}")


def _get_quote(db, request, quote_id):
    quote = db.get(Quote, quote_id)
    if quote is None or quote.deleted_at is not None:
        raise NotFoundError("Quote not found.")
    if not can_access_quote(db, _principal(request), quote):
        raise PermissionDeniedError()
    return quote


def _get_template(db, template_id):
    template = db.get(QuoteTemplate, template_id)
    if template is None:
        raise NotFoundError("Quote template not found.")
    return template


def _get_item(db, quote, item_id):
    item = db.get(QuoteItem, item_id)
    if item is None or item.quote_id != quote.quote_id:
        raise NotFoundError("Quote item not found.")
    return item


# ---------------------------------------------------------------------------
# Quote CRUD Views
# ---------------------------------------------------------------------------

class QuoteListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_READ)

        session = SessionLocal()
        try:
            stmt = sa.select(Quote)
            stmt = scope_quote_queryset(session, principal, stmt)

            # Filters
            search = request.query_params.get("search")
            if search:
                like = f"%{search}%"
                stmt = stmt.where(
                    sa.or_(
                        Quote.quote_number.like(like),
                        Quote.title.like(like),
                    )
                )

            quote_type = request.query_params.get("quote_type")
            if quote_type:
                stmt = stmt.where(Quote.quote_type == quote_type)

            quote_status = request.query_params.get("status")
            if quote_status:
                stmt = stmt.where(Quote.status == quote_status)

            customer_id = request.query_params.get("customer_id")
            if customer_id:
                stmt = stmt.where(Quote.customer_id == int(customer_id))

            owner_user_id = request.query_params.get("owner_user_id")
            if owner_user_id:
                stmt = stmt.where(Quote.owner_user_id == int(owner_user_id))

            stmt = stmt.order_by(sa.desc(Quote.quote_id))
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
            for quote in rows:
                items = session.execute(
                    sa.select(QuoteItem)
                    .where(QuoteItem.quote_id == quote.quote_id)
                    .order_by(QuoteItem.sort_order)
                ).scalars().all()
                quote_data = QuoteReadSerializer(quote).data
                quote_data["items"] = [QuoteReadSerializer().data.get("items", []) and {
                    "item_id": i.item_id,
                    "description": i.description,
                    "quantity": str(i.quantity),
                    "unit_price": str(i.unit_price),
                    "line_total": str(i.line_total),
                } for i in items]
                data.append(quote_data)

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
        _require_permission(principal, PERMISSION_QUOTE_CREATE)

        serializer = QuoteWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            quote = QuoteService.create_quote(
                session, payload, principal.user_id, request=request
            )

            # Fetch items for response
            items = session.execute(
                sa.select(QuoteItem)
                .where(QuoteItem.quote_id == quote.quote_id)
                .order_by(QuoteItem.sort_order)
            ).scalars().all()

            data = QuoteReadSerializer(quote).data
            from quotes.serializers import QuoteItemReadSerializer
            data["items"] = QuoteItemReadSerializer(items, many=True).data
            return Response(data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class QuoteDetailView(APIView):
    def get(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_READ)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            items = session.execute(
                sa.select(QuoteItem)
                .where(QuoteItem.quote_id == quote.quote_id)
                .order_by(QuoteItem.sort_order)
            ).scalars().all()

            data = QuoteReadSerializer(quote).data
            from quotes.serializers import QuoteItemReadSerializer
            data["items"] = QuoteItemReadSerializer(items, many=True).data
            return Response(data)
        finally:
            session.close()

    def patch(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_UPDATE)

        serializer = QuoteUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            quote = QuoteService.update_quote(
                session, quote, payload, principal.user_id, request=request
            )
            data = QuoteReadSerializer(quote).data
            return Response(data)
        finally:
            session.close()

    def delete(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_DELETE)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            quote = QuoteWorkflowService.delete_quote(
                session, quote, principal.user_id, request=request,
            )
            return Response({
                "success": True,
                "message": "Quote deleted successfully.",
                "quote_id": quote.quote_id,
            })
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Quote Item Views
# ---------------------------------------------------------------------------

class QuoteItemListView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_UPDATE)

        serializer = QuoteItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item_data = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            item = QuoteService.add_item(
                session, quote, item_data, principal.user_id, request=request
            )
            from quotes.serializers import QuoteItemReadSerializer
            return Response(QuoteItemReadSerializer(item).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class QuoteItemDetailView(APIView):
    def patch(self, request, quote_id, item_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_UPDATE)

        serializer = QuoteItemWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item_data = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            item = _get_item(session, quote, item_id)
            item = QuoteService.update_item(
                session, quote, item, item_data, principal.user_id, request=request
            )
            from quotes.serializers import QuoteItemReadSerializer
            return Response(QuoteItemReadSerializer(item).data)
        finally:
            session.close()

    def delete(self, request, quote_id, item_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_UPDATE)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            item = _get_item(session, quote, item_id)
            QuoteService.remove_item(
                session, quote, item, principal.user_id, request=request
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Calculation Views
# ---------------------------------------------------------------------------

class QuoteCalculationView(APIView):
    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_CALCULATE)

        serializer = CalculationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        items_data = [dict(item) for item in data["items"]]
        quote_discount = None
        if data.get("discount_type"):
            quote_discount = {
                "discount_type": data["discount_type"],
                "discount_value": data.get("discount_value", 0),
            }

        result = QuoteCalculationService.calculate_quote_state(
            items_data,
            quote_discount=quote_discount,
            additional_charges=data.get("additional_charges", 0),
            currency=data.get("currency", "KES"),
        )

        # Convert Decimal to string for JSON serialization
        for line in result["lines"]:
            for k, v in line.items():
                line[k] = str(v)
        result["subtotal"] = str(result["subtotal"])
        result["total_discount"] = str(result["total_discount"])
        result["total_tax"] = str(result["total_tax"])
        result["additional_charges"] = str(result["additional_charges"])
        result["grand_total"] = str(result["grand_total"])

        return Response(result)


class QuoteRecalculateView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_CALCULATE)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            result = QuoteCalculationService.recalculate_quote(session, quote)

            for line in result["lines"]:
                for k, v in line.items():
                    line[k] = str(v)
            result["subtotal"] = str(result["subtotal"])
            result["total_discount"] = str(result["total_discount"])
            result["total_tax"] = str(result["total_tax"])
            result["additional_charges"] = str(result["additional_charges"])
            result["grand_total"] = str(result["grand_total"])

            return Response(result)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Workflow / Action Views
# ---------------------------------------------------------------------------

class QuoteSubmitApprovalView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_SUBMIT_APPROVAL)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            quote = QuoteWorkflowService.submit_for_approval(
                session, quote, principal.user_id, request=request
            )
            return Response(QuoteReadSerializer(quote).data)
        finally:
            session.close()


class QuoteApproveView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_APPROVE)

        serializer = QuoteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            quote = QuoteWorkflowService.approve(
                session, quote, principal.user_id,
                reason=serializer.validated_data.get("reason"),
                request=request,
            )
            return Response(QuoteReadSerializer(quote).data)
        finally:
            session.close()


class QuoteRejectView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_REJECT)

        serializer = QuoteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            quote = QuoteWorkflowService.reject(
                session, quote, principal.user_id,
                reason=serializer.validated_data.get("reason"),
                request=request,
            )
            return Response(QuoteReadSerializer(quote).data)
        finally:
            session.close()


class QuoteSendView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_SEND)

        customer_account_id = request.data.get("customer_account_id")

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            quote = QuoteWorkflowService.send_quote(
                session, quote, principal.user_id,
                customer_account_id=customer_account_id,
                request=request,
            )
            return Response(QuoteReadSerializer(quote).data)
        finally:
            session.close()


class QuoteCancelView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_UPDATE)

        reason = request.data.get("reason")

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            quote = QuoteWorkflowService.cancel_quote(
                session, quote, principal.user_id,
                reason=reason, request=request,
            )
            return Response(QuoteReadSerializer(quote).data)
        finally:
            session.close()


class QuoteDuplicateView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_DUPLICATE)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            new_quote = QuoteService.duplicate_quote(
                session, quote, principal.user_id, request=request
            )
            return Response(QuoteReadSerializer(new_quote).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Document / Preview Views
# ---------------------------------------------------------------------------

class QuotePreviewView(APIView):
    def get(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_PREVIEW)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            items = session.execute(
                sa.select(QuoteItem)
                .where(QuoteItem.quote_id == quote.quote_id)
                .order_by(QuoteItem.sort_order)
            ).scalars().all()

            data = QuoteReadSerializer(quote).data
            from quotes.serializers import QuoteItemReadSerializer
            data["items"] = QuoteItemReadSerializer(items, many=True).data
            return Response(data)
        finally:
            session.close()


class QuotePdfView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_DOWNLOAD_PDF)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)
            document = QuoteDocumentService.generate_document(
                session, quote, principal.user_id, request=request
            )
            return Response({
                "document_id": document.document_id,
                "file_name": document.file_name,
                "content_hash": document.content_hash,
                "quote_version_id": document.quote_version_id,
                "message": "Document generated. PDF rendering is handled by the async document worker.",
            }, status=status.HTTP_201_CREATED)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Audit / Activity View
# ---------------------------------------------------------------------------

class QuoteActivityView(APIView):
    def get(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_VIEW_AUDIT)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)

            events = session.execute(
                sa.select(QuoteEvent)
                .where(QuoteEvent.quote_id == quote.quote_id)
                .order_by(sa.desc(QuoteEvent.occurred_at))
            ).scalars().all()

            data = []
            for event in events:
                data.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "actor_user_id": event.actor_user_id,
                    "actor_portal_user_id": event.actor_portal_user_id,
                    "actor_type": event.actor_type,
                    "description": event.description,
                    "metadata_": event.metadata_,
                    "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
                })

            return Response(data)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Approvals View
# ---------------------------------------------------------------------------

class QuoteApprovalsListView(APIView):
    def get(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_VIEW_AUDIT)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)

            approvals = session.execute(
                sa.select(QuoteApproval)
                .where(QuoteApproval.quote_id == quote.quote_id)
                .order_by(sa.desc(QuoteApproval.requested_at))
            ).scalars().all()

            data = []
            for approval in approvals:
                data.append({
                    "approval_id": approval.approval_id,
                    "approver_user_id": approval.approver_user_id,
                    "status": approval.status.value if hasattr(approval.status, "value") else approval.status,
                    "reason": approval.reason,
                    "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
                    "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                })

            return Response(data)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Documents View
# ---------------------------------------------------------------------------

class QuoteDocumentsListView(APIView):
    def get(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_READ)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)

            documents = session.execute(
                sa.select(QuoteDocument)
                .where(QuoteDocument.quote_id == quote.quote_id)
                .order_by(sa.desc(QuoteDocument.created_at))
            ).scalars().all()

            data = []
            for doc in documents:
                data.append({
                    "document_id": doc.document_id,
                    "document_type": doc.document_type,
                    "file_name": doc.file_name,
                    "content_hash": doc.content_hash,
                    "quote_version_id": doc.quote_version_id,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                })

            return Response(data)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Tax Rules Views
# ---------------------------------------------------------------------------

class TaxRuleListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_READ)

        session = SessionLocal()
        try:
            rows = session.execute(
                sa.select(TaxRule).where(TaxRule.is_active == sa.true()).order_by(TaxRule.code)
            ).scalars().all()

            data = [{
                "tax_rule_id": t.tax_rule_id,
                "code": t.code,
                "name": t.name,
                "rate": str(t.rate),
                "is_active": t.is_active,
            } for t in rows]
            return Response(data)
        finally:
            session.close()

    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_MANAGE_TAX)

        session = SessionLocal()
        try:
            code = request.data.get("code")
            name = request.data.get("name")
            rate = request.data.get("rate", 0)

            if not code or not name:
                raise ValidationError_("code and name are required.")

            tax_rule = TaxRule(code=code, name=name, rate=rate)
            session.add(tax_rule)
            session.flush()

            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="tax_rule.created",
                resource_type="tax_rules",
                resource_id=tax_rule.tax_rule_id,
                description=f"Tax rule '{name}' ({code}) created",
                request=request,
            )

            session.commit()
            session.refresh(tax_rule)
            return Response({
                "tax_rule_id": tax_rule.tax_rule_id,
                "code": tax_rule.code,
                "name": tax_rule.name,
                "rate": str(tax_rule.rate),
            }, status=status.HTTP_201_CREATED)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Quote Template Views
# ---------------------------------------------------------------------------

class QuoteTemplateListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_READ)

        session = SessionLocal()
        try:
            stmt = sa.select(QuoteTemplate).order_by(QuoteTemplate.name)
            template_type = request.query_params.get("template_type")
            if template_type:
                stmt = stmt.where(QuoteTemplate.template_type == template_type)
            template_status = request.query_params.get("status")
            if template_status:
                stmt = stmt.where(QuoteTemplate.status == template_status)

            rows = session.execute(stmt).scalars().all()
            data = QuoteTemplateReadSerializer(rows, many=True).data
            return Response(data)
        finally:
            session.close()

    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_MANAGE_TEMPLATES)

        serializer = QuoteTemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            template = QuoteTemplateService.create_template(
                session, payload, principal.user_id, request=request
            )
            return Response(QuoteTemplateReadSerializer(template).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class QuoteTemplateDetailView(APIView):
    def get(self, request, template_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_READ)

        session = SessionLocal()
        try:
            template = _get_template(session, template_id)
            return Response(QuoteTemplateReadSerializer(template).data)
        finally:
            session.close()

    def patch(self, request, template_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_MANAGE_TEMPLATES)

        serializer = QuoteTemplateWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            template = _get_template(session, template_id)
            template = QuoteTemplateService.update_template(
                session, template, payload, principal.user_id, request=request
            )
            return Response(QuoteTemplateReadSerializer(template).data)
        finally:
            session.close()


class QuoteTemplateActivateView(APIView):
    def post(self, request, template_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_MANAGE_TEMPLATES)

        session = SessionLocal()
        try:
            template = _get_template(session, template_id)
            template = QuoteTemplateService.activate_template(
                session, template, principal.user_id, request=request
            )
            return Response(QuoteTemplateReadSerializer(template).data)
        finally:
            session.close()


class QuoteTemplateDeactivateView(APIView):
    def post(self, request, template_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_MANAGE_TEMPLATES)

        session = SessionLocal()
        try:
            template = _get_template(session, template_id)
            template = QuoteTemplateService.deactivate_template(
                session, template, principal.user_id, request=request
            )
            return Response(QuoteTemplateReadSerializer(template).data)
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Quote Convert to Order View
# ---------------------------------------------------------------------------

class QuoteConvertToOrderView(APIView):
    def post(self, request, quote_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_QUOTE_CONVERT)

        session = SessionLocal()
        try:
            quote = _get_quote(session, request, quote_id)

            from sales_orders.services import QuoteConversionService
            from sales_orders.serializers import SalesOrderReadSerializer, SalesOrderItemReadSerializer
            from sales_orders.models import SalesOrderItem

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
