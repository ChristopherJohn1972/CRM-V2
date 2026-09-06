from enum import Enum


class CustomerAccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class PortalUserStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"
    REVOKED = "REVOKED"


class PortalRelationshipType(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    FINANCE = "FINANCE"
    CONTACT = "CONTACT"
    VIEWER = "VIEWER"


class PortalPermissionEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


# Capability rank per relationship type: higher levels imply lower ones.
PORTAL_RELATIONSHIP_RANK = {
    PortalRelationshipType.VIEWER.value: 1,
    PortalRelationshipType.CONTACT.value: 2,
    PortalRelationshipType.FINANCE.value: 3,
    PortalRelationshipType.ADMIN.value: 4,
    PortalRelationshipType.OWNER.value: 5,
}


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InvoiceStatus(str, Enum):
    OUTSTANDING = "OUTSTANDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class ComplaintStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ComplaintPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class NotificationType(str, Enum):
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    RECEIPT_AVAILABLE = "RECEIPT_AVAILABLE"
    COMPLAINT_UPDATED = "COMPLAINT_UPDATED"
    COMPLAINT_RESOLVED = "COMPLAINT_RESOLVED"
    NEW_DOCUMENT = "NEW_DOCUMENT"
    ACCOUNT_NOTIFICATION = "ACCOUNT_NOTIFICATION"
    MOMENTUM_MILESTONE = "MOMENTUM_MILESTONE"
    REWARD_AVAILABLE = "REWARD_AVAILABLE"
    SECURITY_NOTIFICATION = "SECURITY_NOTIFICATION"


class RewardStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RedemptionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FULFILLED = "FULFILLED"