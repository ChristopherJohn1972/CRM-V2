import logging
import secrets
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import sqlalchemy as sa

from clients.models import Customer
from common import audit
from common.events import DomainEvent, EventBus
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from quotes.models import Quote, QuoteItem
from sales_orders.enums import (
    ALLOWED_ORDER_TRANSITIONS,
    ALLOWED_PAYMENT_TRANSITIONS,
    ALLOWED_RECEIPT_TRANSITIONS,
    DiscountType,
    OrderEventType,
    OrderItemType,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    PaymentOverallStatus,
    PaymentStatus,
    ReceiptStatus,
    ReceiptTemplateStatus,
    TERMINAL_ORDER_STATUSES,
)
from sales_orders.models import (
    OrderAdjustment,
    OrderPayment,
    Receipt,
    ReceiptNumberSequence,
    ReceiptTemplate,
    ReceiptTemplateVersion,
    ReceiptVerification,
    SalesOrder,
    SalesOrderDocument,
    SalesOrderEvent,
    SalesOrderItem,
    SalesOrderPortalAccess,
    SONumberSequence,
)

logger = logging.getLogger(__name__)

SO_NUMBER_BUCKET = "SALES_ORDER"
RECEIPT_NUMBER_BUCKET = "RECEIPT"
ROUNDING = ROUND_HALF_UP
PRECISION = Decimal("0.01")


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _today():
    return date.today()


# ---------------------------------------------------------------------------
# Number Services
# ---------------------------------------------------------------------------

class SONumberService:
    @staticmethod
    def generate_order_number(db) -> tuple:
        """Atomically generate the next SO number. Returns (order_number, sequence_value)."""
        row = db.execute(
            sa.select(SONumberSequence)
            .where(SONumberSequence.bucket == SO_NUMBER_BUCKET)
            .with_for_update()
        ).scalar_one_or_none()

        if row is None:
            row = SONumberSequence(bucket=SO_NUMBER_BUCKET, last_value=0, min_length=4)
            db.add(row)
            db.flush()

        # Reconcile against existing order numbers
        max_existing = db.execute(
            sa.select(sa.func.max(SalesOrder.sequence_value))
        ).scalar()
        if max_existing and max_existing > row.last_value:
            row.last_value = max_existing

        row.last_value += 1
        order_number = f"SO{str(row.last_value).zfill(row.min_length)}"
        return order_number, row.last_value


class ReceiptNumberService:
    @staticmethod
    def generate_receipt_number(db) -> tuple:
        """Atomically generate the next receipt number. Returns (receipt_number, sequence_value)."""
        row = db.execute(
            sa.select(ReceiptNumberSequence)
            .where(ReceiptNumberSequence.bucket == RECEIPT_NUMBER_BUCKET)
            .with_for_update()
        ).scalar_one_or_none()

        if row is None:
            row = ReceiptNumberSequence(bucket=RECEIPT_NUMBER_BUCKET, last_value=0, min_length=4)
            db.add(row)
            db.flush()

        max_existing = db.execute(
            sa.select(sa.func.max(Receipt.receipt_id))
        ).scalar()
        if max_existing and max_existing > row.last_value:
            row.last_value = max_existing

        row.last_value += 1
        receipt_number = f"RCT{str(row.last_value).zfill(row.min_length)}"
        return receipt_number, row.last_value


# ---------------------------------------------------------------------------
# Calculation Engine
# ---------------------------------------------------------------------------

class SalesOrderCalculationService:
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
    def calculate_order_state(
        items_data: list,
        adjustments_data: list = None,
        order_discount=None,
        additional_charges=None,
        currency="KES",
    ) -> dict:
        """Calculate full order from a list of item data dicts and adjustments."""
        lines = []
        total_discount = Decimal("0.00")
        total_tax = Decimal("0.00")
        subtotal = Decimal("0.00")

        for item_data in items_data:
            line = SalesOrderCalculationService.calculate_line(item_data)
            lines.append(line)
            total_discount += line["discount_amount"]
            total_tax += line["tax_amount"]
            subtotal += line["net_amount"]

        total_discount = total_discount.quantize(PRECISION, rounding=ROUNDING)
        total_tax = total_tax.quantize(PRECISION, rounding=ROUNDING)
        subtotal = subtotal.quantize(PRECISION, rounding=ROUNDING)

        # Order-level discount
        order_discount_amount = Decimal("0.00")
        if order_discount:
            qd_type = order_discount.get("discount_type")
            qd_value = Decimal(str(order_discount.get("discount_value", 0)))
            if qd_type == DiscountType.PERCENTAGE.value:
                order_discount_amount = (subtotal * qd_value / Decimal("100")).quantize(
                    PRECISION, rounding=ROUNDING
                )
            elif qd_type == DiscountType.FIXED.value:
                order_discount_amount = qd_value.quantize(PRECISION, rounding=ROUNDING)
        total_discount += order_discount_amount

        # Additional charges from adjustments
        charges = Decimal(str(additional_charges or 0)).quantize(PRECISION, rounding=ROUNDING)
        if adjustments_data:
            for adj in adjustments_data:
                adj_amount = Decimal(str(adj.get("amount", 0))).quantize(PRECISION, rounding=ROUNDING)
                charges += adj_amount

        grand_total = (subtotal - order_discount_amount + total_tax + charges).quantize(
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
    def recalculate_order(db, order) -> dict:
        """Recalculate a persisted order from its items and adjustments."""
        items = db.execute(
            sa.select(SalesOrderItem)
            .where(SalesOrderItem.order_id == order.order_id)
            .order_by(SalesOrderItem.sort_order)
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

        adjustments = db.execute(
            sa.select(OrderAdjustment)
            .where(OrderAdjustment.order_id == order.order_id)
            .order_by(OrderAdjustment.sort_order)
        ).scalars().all()

        adjustments_data = []
        for adj in adjustments:
            adjustments_data.append({
                "amount": adj.amount,
            })

        order_discount = None
        if order.discount_type:
            order_discount = {
                "discount_type": order.discount_type,
                "discount_value": order.discount_value,
            }

        result = SalesOrderCalculationService.calculate_order_state(
            items_data,
            adjustments_data=adjustments_data,
            order_discount=order_discount,
            additional_charges=order.additional_charges,
            currency=order.currency,
        )

        # Update order totals
        order.subtotal = result["subtotal"]
        order.discount_amount = result["total_discount"]
        order.tax_amount = result["total_tax"]
        order.additional_charges = result["additional_charges"]
        order.grand_total = result["grand_total"]

        # Update balance
        order.balance_due = (order.grand_total - order.amount_paid).quantize(
            PRECISION, rounding=ROUNDING
        )
        if order.balance_due < 0:
            order.balance_due = Decimal("0.00")

        # Update payment status
        order.payment_status = SalesOrderCalculationService._determine_payment_status(
            order.grand_total, order.amount_paid
        )

        db.flush()
        return result

    @staticmethod
    def _determine_payment_status(grand_total: Decimal, amount_paid: Decimal) -> str:
        """Determine payment status from totals."""
        if amount_paid <= 0:
            return PaymentOverallStatus.UNPAID.value
        if amount_paid >= grand_total:
            return PaymentOverallStatus.PAID.value
        return PaymentOverallStatus.PARTIALLY_PAID.value


# ---------------------------------------------------------------------------
# Order Event Service
# ---------------------------------------------------------------------------

class SalesOrderEventService:
    @staticmethod
    def record_event(
        db,
        order_id: int,
        event_type: str,
        actor_user_id: int = None,
        description: str = None,
        metadata: dict = None,
    ):
        event = SalesOrderEvent(
            order_id=order_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            description=description,
            metadata_=metadata,
        )
        db.add(event)
        db.flush()
        return event


# ---------------------------------------------------------------------------
# Sales Order Service (CRUD)
# ---------------------------------------------------------------------------

class SalesOrderService:
    @staticmethod
    def create_order(db, payload: dict, actor_user_id: int, source="DIRECT", quote_id=None, request=None) -> SalesOrder:
        """Create a new sales order (direct or from quote)."""
        customer_id = payload.get("customer_id")
        if not customer_id:
            raise ValidationError_("customer_id is required.")

        customer = db.get(Customer, customer_id)
        if customer is None:
            raise NotFoundError("Customer not found.")

        order_number, seq_value = SONumberService.generate_order_number(db)

        order_date = payload.get("order_date") or _today()

        order = SalesOrder(
            order_number=order_number,
            sequence_value=seq_value,
            customer_id=customer_id,
            source=source,
            quote_id=quote_id,
            order_date=order_date,
            expected_delivery_date=payload.get("expected_delivery_date"),
            currency=payload.get("currency", "KES"),
            notes=payload.get("notes"),
            internal_notes=payload.get("internal_notes"),
            terms_and_conditions=payload.get("terms_and_conditions"),
            payment_term_id=payload.get("payment_term_id"),
            company_profile_id=payload.get("company_profile_id"),
            owner_user_id=actor_user_id,
            assigned_user_id=payload.get("assigned_user_id", actor_user_id),
            assigned_team_id=payload.get("assigned_team_id"),
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )

        # Apply order-level discount
        if payload.get("discount_type") and payload.get("discount_value") is not None:
            order.discount_type = payload["discount_type"]
            order.discount_value = Decimal(str(payload["discount_value"]))

        if payload.get("additional_charges") is not None:
            order.additional_charges = Decimal(str(payload["additional_charges"]))

        db.add(order)
        db.flush()

        # Add initial items if provided
        items_payload = payload.get("items", [])
        for idx, item_data in enumerate(items_payload):
            SalesOrderService._add_item_internal(db, order, item_data, idx)

        # Recalculate
        SalesOrderCalculationService.recalculate_order(db, order)

        event_type = OrderEventType.CONVERTED_FROM_QUOTE.value if source == OrderSource.QUOTE.value else OrderEventType.CREATED.value
        description = f"Order {order_number} created" if source == OrderSource.DIRECT.value else f"Order {order_number} converted from quote"

        SalesOrderEventService.record_event(
            db, order.order_id, event_type,
            actor_user_id=actor_user_id,
            description=description,
            metadata={"customer_id": customer_id, "source": source, "quote_id": quote_id},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.created",
            resource_type="sales_orders",
            resource_id=order.order_id,
            description=f"Sales order {order_number} created",
            metadata={"order_number": order_number, "source": source},
            request=request,
        )

        EventBus.publish(
            DomainEvent(
                event_type="SalesOrderCreated",
                customer_id=customer_id,
                source_module="sales_orders",
                actor_user_id=actor_user_id,
                actor_type="INTERNAL_USER",
                summary=f"Order {order_number} created",
                reference_type="sales_orders",
                reference_id=order.order_id,
                payload={"order_number": order_number},
            )
        )

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def update_order(db, order, payload: dict, actor_user_id: int, request=None) -> SalesOrder:
        """Update an existing sales order."""
        if order.status.value in TERMINAL_ORDER_STATUSES:
            raise ValidationError_(f"Cannot update an order in {order.status.value} status.")

        version = payload.pop("version", None)
        if version is not None and int(version) != order.version:
            raise ConflictError(
                f"Version mismatch. Current version is {order.version}.",
                error_code="optimistic_lock",
            )

        # Prevent editing items through update
        payload.pop("items", None)

        changed_fields = []
        for key, value in payload.items():
            if hasattr(order, key) and key not in ("order_id", "order_number", "sequence_value", "created_by", "created_at", "amount_paid", "balance_due", "payment_status"):
                old_val = getattr(order, key)
                if key in ("discount_value", "additional_charges") and value is not None:
                    value = Decimal(str(value))
                setattr(order, key, value)
                if old_val != value:
                    changed_fields.append(key)

        if changed_fields:
            order.updated_by = actor_user_id
            order.version += 1
            db.flush()

            # Recalculate if financial fields changed
            financial_fields = {"discount_type", "discount_value", "additional_charges", "tax_amount"}
            if financial_fields.intersection(set(changed_fields)):
                SalesOrderCalculationService.recalculate_order(db, order)

            SalesOrderEventService.record_event(
                db, order.order_id, OrderEventType.EDITED.value,
                actor_user_id=actor_user_id,
                description=f"Order {order.order_number} updated",
                metadata={"changed_fields": changed_fields},
            )

            audit.record_audit(
                db,
                actor_user_id=actor_user_id,
                action="sales_order.updated",
                resource_type="sales_orders",
                resource_id=order.order_id,
                description=f"Order {order.order_number} updated",
                metadata={"changed_fields": changed_fields},
                request=request,
            )

            db.commit()
            db.refresh(order)

        return order

    @staticmethod
    def add_item(db, order, item_data: dict, actor_user_id: int, request=None) -> SalesOrderItem:
        if order.status.value in TERMINAL_ORDER_STATUSES:
            raise ValidationError_(f"Cannot modify items on an order in {order.status.value} status.")

        max_order = db.execute(
            sa.select(sa.func.coalesce(sa.func.max(SalesOrderItem.sort_order), 0))
            .where(SalesOrderItem.order_id == order.order_id)
        ).scalar()
        item_data["sort_order"] = item_data.get("sort_order", max_order + 1)

        item = SalesOrderService._add_item_internal(db, order, item_data, item_data["sort_order"])
        db.flush()

        SalesOrderCalculationService.recalculate_order(db, order)
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.ITEM_ADDED.value,
            actor_user_id=actor_user_id,
            description=f"Item added: {item.description}",
            metadata={"item_id": item.item_id, "description": item.description},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.item_added",
            resource_type="sales_order_items",
            resource_id=item.item_id,
            description=f"Item added to order {order.order_number}",
            metadata={"order_number": order.order_number, "item_id": item.item_id},
            request=request,
        )

        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_item(db, order, item, item_data: dict, actor_user_id: int, request=None) -> SalesOrderItem:
        if order.status.value in TERMINAL_ORDER_STATUSES:
            raise ValidationError_(f"Cannot modify items on an order in {order.status.value} status.")

        changed_fields = []
        for key, value in item_data.items():
            if hasattr(item, key) and key not in ("item_id", "order_id", "created_at"):
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
            line_result = SalesOrderCalculationService.calculate_line({
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_type": item.discount_type,
                "discount_value": item.discount_value,
                "tax_rate": item.tax_rate,
            })
            for k, v in line_result.items():
                setattr(item, k, v)

            db.flush()
            SalesOrderCalculationService.recalculate_order(db, order)
            order.updated_by = actor_user_id
            order.version += 1
            db.flush()

            SalesOrderEventService.record_event(
                db, order.order_id, OrderEventType.ITEM_UPDATED.value,
                actor_user_id=actor_user_id,
                description=f"Item updated: {item.description}",
                metadata={"item_id": item.item_id, "changed_fields": changed_fields},
            )

            audit.record_audit(
                db,
                actor_user_id=actor_user_id,
                action="sales_order.item_updated",
                resource_type="sales_order_items",
                resource_id=item.item_id,
                description=f"Item {item.item_id} updated in order {order.order_number}",
                metadata={"changed_fields": changed_fields},
                request=request,
            )

            db.commit()
            db.refresh(item)

        return item

    @staticmethod
    def remove_item(db, order, item, actor_user_id: int, request=None):
        if order.status.value in TERMINAL_ORDER_STATUSES:
            raise ValidationError_(f"Cannot modify items on an order in {order.status.value} status.")

        item_desc = item.description
        item_id = item.item_id

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.ITEM_REMOVED.value,
            actor_user_id=actor_user_id,
            description=f"Item removed: {item_desc}",
            metadata={"item_id": item_id, "description": item_desc},
        )

        db.delete(item)
        db.flush()

        SalesOrderCalculationService.recalculate_order(db, order)
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.item_removed",
            resource_type="sales_order_items",
            resource_id=item_id,
            description=f"Item removed from order {order.order_number}",
            metadata={"order_number": order.order_number, "item_id": item_id},
            request=request,
        )

        db.commit()

    @staticmethod
    def delete_order(db, order, actor_user_id: int, request=None) -> None:
        """Soft-delete a sales order. Blocks if order has financial activity."""
        if order.deleted_at is not None:
            raise ValidationError_("This order has already been deleted.")

        # Check for financial dependencies
        payment_count = db.execute(
            sa.select(sa.func.count())
            .select_from(OrderPayment.__table__)
            .where(OrderPayment.order_id == order.order_id)
        ).scalar()

        receipt_count = db.execute(
            sa.select(sa.func.count())
            .select_from(Receipt.__table__)
            .where(Receipt.order_id == order.order_id)
        ).scalar()

        if payment_count > 0 or receipt_count > 0:
            raise ValidationError_(
                "Order cannot be deleted because it has associated financial transactions. "
                "Cancel or archive the order instead."
            )

        order.deleted_at = _now()
        order.deleted_by = actor_user_id
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, "DELETED",
            actor_user_id=actor_user_id,
            description=f"Order {order.order_number} deleted",
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.deleted",
            resource_type="sales_orders",
            resource_id=order.order_id,
            description=f"Order {order.order_number} deleted",
            request=request,
        )

        db.commit()

    @staticmethod
    def _add_item_internal(db, order, item_data: dict, sort_order: int) -> SalesOrderItem:
        """Internal helper to create a SalesOrderItem without committing."""
        item_type = item_data.get("item_type", OrderItemType.CUSTOM.value)
        description = item_data.get("description", "")
        if not description:
            raise ValidationError_("Item description is required.")

        item = SalesOrderItem(
            order_id=order.order_id,
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
        line_result = SalesOrderCalculationService.calculate_line({
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
# Order Workflow Service
# ---------------------------------------------------------------------------

class SalesOrderWorkflowService:
    @staticmethod
    def _validate_transition(order, new_status):
        current = order.status.value if hasattr(order.status, "value") else order.status
        allowed = ALLOWED_ORDER_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValidationError_(
                f"Status transition from {current} to {new_status} is not allowed.",
                field_errors={"status": "Invalid transition."},
            )

    @staticmethod
    def confirm(db, order, actor_user_id: int, request=None):
        SalesOrderWorkflowService._validate_transition(order, OrderStatus.CONFIRMED.value)

        # Recalculate before confirmation to ensure accuracy
        SalesOrderCalculationService.recalculate_order(db, order)

        order.status = OrderStatus.CONFIRMED
        order.confirmed_by = actor_user_id
        order.confirmed_at = _now()
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.CONFIRMED.value,
            actor_user_id=actor_user_id,
            description=f"Order {order.order_number} confirmed",
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.confirmed",
            resource_type="sales_orders",
            resource_id=order.order_id,
            description=f"Order {order.order_number} confirmed",
            request=request,
        )

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def cancel(db, order, actor_user_id: int, reason: str = None, request=None):
        SalesOrderWorkflowService._validate_transition(order, OrderStatus.CANCELLED.value)

        order.status = OrderStatus.CANCELLED
        order.cancelled_by = actor_user_id
        order.cancelled_at = _now()
        order.cancellation_reason = reason
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.CANCELLED.value,
            actor_user_id=actor_user_id,
            description=f"Order {order.order_number} cancelled",
            metadata={"reason": reason},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.cancelled",
            resource_type="sales_orders",
            resource_id=order.order_id,
            description=f"Order {order.order_number} cancelled",
            request=request,
        )

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def submit_for_approval(db, order, actor_user_id: int, request=None):
        SalesOrderWorkflowService._validate_transition(order, OrderStatus.PENDING_APPROVAL.value)
        order.status = OrderStatus.PENDING_APPROVAL
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.SUBMITTED_FOR_APPROVAL.value,
            actor_user_id=actor_user_id,
            description=f"Order {order.order_number} submitted for approval",
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.submitted_for_approval",
            resource_type="sales_orders",
            resource_id=order.order_id,
            description=f"Order {order.order_number} submitted for approval",
            request=request,
        )

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def approve(db, order, actor_user_id: int, request=None):
        SalesOrderWorkflowService._validate_transition(order, OrderStatus.APPROVED.value)
        order.status = OrderStatus.APPROVED
        order.approved_by = actor_user_id
        order.approved_at = _now()
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.APPROVED.value,
            actor_user_id=actor_user_id,
            description=f"Order {order.order_number} approved",
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="sales_order.approved",
            resource_type="sales_orders",
            resource_id=order.order_id,
            description=f"Order {order.order_number} approved",
            request=request,
        )

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def mark_processing(db, order, actor_user_id: int, request=None):
        SalesOrderWorkflowService._validate_transition(order, OrderStatus.PROCESSING.value)
        order.status = OrderStatus.PROCESSING
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.PROCESSING.value,
            actor_user_id=actor_user_id,
            description=f"Order {order.order_number} is now processing",
        )

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def mark_fulfilled(db, order, actor_user_id: int, request=None):
        SalesOrderWorkflowService._validate_transition(order, OrderStatus.FULFILLED.value)
        order.status = OrderStatus.FULFILLED
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.FULFILLED.value,
            actor_user_id=actor_user_id,
            description=f"Order {order.order_number} fulfilled",
        )

        db.commit()
        db.refresh(order)
        return order


# ---------------------------------------------------------------------------
# Quote Conversion Service
# ---------------------------------------------------------------------------

class QuoteConversionService:
    @staticmethod
    def convert_quote_to_order(db, quote, actor_user_id: int, request=None) -> SalesOrder:
        """Convert an accepted quote into a Sales Order."""
        # Validate quote status
        if quote.status.value != "ACCEPTED":
            raise ValidationError_(
                f"Only ACCEPTED quotes can be converted. Current status: {quote.status.value}."
            )

        # Check for existing order (idempotency)
        existing = db.execute(
            sa.select(SalesOrder)
            .where(SalesOrder.quote_id == quote.quote_id)
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(
                f"This quote has already been converted to order {existing.order_number}.",
                error_code="quote_already_converted",
            )

        # Copy quote items into order payload
        quote_items = db.execute(
            sa.select(QuoteItem)
            .where(QuoteItem.quote_id == quote.quote_id)
            .order_by(QuoteItem.sort_order)
        ).scalars().all()

        items_payload = []
        for qi in quote_items:
            items_payload.append({
                "item_type": qi.item_type.value if hasattr(qi.item_type, "value") else qi.item_type,
                "reference_id": qi.reference_id,
                "sku": qi.sku,
                "description": qi.description,
                "quantity": str(qi.quantity),
                "unit_price": str(qi.unit_price),
                "discount_type": qi.discount_type.value if qi.discount_type else None,
                "discount_value": str(qi.discount_value),
                "tax_code": qi.tax_code,
                "tax_rate": str(qi.tax_rate),
                "unit_of_measure": qi.unit_of_measure,
                "notes": qi.notes,
            })

        order_payload = {
            "customer_id": quote.customer_id,
            "expected_delivery_date": None,
            "currency": quote.currency,
            "discount_type": quote.discount_type.value if quote.discount_type else None,
            "discount_value": str(quote.discount_value) if quote.discount_value else None,
            "additional_charges": str(quote.additional_charges) if quote.additional_charges else None,
            "notes": quote.notes,
            "internal_notes": quote.internal_notes,
            "terms_and_conditions": quote.terms_and_conditions,
            "payment_term_id": quote.payment_term_id,
            "company_profile_id": quote.company_profile_id,
            "items": items_payload,
        }

        order = SalesOrderService.create_order(
            db, order_payload, actor_user_id,
            source=OrderSource.QUOTE.value,
            quote_id=quote.quote_id,
            request=request,
        )

        # Record conversion event on the quote
        from quotes.services import QuoteEventService
        QuoteEventService.record_event(
            db, quote.quote_id, OrderEventType.CONVERTED_FROM_QUOTE.value,
            actor_user_id=actor_user_id,
            description=f"Quote {quote.quote_number} converted to order {order.order_number}",
            metadata={"order_id": order.order_id, "order_number": order.order_number},
        )

        return order


# ---------------------------------------------------------------------------
# Payment Service
# ---------------------------------------------------------------------------

class PaymentService:
    @staticmethod
    def record_payment(db, payload: dict, actor_user_id: int, request=None) -> OrderPayment:
        """Record a new payment against a sales order."""
        order_id = payload.get("order_id")
        if not order_id:
            raise ValidationError_("order_id is required.")

        order = db.get(SalesOrder, order_id)
        if order is None:
            raise NotFoundError("Sales order not found.")

        if order.status.value in TERMINAL_ORDER_STATUSES:
            raise ValidationError_(f"Cannot record payment for an order in {order.status.value} status.")

        amount = Decimal(str(payload.get("amount", 0)))
        if amount <= 0:
            raise ValidationError_("Payment amount must be greater than zero.")

        if amount > order.balance_due and order.balance_due > 0:
            raise ValidationError_(
                f"Payment amount ({amount}) exceeds balance due ({order.balance_due}).",
                field_errors={"amount": "Payment exceeds balance."},
            )

        payment_method = payload.get("payment_method")
        if not payment_method:
            raise ValidationError_("payment_method is required.")

        # Check idempotency
        idempotency_key = payload.get("idempotency_key")
        if idempotency_key:
            existing = db.execute(
                sa.select(OrderPayment)
                .where(OrderPayment.idempotency_key == idempotency_key)
            ).scalar_one_or_none()
            if existing:
                raise ConflictError("Payment with this idempotency key already exists.", error_code="duplicate_payment")

        payment_reference = payload.get("payment_reference") or f"PAY-{order.order_number}-{secrets.token_hex(4).upper()}"

        payment = OrderPayment(
            payment_reference=payment_reference,
            order_id=order.order_id,
            customer_id=order.customer_id,
            amount=amount,
            currency=order.currency,
            payment_method=payment_method,
            status=PaymentStatus.PENDING.value,
            gateway_reference=payload.get("gateway_reference"),
            notes=payload.get("notes"),
            received_at=_now(),
            idempotency_key=idempotency_key,
            created_by=actor_user_id,
        )
        db.add(payment)
        db.flush()

        # Update order
        order.amount_paid = (order.amount_paid + amount).quantize(PRECISION, rounding=ROUNDING)
        order.balance_due = (order.grand_total - order.amount_paid).quantize(PRECISION, rounding=ROUNDING)
        if order.balance_due < 0:
            order.balance_due = Decimal("0.00")
        order.payment_status = SalesOrderCalculationService._determine_payment_status(
            order.grand_total, order.amount_paid
        )
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        SalesOrderEventService.record_event(
            db, order.order_id, OrderEventType.PAYMENT_RECORDED.value,
            actor_user_id=actor_user_id,
            description=f"Payment of {amount} {order.currency} recorded",
            metadata={"payment_id": payment.payment_id, "amount": str(amount)},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="payment.recorded",
            resource_type="order_payments",
            resource_id=payment.payment_id,
            description=f"Payment of {amount} {order.currency} recorded for order {order.order_number}",
            metadata={"order_number": order.order_number, "payment_reference": payment_reference},
            request=request,
        )

        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def confirm_payment(db, payment, actor_user_id: int, request=None) -> Receipt:
        """Confirm a pending payment and generate receipt."""
        if payment.status.value != PaymentStatus.PENDING.value:
            raise ValidationError_(f"Payment is not in PENDING status. Current: {payment.status.value}.")

        payment.status = PaymentStatus.CONFIRMED
        payment.confirmed_at = _now()
        payment.confirmed_by = actor_user_id
        db.flush()

        order = db.get(SalesOrder, payment.order_id)

        # Generate receipt
        receipt = ReceiptService.generate_receipt(db, payment, actor_user_id, request=request)

        SalesOrderEventService.record_event(
            db, payment.order_id, OrderEventType.PAYMENT_CONFIRMED.value,
            actor_user_id=actor_user_id,
            description=f"Payment {payment.payment_reference} confirmed",
            metadata={"payment_id": payment.payment_id, "receipt_id": receipt.receipt_id},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="payment.confirmed",
            resource_type="order_payments",
            resource_id=payment.payment_id,
            description=f"Payment {payment.payment_reference} confirmed for order {order.order_number}",
            metadata={"order_number": order.order_number},
            request=request,
        )

        db.commit()
        db.refresh(payment)
        return receipt

    @staticmethod
    def reverse_payment(db, payment, actor_user_id: int, reason: str = None, request=None):
        """Reverse/void a confirmed payment."""
        if payment.status.value != PaymentStatus.CONFIRMED.value:
            raise ValidationError_(f"Payment is not in CONFIRMED status. Current: {payment.status.value}.")

        payment.status = PaymentStatus.REVERSED
        payment.reversed_at = _now()
        payment.reversed_by = actor_user_id
        payment.reversal_reason = reason
        db.flush()

        order = db.get(SalesOrder, payment.order_id)

        # Update order amounts
        order.amount_paid = (order.amount_paid - payment.amount).quantize(PRECISION, rounding=ROUNDING)
        if order.amount_paid < 0:
            order.amount_paid = Decimal("0.00")
        order.balance_due = (order.grand_total - order.amount_paid).quantize(PRECISION, rounding=ROUNDING)
        order.payment_status = SalesOrderCalculationService._determine_payment_status(
            order.grand_total, order.amount_paid
        )
        order.updated_by = actor_user_id
        order.version += 1
        db.flush()

        # Void associated receipt
        receipt = db.execute(
            sa.select(Receipt).where(Receipt.payment_id == payment.payment_id)
        ).scalar_one_or_none()
        if receipt and receipt.status.value == ReceiptStatus.VALID.value:
            ReceiptService.void_receipt(db, receipt, actor_user_id, reason=reason, request=request)

        SalesOrderEventService.record_event(
            db, payment.order_id, OrderEventType.PAYMENT_REVERSED.value,
            actor_user_id=actor_user_id,
            description=f"Payment {payment.payment_reference} reversed",
            metadata={"payment_id": payment.payment_id, "reason": reason},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="payment.reversed",
            resource_type="order_payments",
            resource_id=payment.payment_id,
            description=f"Payment {payment.payment_reference} reversed for order {order.order_number}",
            request=request,
        )

        db.commit()
        db.refresh(payment)
        return payment


# ---------------------------------------------------------------------------
# Receipt Service
# ---------------------------------------------------------------------------

class ReceiptService:
    @staticmethod
    def generate_receipt(db, payment, actor_user_id: int, request=None) -> Receipt:
        """Generate a receipt after payment confirmation."""
        receipt_number, _ = ReceiptNumberService.generate_receipt_number(db)
        verification_token = secrets.token_urlsafe(48)

        # Resolve template
        template = db.execute(
            sa.select(ReceiptTemplate).where(
                ReceiptTemplate.is_default == sa.true(),
                ReceiptTemplate.status == ReceiptTemplateStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()

        template_id = None
        template_version_id = None
        if template:
            template_id = template.template_id
            tv = db.execute(
                sa.select(ReceiptTemplateVersion)
                .where(
                    ReceiptTemplateVersion.template_id == template.template_id,
                    ReceiptTemplateVersion.version == template.current_version,
                )
            ).scalar_one_or_none()
            if tv:
                template_version_id = tv.template_version_id

        # Snapshot company profile
        company_profile_snapshot = None
        if payment:
            order = db.get(SalesOrder, payment.order_id)
            if order and order.company_profile_id:
                from quotes.models import CompanyProfile
                profile = db.get(CompanyProfile, order.company_profile_id)
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
                        "bank_name": profile.bank_name,
                        "bank_account_number": profile.bank_account_number,
                        "bank_branch": profile.bank_branch,
                    }

        receipt = Receipt(
            receipt_number=receipt_number,
            payment_id=payment.payment_id,
            order_id=payment.order_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            currency=payment.currency,
            status=ReceiptStatus.VALID.value,
            verification_token=verification_token,
            template_id=template_id,
            template_version_id=template_version_id,
            company_profile_snapshot=company_profile_snapshot,
            issued_at=_now(),
        )
        db.add(receipt)
        db.flush()

        SalesOrderEventService.record_event(
            db, payment.order_id, OrderEventType.RECEIPT_ISSUED.value,
            actor_user_id=actor_user_id,
            description=f"Receipt {receipt_number} issued",
            metadata={"receipt_id": receipt.receipt_id, "receipt_number": receipt_number},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="receipt.issued",
            resource_type="receipts",
            resource_id=receipt.receipt_id,
            description=f"Receipt {receipt_number} issued",
            metadata={"receipt_number": receipt_number},
            request=request,
        )

        return receipt

    @staticmethod
    def void_receipt(db, receipt, actor_user_id: int, reason: str = None, request=None):
        """Void a receipt."""
        if receipt.status.value != ReceiptStatus.VALID.value:
            raise ValidationError_(f"Receipt is not in VALID status. Current: {receipt.status.value}.")

        receipt.status = ReceiptStatus.VOIDED
        receipt.voided_at = _now()
        receipt.voided_by = actor_user_id
        receipt.void_reason = reason
        db.flush()

        SalesOrderEventService.record_event(
            db, receipt.order_id, OrderEventType.RECEIPT_VOIDED.value,
            actor_user_id=actor_user_id,
            description=f"Receipt {receipt.receipt_number} voided",
            metadata={"receipt_id": receipt.receipt_id, "reason": reason},
        )

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="receipt.voided",
            resource_type="receipts",
            resource_id=receipt.receipt_id,
            description=f"Receipt {receipt.receipt_number} voided",
            request=request,
        )

        db.flush()


# ---------------------------------------------------------------------------
# Receipt Verification Service
# ---------------------------------------------------------------------------

class ReceiptVerificationService:
    @staticmethod
    def verify(db, token: str, ip_address: str = None, user_agent: str = None) -> dict:
        """Verify a receipt by its verification token."""
        receipt = db.execute(
            sa.select(Receipt).where(Receipt.verification_token == token)
        ).scalar_one_or_none()

        if receipt is None:
            # Log attempt
            result = "INVALID"
            verification_log = ReceiptVerification(
                receipt_id=0,
                verification_token=token,
                ip_address=ip_address,
                user_agent=user_agent,
                result=result,
            )
            db.add(verification_log)
            db.flush()

            return {
                "valid": False,
                "reason": "not_found",
                "message": "Receipt not found.",
            }

        # Log verification
        result = receipt.status.value if receipt.status.value == "VALID" else receipt.status.value
        verification_log = ReceiptVerification(
            receipt_id=receipt.receipt_id,
            verification_token=token,
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
        )
        db.add(verification_log)
        db.flush()

        if receipt.status.value != ReceiptStatus.VALID.value:
            return {
                "valid": False,
                "reason": receipt.status.value.lower(),
                "message": f"Receipt is {receipt.status.value.lower()}.",
                "receipt_number": receipt.receipt_number,
            }

        order = db.get(SalesOrder, receipt.order_id)
        customer = db.get(Customer, receipt.customer_id)

        return {
            "valid": True,
            "receipt_number": receipt.receipt_number,
            "status": receipt.status.value,
            "amount": str(receipt.amount),
            "currency": receipt.currency,
            "order_number": order.order_number if order else None,
            "date": receipt.issued_at.isoformat() if receipt.issued_at else None,
            "issuer": "CRM V2",
        }


# ---------------------------------------------------------------------------
# Portal Service
# ---------------------------------------------------------------------------

class SalesOrderPortalService:
    @staticmethod
    def publish_to_portal(db, order_id: int, customer_account_id: int, actor_user_id: int):
        """Publish a sales order to the client portal."""
        existing = db.execute(
            sa.select(SalesOrderPortalAccess).where(
                SalesOrderPortalAccess.order_id == order_id,
                SalesOrderPortalAccess.customer_account_id == customer_account_id,
            )
        ).scalar_one_or_none()

        if existing:
            existing.visibility = "VISIBLE"
            existing.published_at = _now()
            existing.revoked_at = None
        else:
            access = SalesOrderPortalAccess(
                order_id=order_id,
                customer_account_id=customer_account_id,
                visibility="VISIBLE",
                published_at=_now(),
            )
            db.add(access)

        db.flush()

        SalesOrderEventService.record_event(
            db, order_id, OrderEventType.PORTAL_PUBLISHED.value,
            actor_user_id=actor_user_id,
            description="Order published to client portal",
            metadata={"customer_account_id": customer_account_id},
        )
