from enum import Enum


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class OrderSource(str, Enum):
    QUOTE = "QUOTE"
    DIRECT = "DIRECT"


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    ON_HOLD = "ON_HOLD"


class OrderItemType(str, Enum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    CUSTOM = "CUSTOM"


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class AdjustmentType(str, Enum):
    SHIPPING = "SHIPPING"
    HANDLING = "HANDLING"
    SERVICE_FEE = "SERVICE_FEE"
    DISCOUNT = "DISCOUNT"
    SURCHARGE = "SURCHARGE"
    OTHER = "OTHER"


class PaymentMethod(str, Enum):
    MPESA = "MPESA"
    BANK_TRANSFER = "BANK_TRANSFER"
    CARD = "CARD"
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class PaymentOverallStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERPAID = "OVERPAID"


class ReceiptStatus(str, Enum):
    VALID = "VALID"
    VOIDED = "VOIDED"
    REVERSED = "REVERSED"


class ReceiptTemplateStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class OrderEventType(str, Enum):
    CREATED = "CREATED"
    EDITED = "EDITED"
    CONVERTED_FROM_QUOTE = "CONVERTED_FROM_QUOTE"
    ITEM_ADDED = "ITEM_ADDED"
    ITEM_REMOVED = "ITEM_REMOVED"
    ITEM_UPDATED = "ITEM_UPDATED"
    SUBMITTED_FOR_APPROVAL = "SUBMITTED_FOR_APPROVAL"
    APPROVED = "APPROVED"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    PAYMENT_RECORDED = "PAYMENT_RECORDED"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    PAYMENT_REVERSED = "PAYMENT_REVERSED"
    RECEIPT_ISSUED = "RECEIPT_ISSUED"
    RECEIPT_VOIDED = "RECEIPT_VOIDED"
    PORTAL_PUBLISHED = "PORTAL_PUBLISHED"
    STATUS_CHANGED = "STATUS_CHANGED"
    DOCUMENT_GENERATED = "DOCUMENT_GENERATED"


# ---------------------------------------------------------------------------
# Status transition maps
# ---------------------------------------------------------------------------

ALLOWED_ORDER_TRANSITIONS = {
    OrderStatus.DRAFT.value: {
        OrderStatus.CONFIRMED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.PENDING_APPROVAL.value: {
        OrderStatus.APPROVED.value,
        OrderStatus.CANCELLED.value,
        OrderStatus.DRAFT.value,
    },
    OrderStatus.APPROVED.value: {
        OrderStatus.CONFIRMED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.CONFIRMED.value: {
        OrderStatus.PROCESSING.value,
        OrderStatus.CANCELLED.value,
        OrderStatus.ON_HOLD.value,
    },
    OrderStatus.PROCESSING.value: {
        OrderStatus.FULFILLED.value,
        OrderStatus.CANCELLED.value,
        OrderStatus.ON_HOLD.value,
    },
    OrderStatus.FULFILLED.value: set(),
    OrderStatus.CANCELLED.value: set(),
    OrderStatus.ON_HOLD.value: {
        OrderStatus.CONFIRMED.value,
        OrderStatus.PROCESSING.value,
        OrderStatus.CANCELLED.value,
    },
}

TERMINAL_ORDER_STATUSES = {
    OrderStatus.FULFILLED.value,
    OrderStatus.CANCELLED.value,
}


# ---------------------------------------------------------------------------
# Payment status transitions
# ---------------------------------------------------------------------------

ALLOWED_PAYMENT_TRANSITIONS = {
    PaymentStatus.PENDING.value: {
        PaymentStatus.CONFIRMED.value,
        PaymentStatus.FAILED.value,
        PaymentStatus.REVERSED.value,
    },
    PaymentStatus.CONFIRMED.value: {
        PaymentStatus.REVERSED.value,
    },
    PaymentStatus.FAILED.value: set(),
    PaymentStatus.REVERSED.value: set(),
}


# ---------------------------------------------------------------------------
# Receipt status transitions
# ---------------------------------------------------------------------------

ALLOWED_RECEIPT_TRANSITIONS = {
    ReceiptStatus.VALID.value: {
        ReceiptStatus.VOIDED.value,
        ReceiptStatus.REVERSED.value,
    },
    ReceiptStatus.VOIDED.value: set(),
    ReceiptStatus.REVERSED.value: set(),
}
