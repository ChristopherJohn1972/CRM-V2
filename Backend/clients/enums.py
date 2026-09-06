from enum import Enum


class CustomerType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"
    ORGANISATION = "ORGANISATION"


class CustomerStatus(str, Enum):
    PROSPECT = "PROSPECT"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class AccountNumberStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESERVED = "RESERVED"
    RETIRED = "RETIRED"


class AddressType(str, Enum):
    BILLING = "BILLING"
    SHIPPING = "SHIPPING"
    OFFICE = "OFFICE"
    HOME = "HOME"
    OTHER = "OTHER"


ALLOWED_STATUS_TRANSITIONS = {
    CustomerStatus.PROSPECT.value: {
        CustomerStatus.ONBOARDING.value,
        CustomerStatus.ACTIVE.value,
        CustomerStatus.INACTIVE.value,
        CustomerStatus.CLOSED.value,
    },
    CustomerStatus.ONBOARDING.value: {
        CustomerStatus.ACTIVE.value,
        CustomerStatus.PROSPECT.value,
    },
    CustomerStatus.ACTIVE.value: {
        CustomerStatus.INACTIVE.value,
        CustomerStatus.SUSPENDED.value,
        CustomerStatus.CLOSED.value,
    },
    CustomerStatus.INACTIVE.value: {
        CustomerStatus.ACTIVE.value,
        CustomerStatus.SUSPENDED.value,
        CustomerStatus.CLOSED.value,
    },
    CustomerStatus.SUSPENDED.value: {
        CustomerStatus.ACTIVE.value,
        CustomerStatus.INACTIVE.value,
        CustomerStatus.CLOSED.value,
    },
    CustomerStatus.CLOSED.value: set(),
    CustomerStatus.ARCHIVED.value: {CustomerStatus.INACTIVE.value},
}

TERMINAL_STATUSES = {CustomerStatus.CLOSED.value}
