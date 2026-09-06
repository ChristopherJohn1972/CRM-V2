import logging

import sqlalchemy as sa
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from common.events import DomainEvent, EventBus
from common.exceptions import NotFoundError, PermissionDeniedError, ValidationError_
from portal.permissions import IsPortalAuthenticated, PortalPrincipal
from quotes.models import (
    Quote,
    QuoteClientResponse,
    QuoteDocument,
    QuoteEvent,
    QuoteItem,
    QuotePortalAccess,
    QuoteVersion,
)
from quotes.serializers import (
    ClientResponseSerializer,
    QuoteItemReadSerializer,
    QuotePortalEventReadSerializer,
    QuotePortalQuoteReadSerializer,
    QuoteReadSerializer,
)
from quotes.services import QuotePortalService

logger = logging.getLogger(__name__)


def _portal_principal(request) -> PortalPrincipal:
    return getattr(request, "user", None)


def _require_portal_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        raise PermissionDeniedError(f"Missing required portal permission: {code}")


def _get_customer_account_ids(db, portal_user_id):
    """Return list of customer_account_ids the portal user has access to."""
    from portal.models import PortalUserCustomer

    links = db.execute(
        sa.select(PortalUserCustomer.customer_account_id)
        .where(
            PortalUserCustomer.portal_user_id == portal_user_id,
            PortalUserCustomer.is_active == sa.true(),
        )
    ).scalars().all()
    return list(links)


def _get_portal_quote(db, request, quote_id, portal_user_id):
    """Get a quote that is visible to this portal user's organization."""
    quote = db.get(Quote, quote_id)
    if quote is None:
        raise NotFoundError("Quote not found.")

    # Must be in SENT or later status
    allowed_statuses = ("SENT", "VIEWED", "ACCEPTED", "REJECTED", "EXPIRED")
    if quote.status.value not in allowed_statuses:
        raise NotFoundError("Quote not found.")

    # Check portal access exists for this customer account
    account_ids = _get_customer_account_ids(db, portal_user_id)
    if not account_ids:
        raise PermissionDeniedError("No portal access.")

    access = db.execute(
        sa.select(QuotePortalAccess).where(
            QuotePortalAccess.quote_id == quote.quote_id,
            QuotePortalAccess.customer_account_id.in_(account_ids),
            QuotePortalAccess.visibility == "VISIBLE",
        )
    ).scalar_one_or_none()

    if access is None:
        raise PermissionDeniedError("You do not have access to this quote.")

    return quote


class PortalQuoteListView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def get(self, request):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.view")

        session = SessionLocal()
        try:
            account_ids = _get_customer_account_ids(session, principal.portal_user_id)
            if not account_ids:
                return Response({"count": 0, "results": []})

            # Get all quotes with portal access for this user's accounts
            access_records = session.execute(
                sa.select(QuotePortalAccess.quote_id)
                .where(
                    QuotePortalAccess.customer_account_id.in_(account_ids),
                    QuotePortalAccess.visibility == "VISIBLE",
                )
            ).scalars().all()

            if not access_records:
                return Response({"count": 0, "results": []})

            quotes = session.execute(
                sa.select(Quote).where(Quote.quote_id.in_(access_records))
                .order_by(sa.desc(Quote.created_at))
            ).scalars().all()

            data = []
            for quote in quotes:
                items = session.execute(
                    sa.select(QuoteItem)
                    .where(QuoteItem.quote_id == quote.quote_id)
                    .order_by(QuoteItem.sort_order)
                ).scalars().all()

                quote_data = {
                    "quote_id": quote.quote_id,
                    "quote_number": quote.quote_number,
                    "quote_type": quote.quote_type.value if hasattr(quote.quote_type, "value") else quote.quote_type,
                    "title": quote.title,
                    "status": quote.status.value if hasattr(quote.status, "value") else quote.status,
                    "currency": quote.currency,
                    "quote_date": str(quote.quote_date) if quote.quote_date else None,
                    "valid_until": str(quote.valid_until) if quote.valid_until else None,
                    "subtotal": str(quote.subtotal),
                    "discount_amount": str(quote.discount_amount),
                    "tax_amount": str(quote.tax_amount),
                    "grand_total": str(quote.grand_total),
                    "items": [{
                        "item_id": i.item_id,
                        "description": i.description,
                        "quantity": str(i.quantity),
                        "unit_price": str(i.unit_price),
                        "line_total": str(i.line_total),
                    } for i in items],
                    "accepted_at": quote.accepted_at.isoformat() if quote.accepted_at else None,
                    "rejected_at": quote.rejected_at.isoformat() if quote.rejected_at else None,
                }
                data.append(quote_data)

            return Response({"count": len(data), "results": data})
        finally:
            session.close()


class PortalQuoteDetailView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, quote_id):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.view")

        session = SessionLocal()
        try:
            quote = _get_portal_quote(session, request, quote_id, principal.portal_user_id)

            items = session.execute(
                sa.select(QuoteItem)
                .where(QuoteItem.quote_id == quote.quote_id)
                .order_by(QuoteItem.sort_order)
            ).scalars().all()

            data = {
                "quote_id": quote.quote_id,
                "quote_number": quote.quote_number,
                "quote_type": quote.quote_type.value if hasattr(quote.quote_type, "value") else quote.quote_type,
                "title": quote.title,
                "status": quote.status.value if hasattr(quote.status, "value") else quote.status,
                "currency": quote.currency,
                "quote_date": str(quote.quote_date) if quote.quote_date else None,
                "valid_until": str(quote.valid_until) if quote.valid_until else None,
                "subtotal": str(quote.subtotal),
                "discount_amount": str(quote.discount_amount),
                "tax_amount": str(quote.tax_amount),
                "additional_charges": str(quote.additional_charges),
                "grand_total": str(quote.grand_total),
                "items": [{
                    "item_id": i.item_id,
                    "description": i.description,
                    "quantity": str(i.quantity),
                    "unit_price": str(i.unit_price),
                    "discount_amount": str(i.discount_amount),
                    "tax_rate": str(i.tax_rate),
                    "tax_amount": str(i.tax_amount),
                    "gross_amount": str(i.gross_amount),
                    "net_amount": str(i.net_amount),
                    "line_total": str(i.line_total),
                } for i in items],
                "notes": quote.notes,
                "terms_and_conditions": quote.terms_and_conditions,
                "accepted_at": quote.accepted_at.isoformat() if quote.accepted_at else None,
                "rejected_at": quote.rejected_at.isoformat() if quote.rejected_at else None,
            }

            return Response(data)
        finally:
            session.close()


class PortalQuoteDocumentView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, quote_id):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.download")

        session = SessionLocal()
        try:
            quote = _get_portal_quote(session, request, quote_id, principal.portal_user_id)

            document = session.execute(
                sa.select(QuoteDocument)
                .where(QuoteDocument.quote_id == quote.quote_id)
                .order_by(sa.desc(QuoteDocument.created_at))
                .limit(1)
            ).scalar_one_or_none()

            if document is None:
                raise NotFoundError("No document available for this quote.")

            return Response({
                "document_id": document.document_id,
                "file_name": document.file_name,
                "document_type": document.document_type,
                "content_hash": document.content_hash,
                "created_at": document.created_at.isoformat() if document.created_at else None,
            })
        finally:
            session.close()


class PortalQuoteAcceptView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def post(self, request, quote_id):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.accept")

        serializer = ClientResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment")

        session = SessionLocal()
        try:
            quote = _get_portal_quote(session, request, quote_id, principal.portal_user_id)

            # Get customer account
            account_ids = _get_customer_account_ids(session, principal.portal_user_id)
            from portal.models import PortalUserCustomer
            link = session.execute(
                sa.select(PortalUserCustomer.customer_account_id)
                .where(
                    PortalUserCustomer.portal_user_id == principal.portal_user_id,
                    PortalUserCustomer.customer_account_id.in_(account_ids),
                )
            ).scalar_one_or_none()

            if not link:
                raise PermissionDeniedError("No portal account access.")

            quote = QuotePortalService.client_accept(
                session, quote, principal.portal_user_id, link, comment
            )

            return Response({
                "quote_id": quote.quote_id,
                "quote_number": quote.quote_number,
                "status": quote.status.value if hasattr(quote.status, "value") else quote.status,
                "accepted_at": quote.accepted_at.isoformat() if quote.accepted_at else None,
                "message": "Quote accepted successfully.",
            })
        finally:
            session.close()


class PortalQuoteDeclineView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def post(self, request, quote_id):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.decline")

        serializer = ClientResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment")

        session = SessionLocal()
        try:
            quote = _get_portal_quote(session, request, quote_id, principal.portal_user_id)

            account_ids = _get_customer_account_ids(session, principal.portal_user_id)
            from portal.models import PortalUserCustomer
            link = session.execute(
                sa.select(PortalUserCustomer.customer_account_id)
                .where(
                    PortalUserCustomer.portal_user_id == principal.portal_user_id,
                    PortalUserCustomer.customer_account_id.in_(account_ids),
                )
            ).scalar_one_or_none()

            if not link:
                raise PermissionDeniedError("No portal account access.")

            quote = QuotePortalService.client_reject(
                session, quote, principal.portal_user_id, link, comment
            )

            return Response({
                "quote_id": quote.quote_id,
                "quote_number": quote.quote_number,
                "status": quote.status.value if hasattr(quote.status, "value") else quote.status,
                "rejected_at": quote.rejected_at.isoformat() if quote.rejected_at else None,
                "message": "Quote declined.",
            })
        finally:
            session.close()


class PortalQuoteAcknowledgeView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def post(self, request, quote_id):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.acknowledge")

        serializer = ClientResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment")

        session = SessionLocal()
        try:
            quote = _get_portal_quote(session, request, quote_id, principal.portal_user_id)

            account_ids = _get_customer_account_ids(session, principal.portal_user_id)
            from portal.models import PortalUserCustomer
            link = session.execute(
                sa.select(PortalUserCustomer.customer_account_id)
                .where(
                    PortalUserCustomer.portal_user_id == principal.portal_user_id,
                    PortalUserCustomer.customer_account_id.in_(account_ids),
                )
            ).scalar_one_or_none()

            if not link:
                raise PermissionDeniedError("No portal account access.")

            quote = QuotePortalService.client_acknowledge(
                session, quote, principal.portal_user_id, link, comment
            )

            return Response({
                "quote_id": quote.quote_id,
                "quote_number": quote.quote_number,
                "status": quote.status.value if hasattr(quote.status, "value") else quote.status,
                "message": "Quote acknowledged.",
            })
        finally:
            session.close()


class PortalQuoteChangeRequestView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def post(self, request, quote_id):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.request_changes")

        serializer = ClientResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment")

        if not comment:
            raise ValidationError_("Please provide details about the requested changes.")

        session = SessionLocal()
        try:
            quote = _get_portal_quote(session, request, quote_id, principal.portal_user_id)

            account_ids = _get_customer_account_ids(session, principal.portal_user_id)
            from portal.models import PortalUserCustomer
            link = session.execute(
                sa.select(PortalUserCustomer.customer_account_id)
                .where(
                    PortalUserCustomer.portal_user_id == principal.portal_user_id,
                    PortalUserCustomer.customer_account_id.in_(account_ids),
                )
            ).scalar_one_or_none()

            if not link:
                raise PermissionDeniedError("No portal account access.")

            response = QuotePortalService.client_request_changes(
                session, quote, principal.portal_user_id, link, comment
            )

            return Response({
                "response_id": response.response_id,
                "message": "Change request submitted. Our team will review and respond.",
            })
        finally:
            session.close()


class PortalQuoteEventsView(APIView):
    permission_classes = [IsPortalAuthenticated]

    def get(self, request, quote_id):
        principal = _portal_principal(request)
        _require_portal_permission(principal, "portal.quote.view")

        session = SessionLocal()
        try:
            quote = _get_portal_quote(session, request, quote_id, principal.portal_user_id)

            # Only return customer-visible events
            visible_events = ("SENT", "VIEWED", "ACCEPTED", "DECLINED", "CHANGE_REQUESTED", "EXPIRED")
            events = session.execute(
                sa.select(QuoteEvent)
                .where(
                    QuoteEvent.quote_id == quote.quote_id,
                    QuoteEvent.event_type.in_(visible_events),
                )
                .order_by(sa.desc(QuoteEvent.occurred_at))
            ).scalars().all()

            data = [{
                "event_id": e.event_id,
                "event_type": e.event_type,
                "description": e.description,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            } for e in events]

            return Response(data)
        finally:
            session.close()
