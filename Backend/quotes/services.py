import hashlib
import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

import sqlalchemy as sa

from clients.models import Customer
from common import audit
from common.events import DomainEvent, EventBus
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from quotes.enums import (
    ALLOWED_QUOTE_TRANSITIONS,
    ApprovalStatus,
    ClientResponseDecision,
    DiscountType,
    QuoteEventType,
    QuoteItemType,
    QuoteStatus,
    QuoteTemplateStatus,
    QuoteType,
    TERMINAL_STATUSES,
)
from quotes.models import (
    CompanyProfile,
    PaymentTerm,
    Quote,
    QuoteApproval,
    QuoteClientResponse,
    QuoteDocument,
    QuoteEvent,
    QuoteItem,
    QuoteNumberSequence,
    QuotePortalAccess,
    QuoteTemplate,
    QuoteTemplateVersion,
    QuoteVersion,
    TaxRule,
)

logger = logging.getLogger(__name__)

QUOTE_NUMBER_BUCKET = "QUOTE"
ROUNDING = ROUND_HALF_UP
PRECISION = Decimal("0.01")


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today():
    return date.today()


# ---------------------------------------------------------------------------
# Numbering Service
# ---------------------------------------------------------------------------

class QuoteNumberService:
    @staticmethod
    def generate_quote_number(db) -> tuple:
        """Atomically generate the next QN number. Returns (quote_number, sequence_value)."""
        row = db.execute(
            sa.select(QuoteNumberSequence)
            .where(QuoteNumberSequence.bucket == QUOTE_NUMBER_BUCKET)
            .with_for_update()
        ).scalar_one_or_none()

        if row is None:
            row = QuoteNumberSequence(bucket=QUOTE_NUMBER_BUCKET, last_value=0, min_length=2)
            db.add(row)
            db.flush()

        # Reconcile against existing quote numbers so soft-deleted numbers
        # don't cause duplicates and we never regress below the highest existing.
        max_existing = db.execute(
            sa.select(sa.func.max(Quote.sequence_value))
        ).scalar()
        if max_existing and max_existing > row.last_value:
            row.last_value = max_existing

        row.last_value += 1
        quote_number = f"QN{str(row.last_value).zfill(row.min_length)}"
        return quote_number, row.last_value


# ---------------------------------------------------------------------------
# Calculation Engine
# ---------------------------------------------------------------------------

class QuoteCalculationService:
    @staticmethod
    def calculate_line(item_data: dict) -> dict:
        """Calculate a single line item from raw input data."""
        quantity = Decimal(str(item_data.get("quantity", 1)))
        unit_price = Decimal(str(item_data.get("unit_price", 0)))

        gross = (quantity * unit_price).quantize(PRECISION, rounding=ROUNDING)

        discount_type = item_data.get("discount_type")
        discount_value = Decimal(str(item_data.get("discount_value", 0)))

        if discount_type == DiscountType.PERCENTAGE.value:
            discount_amount = (gross * discount_value / Decimal("100")).quantize(
                PRECISION, rounding=ROUNDING
            )
        elif discount_type == DiscountType.FIXED.value:
            discount_amount = discount_value.quantize(PRECISION, rounding=ROUNDING)
        else:
            discount_amount = Decimal("0.00")

        # Validate discount doesn't exceed gross
        if discount_amount > gross:
            discount_amount = gross

        net = (gross - discount_amount).quantize(PRECISION, rounding=ROUNDING)

        tax_rate = Decimal(str(item_data.get("tax_rate", 0)))
        tax_amount = (net * tax_rate / Decimal("100")).quantize(PRECISION, rounding=ROUNDING)

        line_total = (net + tax_amount).quantize(PRECISION, rounding=ROUNDING)

        return {
            "gross_amount": gross,
            "discount_amount": discount_amount,
            "net_amount": net,
            "tax_amount": tax_amount,
            "line_total": line_total,
        }

    @staticmethod
    def calculate_quote_state(items_data: list, quote_discount=None, additional_charges=None, currency="KES") -> dict:
        """Calculate full quote from a list of item data dicts."""
        lines = []
        total_discount = Decimal("0.00")
        total_tax = Decimal("0.00")
        subtotal = Decimal("0.00")

        for item_data in items_data:
            line = QuoteCalculationService.calculate_line(item_data)
            lines.append(line)
            total_discount += line["discount_amount"]
            total_tax += line["tax_amount"]
            subtotal += line["net_amount"]

        total_discount = total_discount.quantize(PRECISION, rounding=ROUNDING)
        total_tax = total_tax.quantize(PRECISION, rounding=ROUNDING)
        subtotal = subtotal.quantize(PRECISION, rounding=ROUNDING)

        # Quote-level discount
        quote_discount_amount = Decimal("0.00")
        if quote_discount:
            qd_type = quote_discount.get("discount_type")
            qd_value = Decimal(str(quote_discount.get("discount_value", 0)))
            if qd_type == DiscountType.PERCENTAGE.value:
                quote_discount_amount = (subtotal * qd_value / Decimal("100")).quantize(
                    PRECISION, rounding=ROUNDING
                )
            elif qd_type == DiscountType.FIXED.value:
                quote_discount_amount = qd_value.quantize(PRECISION, rounding=ROUNDING)
        total_discount += quote_discount_amount

        charges = Decimal(str(additional_charges or 0)).quantize(PRECISION, rounding=ROUNDING)

        grand_total = (subtotal - quote_discount_amount + total_tax + charges).quantize(
            PRECISION, rounding=ROUNDING
        )

        return {
            "currency": currency,
            "lines": lines,
            "subtotal": subtotal,
            "total_discount": total_discount,
            "total_tax": total_tax,
            "additional_charges": charges,
            "grand_total": grand_total,
        }

    @staticmethod
    def recalculate_quote(db, quote) -> dict:
        """Recalculate a persisted quote from its items."""
        items = db.execute(
            sa.select(QuoteItem)
            .where(QuoteItem.quote_id == quote.quote_id)
            .order_by(QuoteItem.sort_order)
        ).scalars().all()

        items_data = []
        for item in items:
            items_data.append({
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_type": item.discount_type,
                "discount_value": item.discount_value,
                "tax_rate": item.tax_rate,
            })

        quote_discount = None
        if quote.discount_type:
            quote_discount = {
                "discount_type": quote.discount_type,
                "discount_value": quote.discount_value,
            }

        result = QuoteCalculationService.calculate_quote_state(
            items_data,
            quote_discount=quote_discount,
            additional_charges=quote.additional_charges,
            currency=quote.currency,
        )

        # Update quote totals
        quote.subtotal = result["subtotal"]
        quote.discount_amount = result["total_discount"]
        quote.tax_amount = result["total_tax"]
        quote.grand_total = result["grand_total"]
        db.flush()

        return result


# ---------------------------------------------------------------------------
# Quote Service (CRUD)
# ---------------------------------------------------------------------------

class QuoteService:
    @staticmethod
    def create_quote(db, payload: dict, actor_user_id: int, request=None) -> Quote:
        customer_id = payload.get("customer_id")
        if not customer_id:
            raise ValidationError_("customer_id is required.")

        customer = db.get(Customer, customer_id)
        if customer is None:
            raise NotFoundError("Customer not found.")

        quote_type = payload.get("quote_type", QuoteType.PRODUCT.value)
        if quote_type not in [t.value for t in QuoteType]:
            raise ValidationError_("Invalid quote_type.")

        quote_number, seq_value = QuoteNumberService.generate_quote_number(db)

        quote_date = payload.get("quote_date") or _today()
        valid_until = payload.get("valid_until")

        quote = Quote(
            quote_number=quote_number,
            sequence_value=seq_value,
            quote_type=quote_type,
            title=payload.get("title"),
            customer_id=customer_id,
            currency=payload.get("currency", "KES"),
            quote_date=quote_date,
            valid_until=valid_until,
            notes=payload.get("notes"),
            internal_notes=payload.get("internal_notes"),
            terms_and_conditions=payload.get("terms_and_conditions"),
            payment_term_id=payload.get("payment_term_id"),
            template_id=payload.get("template_id"),
            company_profile_id=payload.get("company_profile_id"),
            owner_user_id=actor_user_id,
            assigned_user_id=payload.get("assigned_user_id", actor_user_id),
            assigned_team_id=payload.get("assigned_team_id"),
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )

        # Apply quote-level discount if provided
        if payload.get("discount_type") and payload.get("discount_value") is not None:
            quote.discount_type = payload["discount_type"]
            quote.discount_value = Decimal(str(payload["discount_value"]))

        if payload.get("additional_charges") is not None:
            quote.additional_charges = Decimal(str(payload["additional_charges"]))

        db.add(quote)
        db.flush()

        # Add initial items if provided
        items_payload = payload.get("items", [])
        if items_payload:
            for idx, item_data in enumerate(items_payload):
                QuoteService._add_item_internal(db, quote, item_data, idx)
        elif quote.template_id:
            # Copy items from template content_config
            template = db.get(QuoteTemplate, quote.template_id)
            if template and template.content_config:
                tmpl_items = template.content_config.get("items", [])
                for idx, item_data in enumerate(tmpl_items):
                    QuoteService._add_item_internal(db, quote, item_data, idx)

        # Recalculate
        QuoteCalculationService.recalculate_quote(db, quote)

        # Record event
        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.CREATED.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote_number} created",
            metadata={"quote_type": quote_type, "customer_id": customer_id},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.created",
            resource_type="quotes",
            resource_id=quote.quote_id,
            description=f"Quote {quote_number} created",
            metadata={"quote_number": quote_number, "quote_type": quote_type},
            request=request,
        )

        db.commit()
        db.refresh(quote)

        EventBus.publish(
            DomainEvent(
                event_type="QuoteCreated",
                customer_id=customer_id,
                source_module="quotes",
                actor_user_id=actor_user_id,
                actor_type="INTERNAL_USER",
                summary=f"Quote {quote_number} created",
                reference_type="quotes",
                reference_id=quote.quote_id,
                payload={"quote_number": quote_number},
            )
        )
        return quote

    @staticmethod
    def update_quote(db, quote, payload: dict, actor_user_id: int, request=None) -> Quote:
        if quote.status in TERMINAL_STATUSES:
            raise ValidationError_(f"Cannot update a quote in {quote.status} status.")

        version = payload.pop("version", None)
        if version is not None and int(version) != quote.version:
            raise ConflictError(
                f"Version mismatch. Current version is {quote.version}.",
                error_code="optimistic_lock",
            )

        # Prevent editing items through update_quote
        payload.pop("items", None)

        changed_fields = []
        for key, value in payload.items():
            if hasattr(quote, key) and key not in ("quote_id", "quote_number", "sequence_value", "created_by", "created_at"):
                old_val = getattr(quote, key)
                if key == "discount_value" and value is not None:
                    value = Decimal(str(value))
                if key == "additional_charges" and value is not None:
                    value = Decimal(str(value))
                setattr(quote, key, value)
                if old_val != value:
                    changed_fields.append(key)

        if changed_fields:
            quote.updated_by = actor_user_id
            quote.version += 1
            db.flush()

            # Recalculate if financial fields changed
            financial_fields = {"discount_type", "discount_value", "additional_charges", "tax_amount"}
            if financial_fields.intersection(set(changed_fields)):
                QuoteCalculationService.recalculate_quote(db, quote)

            QuoteEventService.record_event(
                db, quote.quote_id, QuoteEventType.UPDATED.value,
                actor_user_id=actor_user_id,
                description=f"Quote {quote.quote_number} updated",
                metadata={"changed_fields": changed_fields},
            )

            audit.record_audit(
                db,
                actor_user_id=actor_user_id,
                action="quote.updated",
                resource_type="quotes",
                resource_id=quote.quote_id,
                description=f"Quote {quote.quote_number} updated",
                metadata={"changed_fields": changed_fields},
                request=request,
            )

            db.commit()
            db.refresh(quote)

        return quote

    @staticmethod
    def add_item(db, quote, item_data: dict, actor_user_id: int, request=None) -> QuoteItem:
        if quote.status in TERMINAL_STATUSES:
            raise ValidationError_(f"Cannot modify items on a quote in {quote.status} status.")

        # Get max sort order
        max_order = db.execute(
            sa.select(sa.func.coalesce(sa.func.max(QuoteItem.sort_order), 0))
            .where(QuoteItem.quote_id == quote.quote_id)
        ).scalar()
        item_data["sort_order"] = item_data.get("sort_order", max_order + 1)

        item = QuoteService._add_item_internal(db, quote, item_data, item_data["sort_order"])
        db.flush()

        # Recalculate
        QuoteCalculationService.recalculate_quote(db, quote)

        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.ITEM_ADDED.value,
            actor_user_id=actor_user_id,
            description=f"Item added: {item.description}",
            metadata={"item_id": item.item_id, "description": item.description},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.item_added",
            resource_type="quote_items",
            resource_id=item.item_id,
            description=f"Item added to quote {quote.quote_number}",
            metadata={"quote_number": quote.quote_number, "item_id": item.item_id},
            request=request,
        )

        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_item(db, quote, item, item_data: dict, actor_user_id: int, request=None) -> QuoteItem:
        if quote.status in TERMINAL_STATUSES:
            raise ValidationError_(f"Cannot modify items on a quote in {quote.status} status.")

        changed_fields = []
        for key, value in item_data.items():
            if hasattr(item, key) and key not in ("item_id", "quote_id", "created_at"):
                old_val = getattr(item, key)
                if key in ("unit_price", "quantity", "discount_value") and value is not None:
                    value = Decimal(str(value))
                if key == "tax_rate" and value is not None:
                    value = Decimal(str(value))
                setattr(item, key, value)
                if old_val != value:
                    changed_fields.append(key)

        if changed_fields:
            item.updated_at = _now()

            # Recalculate line
            line_result = QuoteCalculationService.calculate_line({
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_type": item.discount_type,
                "discount_value": item.discount_value,
                "tax_rate": item.tax_rate,
            })
            for k, v in line_result.items():
                setattr(item, k, v)

            db.flush()
            QuoteCalculationService.recalculate_quote(db, quote)

            quote.updated_by = actor_user_id
            quote.version += 1
            db.flush()

            QuoteEventService.record_event(
                db, quote.quote_id, QuoteEventType.ITEM_UPDATED.value,
                actor_user_id=actor_user_id,
                description=f"Item updated: {item.description}",
                metadata={"item_id": item.item_id, "changed_fields": changed_fields},
            )

            audit.record_audit(
                db,
                actor_user_id=actor_user_id,
                action="quote.item_updated",
                resource_type="quote_items",
                resource_id=item.item_id,
                description=f"Item {item.item_id} updated in quote {quote.quote_number}",
                metadata={"changed_fields": changed_fields},
                request=request,
            )

            db.commit()
            db.refresh(item)

        return item

    @staticmethod
    def remove_item(db, quote, item, actor_user_id: int, request=None):
        if quote.status in TERMINAL_STATUSES:
            raise ValidationError_(f"Cannot modify items on a quote in {quote.status} status.")

        item_desc = item.description
        item_id = item.item_id

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.ITEM_REMOVED.value,
            actor_user_id=actor_user_id,
            description=f"Item removed: {item_desc}",
            metadata={"item_id": item_id, "description": item_desc},
        )

        db.delete(item)
        db.flush()

        QuoteCalculationService.recalculate_quote(db, quote)
        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.item_removed",
            resource_type="quote_items",
            resource_id=item_id,
            description=f"Item removed from quote {quote.quote_number}",
            metadata={"quote_number": quote.quote_number, "item_id": item_id},
            request=request,
        )

        db.commit()

    @staticmethod
    def duplicate_quote(db, source_quote, actor_user_id: int, request=None) -> Quote:
        quote_number, seq_value = QuoteNumberService.generate_quote_number(db)

        new_quote = Quote(
            quote_number=quote_number,
            sequence_value=seq_value,
            quote_type=source_quote.quote_type,
            title=f"{source_quote.title} (Copy)" if source_quote.title else None,
            customer_id=source_quote.customer_id,
            currency=source_quote.currency,
            quote_date=_today(),
            valid_until=source_quote.valid_until,
            notes=source_quote.notes,
            internal_notes=source_quote.internal_notes,
            terms_and_conditions=source_quote.terms_and_conditions,
            payment_term_id=source_quote.payment_term_id,
            template_id=source_quote.template_id,
            company_profile_id=source_quote.company_profile_id,
            owner_user_id=actor_user_id,
            assigned_user_id=actor_user_id,
            assigned_team_id=source_quote.assigned_team_id,
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        db.add(new_quote)
        db.flush()

        # Copy items
        source_items = db.execute(
            sa.select(QuoteItem)
            .where(QuoteItem.quote_id == source_quote.quote_id)
            .order_by(QuoteItem.sort_order)
        ).scalars().all()

        for idx, src_item in enumerate(source_items):
            new_item = QuoteItem(
                quote_id=new_quote.quote_id,
                item_type=src_item.item_type,
                reference_id=src_item.reference_id,
                sku=src_item.sku,
                description=src_item.description,
                quantity=src_item.quantity,
                unit_price=src_item.unit_price,
                discount_type=src_item.discount_type,
                discount_value=src_item.discount_value,
                discount_amount=src_item.discount_amount,
                tax_code=src_item.tax_code,
                tax_rate=src_item.tax_rate,
                tax_amount=src_item.tax_amount,
                gross_amount=src_item.gross_amount,
                net_amount=src_item.net_amount,
                line_total=src_item.line_total,
                sort_order=idx,
                unit_of_measure=src_item.unit_of_measure,
                notes=src_item.notes,
            )
            db.add(new_item)
        db.flush()

        # Copy quote-level discount
        new_quote.discount_type = source_quote.discount_type
        new_quote.discount_value = source_quote.discount_value
        new_quote.additional_charges = source_quote.additional_charges

        QuoteCalculationService.recalculate_quote(db, new_quote)

        QuoteEventService.record_event(
            db, new_quote.quote_id, QuoteEventType.CREATED.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote_number} duplicated from {source_quote.quote_number}",
            metadata={"source_quote_number": source_quote.quote_number},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.duplicated",
            resource_type="quotes",
            resource_id=new_quote.quote_id,
            description=f"Quote {quote_number} duplicated from {source_quote.quote_number}",
            metadata={"source": source_quote.quote_number, "new": quote_number},
            request=request,
        )

        db.commit()
        db.refresh(new_quote)
        return new_quote

    @staticmethod
    def _add_item_internal(db, quote, item_data: dict, sort_order: int) -> QuoteItem:
        """Internal helper to create a QuoteItem without committing."""
        item_type = item_data.get("item_type", QuoteItemType.CUSTOM.value)
        description = item_data.get("description", "")
        if not description:
            raise ValidationError_("Item description is required.")

        item = QuoteItem(
            quote_id=quote.quote_id,
            item_type=item_type,
            reference_id=item_data.get("reference_id"),
            sku=item_data.get("sku"),
            description=description,
            quantity=Decimal(str(item_data.get("quantity", 1))),
            unit_price=Decimal(str(item_data.get("unit_price", 0))),
            discount_type=item_data.get("discount_type"),
            discount_value=Decimal(str(item_data.get("discount_value", 0))),
            tax_code=item_data.get("tax_code"),
            tax_rate=Decimal(str(item_data.get("tax_rate", 0))),
            sort_order=sort_order,
            unit_of_measure=item_data.get("unit_of_measure"),
            notes=item_data.get("notes"),
        )

        # Calculate line values
        line_result = QuoteCalculationService.calculate_line({
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "discount_type": item.discount_type,
            "discount_value": item.discount_value,
            "tax_rate": item.tax_rate,
        })
        for k, v in line_result.items():
            setattr(item, k, v)

        db.add(item)
        return item


# ---------------------------------------------------------------------------
# Workflow Service
# ---------------------------------------------------------------------------

class QuoteWorkflowService:
    @staticmethod
    def _validate_transition(quote, new_status):
        current = quote.status.value if hasattr(quote.status, "value") else quote.status
        allowed = ALLOWED_QUOTE_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValidationError_(
                f"Status transition from {current} to {new_status} is not allowed.",
                field_errors={"status": "Invalid transition."},
            )

    @staticmethod
    def submit_for_approval(db, quote, actor_user_id: int, request=None):
        QuoteWorkflowService._validate_transition(quote, QuoteStatus.PENDING_APPROVAL.value)
        quote.status = QuoteStatus.PENDING_APPROVAL
        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.SUBMITTED_FOR_APPROVAL.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} submitted for approval",
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.submitted_for_approval",
            resource_type="quotes",
            resource_id=quote.quote_id,
            description=f"Quote {quote.quote_number} submitted for approval",
            request=request,
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def approve(db, quote, actor_user_id: int, reason: str = None, request=None):
        QuoteWorkflowService._validate_transition(quote, QuoteStatus.APPROVED.value)
        quote.status = QuoteStatus.APPROVED
        quote.approved_by = actor_user_id
        quote.approved_at = _now()
        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        # Record approval
        approval = QuoteApproval(
            quote_id=quote.quote_id,
            approver_user_id=actor_user_id,
            status=ApprovalStatus.APPROVED,
            reason=reason,
            decided_at=_now(),
        )
        db.add(approval)

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.APPROVED.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} approved",
            metadata={"reason": reason},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.approved",
            resource_type="quotes",
            resource_id=quote.quote_id,
            description=f"Quote {quote.quote_number} approved",
            request=request,
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def reject(db, quote, actor_user_id: int, reason: str = None, request=None):
        QuoteWorkflowService._validate_transition(quote, QuoteStatus.REJECTED.value)
        old_status = quote.status.value if hasattr(quote.status, "value") else quote.status
        quote.status = QuoteStatus.REJECTED
        quote.rejected_at = _now()
        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        # Record rejection
        approval = QuoteApproval(
            quote_id=quote.quote_id,
            approver_user_id=actor_user_id,
            status=ApprovalStatus.REJECTED,
            reason=reason,
            decided_at=_now(),
        )
        db.add(approval)

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.REJECTED.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} rejected",
            metadata={"reason": reason, "previous_status": old_status},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.rejected",
            resource_type="quotes",
            resource_id=quote.quote_id,
            description=f"Quote {quote.quote_number} rejected",
            request=request,
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def send_quote(db, quote, actor_user_id: int, customer_account_id: int = None, request=None):
        QuoteWorkflowService._validate_transition(quote, QuoteStatus.SENT.value)

        # Create immutable version snapshot before sending
        version_obj = QuoteVersionService.create_snapshot(db, quote, actor_user_id)

        quote.status = QuoteStatus.SENT
        quote.sent_at = _now()
        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        # Publish to portal if customer_account_id provided
        if customer_account_id:
            QuotePortalService.publish_to_portal(
                db, quote.quote_id, customer_account_id, actor_user_id
            )

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.SENT.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} sent to customer",
            metadata={"customer_account_id": customer_account_id, "version_id": version_obj.version_id},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.sent",
            resource_type="quotes",
            resource_id=quote.quote_id,
            description=f"Quote {quote.quote_number} sent to customer",
            request=request,
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def cancel_quote(db, quote, actor_user_id: int, reason: str = None, request=None):
        QuoteWorkflowService._validate_transition(quote, QuoteStatus.CANCELLED.value)
        quote.status = QuoteStatus.CANCELLED
        quote.cancelled_at = _now()
        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.CANCELLED.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} cancelled",
            metadata={"reason": reason},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.cancelled",
            resource_type="quotes",
            resource_id=quote.quote_id,
            description=f"Quote {quote.quote_number} cancelled",
            request=request,
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def expire_quote(db, quote, actor_user_id: int = None):
        """Mark an expired quote. Called by background job."""
        if quote.status.value not in (QuoteStatus.SENT.value, QuoteStatus.VIEWED.value):
            return quote

        quote.status = QuoteStatus.EXPIRED
        quote.expired_at = _now()
        quote.version += 1
        db.flush()

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.EXPIRED.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} expired",
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def delete_quote(db, quote, actor_user_id: int, request=None):
        """Soft-delete a quote. Only DRAFT and PENDING_APPROVAL quotes can be deleted."""
        current = quote.status.value if hasattr(quote.status, "value") else quote.status

        # Only allow deletion of drafts and pending approval quotes
        DELETABLE_STATUSES = {QuoteStatus.DRAFT.value, QuoteStatus.PENDING_APPROVAL.value}
        if current not in DELETABLE_STATUSES:
            raise ValidationError_(
                f"Cannot delete a quote with status '{current}'. Only Draft and Pending Approval quotes can be deleted.",
                field_errors={"status": "Quote is not in a deletable state."},
            )

        # Check for linked sales orders
        from sales_orders.models import SalesOrder
        linked_orders = db.execute(
            sa.select(SalesOrder).where(SalesOrder.quote_id == quote.quote_id)
        ).scalars().all()
        if linked_orders:
            order_numbers = [o.order_number for o in linked_orders]
            raise ValidationError_(
                f"This quote cannot be deleted because it is linked to sales order(s): {', '.join(order_numbers)}.",
                field_errors={"quote": "Quote has linked sales orders."},
            )

        # Soft delete
        quote.deleted_at = _now()
        quote.deleted_by = actor_user_id
        quote.updated_by = actor_user_id
        quote.version += 1
        db.flush()

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.CANCELLED.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} deleted",
            metadata={"action": "delete"},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote.deleted",
            resource_type="quotes",
            resource_id=quote.quote_id,
            description=f"Quote {quote.quote_number} soft-deleted",
            request=request,
        )

        db.commit()
        db.refresh(quote)
        return quote


# ---------------------------------------------------------------------------
# Version Service
# ---------------------------------------------------------------------------

class QuoteVersionService:
    @staticmethod
    def create_snapshot(db, quote, actor_user_id: int) -> QuoteVersion:
        """Create an immutable snapshot of the quote for sending."""
        items = db.execute(
            sa.select(QuoteItem)
            .where(QuoteItem.quote_id == quote.quote_id)
            .order_by(QuoteItem.sort_order)
        ).scalars().all()

        items_snapshot = []
        for item in items:
            items_snapshot.append({
                "item_id": item.item_id,
                "item_type": item.item_type.value if hasattr(item.item_type, "value") else item.item_type,
                "reference_id": item.reference_id,
                "sku": item.sku,
                "description": item.description,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "discount_type": item.discount_type.value if item.discount_type else None,
                "discount_value": str(item.discount_value),
                "discount_amount": str(item.discount_amount),
                "tax_code": item.tax_code,
                "tax_rate": str(item.tax_rate),
                "tax_amount": str(item.tax_amount),
                "gross_amount": str(item.gross_amount),
                "net_amount": str(item.net_amount),
                "line_total": str(item.line_total),
                "sort_order": item.sort_order,
                "unit_of_measure": item.unit_of_measure,
                "notes": item.notes,
            })

        snapshot = {
            "quote_number": quote.quote_number,
            "quote_type": quote.quote_type.value if hasattr(quote.quote_type, "value") else quote.quote_type,
            "title": quote.title,
            "customer_id": quote.customer_id,
            "currency": quote.currency,
            "quote_date": str(quote.quote_date) if quote.quote_date else None,
            "valid_until": str(quote.valid_until) if quote.valid_until else None,
            "subtotal": str(quote.subtotal),
            "discount_type": quote.discount_type.value if quote.discount_type else None,
            "discount_value": str(quote.discount_value),
            "discount_amount": str(quote.discount_amount),
            "tax_amount": str(quote.tax_amount),
            "additional_charges": str(quote.additional_charges),
            "grand_total": str(quote.grand_total),
            "notes": quote.notes,
            "terms_and_conditions": quote.terms_and_conditions,
            "items": items_snapshot,
        }

        # Get next revision
        max_rev = db.execute(
            sa.select(sa.func.coalesce(sa.func.max(QuoteVersion.revision), 0))
            .where(QuoteVersion.quote_id == quote.quote_id)
        ).scalar()
        next_revision = max_rev + 1

        # Resolve template version if template is set
        template_version_id = None
        if quote.template_id:
            template = db.get(QuoteTemplate, quote.template_id)
            if template:
                tv = db.execute(
                    sa.select(QuoteTemplateVersion)
                    .where(
                        QuoteTemplateVersion.template_id == quote.template_id,
                        QuoteTemplateVersion.version == template.current_version,
                    )
                ).scalar_one_or_none()
                if tv:
                    template_version_id = tv.template_version_id

        # Snapshot company profile
        company_profile_snapshot = None
        if quote.company_profile_id:
            profile = db.get(CompanyProfile, quote.company_profile_id)
            if profile:
                company_profile_snapshot = {
                    "legal_name": profile.legal_name,
                    "display_name": profile.display_name,
                    "logo_url": profile.logo_url,
                    "address": profile.address,
                    "phone": profile.phone,
                    "email": profile.email,
                    "website": profile.website,
                    "what_we_do": profile.what_we_do,
                    "default_terms_and_conditions": profile.default_terms_and_conditions,
                    "default_footer": profile.default_footer,
                    "bank_name": profile.bank_name,
                    "bank_account_number": profile.bank_account_number,
                    "bank_branch": profile.bank_branch,
                }

        version_obj = QuoteVersion(
            quote_id=quote.quote_id,
            revision=next_revision,
            snapshot=snapshot,
            template_version_id=template_version_id,
            company_profile_snapshot=company_profile_snapshot,
            created_by=actor_user_id,
        )
        db.add(version_obj)
        db.flush()

        return version_obj


# ---------------------------------------------------------------------------
# Template Service
# ---------------------------------------------------------------------------

class QuoteTemplateService:
    @staticmethod
    def create_template(db, payload: dict, actor_user_id: int, request=None) -> QuoteTemplate:
        template = QuoteTemplate(
            name=payload["name"],
            description=payload.get("description"),
            template_type=payload.get("template_type", QuoteType.PRODUCT.value),
            content_config=payload.get("content_config"),
            is_default=payload.get("is_default", False),
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        db.add(template)
        db.flush()

        # Create initial version
        version = QuoteTemplateVersion(
            template_id=template.template_id,
            version=1,
            content_config=payload.get("content_config") or {},
            created_by=actor_user_id,
        )
        db.add(version)

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote_template.created",
            resource_type="quote_templates",
            resource_id=template.template_id,
            description=f"Template '{template.name}' created",
            request=request,
        )

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def update_template(db, template, payload: dict, actor_user_id: int, request=None) -> QuoteTemplate:
        if template.status == QuoteTemplateStatus.ARCHIVED.value:
            raise ValidationError_("Cannot edit an archived template.")

        changed_fields = []
        for key, value in payload.items():
            if hasattr(template, key) and key not in ("template_id", "created_by", "created_at", "current_version"):
                old_val = getattr(template, key)
                setattr(template, key, value)
                if old_val != value:
                    changed_fields.append(key)

        if changed_fields:
            template.updated_by = actor_user_id
            template.version = template.current_version + 1 if "content_config" in changed_fields else template.current_version

            # Create new template version if content changed
            if "content_config" in changed_fields:
                template.current_version += 1
                tv = QuoteTemplateVersion(
                    template_id=template.template_id,
                    version=template.current_version,
                    content_config=template.content_config or {},
                    created_by=actor_user_id,
                )
                db.add(tv)

            db.flush()

            audit.record_audit(
                db,
                actor_user_id=actor_user_id,
                action="quote_template.updated",
                resource_type="quote_templates",
                resource_id=template.template_id,
                description=f"Template '{template.name}' updated",
                metadata={"changed_fields": changed_fields},
                request=request,
            )

            db.commit()
            db.refresh(template)

        return template

    @staticmethod
    def activate_template(db, template, actor_user_id: int, request=None):
        template.status = QuoteTemplateStatus.ACTIVE.value
        template.updated_by = actor_user_id
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote_template.activated",
            resource_type="quote_templates",
            resource_id=template.template_id,
            description=f"Template '{template.name}' activated",
            request=request,
        )

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def deactivate_template(db, template, actor_user_id: int, request=None):
        template.status = QuoteTemplateStatus.INACTIVE.value
        template.updated_by = actor_user_id
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="quote_template.deactivated",
            resource_type="quote_templates",
            resource_id=template.template_id,
            description=f"Template '{template.name}' deactivated",
            request=request,
        )

        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get_default_for_type(db, quote_type: str) -> Optional[QuoteTemplate]:
        """Get the default active template for a given quote type."""
        template = db.execute(
            sa.select(QuoteTemplate).where(
                QuoteTemplate.is_default == sa.true(),
                QuoteTemplate.status == QuoteTemplateStatus.ACTIVE.value,
                QuoteTemplate.template_type == quote_type,
            )
        ).scalar_one_or_none()

        if template is None:
            # Fall back to default overall template
            template = db.execute(
                sa.select(QuoteTemplate).where(
                    QuoteTemplate.is_default == sa.true(),
                    QuoteTemplate.status == QuoteTemplateStatus.ACTIVE.value,
                )
            ).scalar_one_or_none()

        return template


# ---------------------------------------------------------------------------
# Portal Service
# ---------------------------------------------------------------------------

class QuotePortalService:
    @staticmethod
    def publish_to_portal(db, quote_id: int, customer_account_id: int, actor_user_id: int):
        """Publish a sent quote to the client portal."""
        existing = db.execute(
            sa.select(QuotePortalAccess).where(
                QuotePortalAccess.quote_id == quote_id,
                QuotePortalAccess.customer_account_id == customer_account_id,
            )
        ).scalar_one_or_none()

        if existing:
            existing.visibility = "VISIBLE"
            existing.published_at = _now()
            existing.revoked_at = None
        else:
            access = QuotePortalAccess(
                quote_id=quote_id,
                customer_account_id=customer_account_id,
                visibility="VISIBLE",
                published_at=_now(),
            )
            db.add(access)

        db.flush()

        QuoteEventService.record_event(
            db, quote_id, QuoteEventType.PORTAL_PUBLISHED.value,
            actor_user_id=actor_user_id,
            description="Quote published to client portal",
            metadata={"customer_account_id": customer_account_id},
        )

    @staticmethod
    def client_accept(db, quote, portal_user_id: int, customer_account_id: int, comment: str = None):
        """Client accepts a quote from the portal."""
        if quote.status.value not in (QuoteStatus.SENT.value, QuoteStatus.VIEWED.value):
            raise ValidationError_("This quote cannot be accepted in its current state.")

        if quote.valid_until and quote.valid_until < _today():
            raise ValidationError_("This quote has expired.")

        quote.status = QuoteStatus.ACCEPTED
        quote.accepted_at = _now()
        quote.version += 1
        db.flush()

        response = QuoteClientResponse(
            quote_id=quote.quote_id,
            portal_user_id=portal_user_id,
            customer_account_id=customer_account_id,
            decision=ClientResponseDecision.ACCEPT,
            comment=comment,
        )
        db.add(response)

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.ACCEPTED.value,
            actor_portal_user_id=portal_user_id,
            actor_type="PORTAL_USER",
            description="Quote accepted by client",
            metadata={"customer_account_id": customer_account_id, "comment": comment},
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def client_reject(db, quote, portal_user_id: int, customer_account_id: int, comment: str = None):
        """Client rejects a quote from the portal."""
        if quote.status.value not in (QuoteStatus.SENT.value, QuoteStatus.VIEWED.value):
            raise ValidationError_("This quote cannot be rejected in its current state.")

        quote.status = QuoteStatus.REJECTED
        quote.rejected_at = _now()
        quote.version += 1
        db.flush()

        response = QuoteClientResponse(
            quote_id=quote.quote_id,
            portal_user_id=portal_user_id,
            customer_account_id=customer_account_id,
            decision=ClientResponseDecision.DECLINE,
            comment=comment,
        )
        db.add(response)

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.DECLINED.value,
            actor_portal_user_id=portal_user_id,
            actor_type="PORTAL_USER",
            description="Quote declined by client",
            metadata={"customer_account_id": customer_account_id, "comment": comment},
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def client_acknowledge(db, quote, portal_user_id: int, customer_account_id: int, comment: str = None):
        """Client acknowledges receipt of a quote."""
        if quote.status.value == QuoteStatus.SENT.value:
            quote.status = QuoteStatus.VIEWED
            quote.viewed_at = _now()
            quote.version += 1
            db.flush()

        response = QuoteClientResponse(
            quote_id=quote.quote_id,
            portal_user_id=portal_user_id,
            customer_account_id=customer_account_id,
            decision=ClientResponseDecision.ACKNOWLEDGED,
            comment=comment,
        )
        db.add(response)

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.VIEWED.value,
            actor_portal_user_id=portal_user_id,
            actor_type="PORTAL_USER",
            description="Quote acknowledged by client",
            metadata={"customer_account_id": customer_account_id},
        )

        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def client_request_changes(db, quote, portal_user_id: int, customer_account_id: int, comment: str = None):
        """Client requests changes to a quote."""
        if quote.status.value not in (QuoteStatus.SENT.value, QuoteStatus.VIEWED.value):
            raise ValidationError_("This quote cannot be changed in its current state.")

        response = QuoteClientResponse(
            quote_id=quote.quote_id,
            portal_user_id=portal_user_id,
            customer_account_id=customer_account_id,
            decision=ClientResponseDecision.CHANGE_REQUESTED,
            comment=comment,
        )
        db.add(response)

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.CHANGE_REQUESTED.value,
            actor_portal_user_id=portal_user_id,
            actor_type="PORTAL_USER",
            description="Client requested changes",
            metadata={"customer_account_id": customer_account_id, "comment": comment},
        )

        db.commit()
        return response


# ---------------------------------------------------------------------------
# Document Service
# ---------------------------------------------------------------------------

class QuoteDocumentService:
    @staticmethod
    def generate_document(db, quote, actor_user_id: int, request=None):
        """Generate a document record for the quote (PDF generation itself is async)."""
        # Get latest version
        version_obj = db.execute(
            sa.select(QuoteVersion)
            .where(QuoteVersion.quote_id == quote.quote_id)
            .order_by(sa.desc(QuoteVersion.revision))
            .limit(1)
        ).scalar_one_or_none()

        if version_obj is None:
            version_obj = QuoteVersionService.create_snapshot(db, quote, actor_user_id)

        # Create document record
        file_name = f"{quote.quote_number}_v{version_obj.revision}.pdf"
        content_hash = hashlib.sha256(
            json.dumps(version_obj.snapshot, default=str).encode()
        ).hexdigest()

        document = QuoteDocument(
            quote_id=quote.quote_id,
            quote_version_id=version_obj.version_id,
            document_type="PDF",
            file_name=file_name,
            content_hash=content_hash,
            created_by=actor_user_id,
        )
        db.add(document)

        QuoteEventService.record_event(
            db, quote.quote_id, QuoteEventType.DOCUMENT_GENERATED.value,
            actor_user_id=actor_user_id,
            description=f"Document generated: {file_name}",
            metadata={"document_id": document.document_id, "file_name": file_name},
        )

        db.commit()
        db.refresh(document)
        return document


# ---------------------------------------------------------------------------
# Event Service
# ---------------------------------------------------------------------------

class QuoteEventService:
    @staticmethod
    def record_event(
        db,
        quote_id: int,
        event_type: str,
        actor_user_id: int = None,
        actor_portal_user_id: int = None,
        actor_type: str = "INTERNAL_USER",
        description: str = None,
        metadata: dict = None,
    ):
        event = QuoteEvent(
            quote_id=quote_id,
            actor_user_id=actor_user_id,
            actor_portal_user_id=actor_portal_user_id,
            actor_type=actor_type,
            event_type=event_type,
            description=description,
            metadata_=metadata,
        )
        db.add(event)
        db.flush()
        return event
