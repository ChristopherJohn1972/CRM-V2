from enum import Enum


class QuoteType(str, Enum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    PROJECT = "PROJECT"


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SENT = "SENT"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class QuoteItemType(str, Enum):
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    CUSTOM = "CUSTOM"


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class QuoteTemplateStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class QuoteEventType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    ITEM_ADDED = "ITEM_ADDED"
    ITEM_REMOVED = "ITEM_REMOVED"
    ITEM_UPDATED = "ITEM_UPDATED"
    PRICE_OVERRIDDEN = "PRICE_OVERRIDDEN"
    DISCOUNT_APPLIED = "DISCOUNT_APPLIED"
    TEMPLATE_SELECTED = "TEMPLATE_SELECTED"
    SUBMITTED_FOR_APPROVAL = "SUBMITTED_FOR_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT = "SENT"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CHANGE_REQUESTED = "CHANGE_REQUESTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    DUPLICATED = "DUPLICATED"
    DOCUMENT_GENERATED = "DOCUMENT_GENERATED"
    PORTAL_PUBLISHED = "PORTAL_PUBLISHED"
    CONVERTED_TO_ORDER = "CONVERTED_TO_ORDER"


class ClientResponseDecision(str, Enum):
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"
    CHANGE_REQUESTED = "CHANGE_REQUESTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


ALLOWED_QUOTE_TRANSITIONS = {
    QuoteStatus.DRAFT.value: {
        QuoteStatus.PENDING_APPROVAL.value,
        QuoteStatus.APPROVED.value,
        QuoteStatus.CANCELLED.value,
    },
    QuoteStatus.PENDING_APPROVAL.value: {
        QuoteStatus.APPROVED.value,
        QuoteStatus.REJECTED.value,
        QuoteStatus.DRAFT.value,
    },
    QuoteStatus.APPROVED.value: {
        QuoteStatus.SENT.value,
        QuoteStatus.CANCELLED.value,
        QuoteStatus.DRAFT.value,
    },
    QuoteStatus.SENT.value: {
        QuoteStatus.VIEWED.value,
        QuoteStatus.ACCEPTED.value,
        QuoteStatus.REJECTED.value,
        QuoteStatus.EXPIRED.value,
    },
    QuoteStatus.VIEWED.value: {
        QuoteStatus.ACCEPTED.value,
        QuoteStatus.REJECTED.value,
        QuoteStatus.EXPIRED.value,
    },
    QuoteStatus.ACCEPTED.value: set(),
    QuoteStatus.REJECTED.value: set(),
    QuoteStatus.EXPIRED.value: set(),
    QuoteStatus.CANCELLED.value: set(),
}


TERMINAL_STATUSES = {
    QuoteStatus.ACCEPTED.value,
    QuoteStatus.REJECTED.value,
    QuoteStatus.EXPIRED.value,
    QuoteStatus.CANCELLED.value,
}
