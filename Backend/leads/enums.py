from enum import Enum


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    UNQUALIFIED = "UNQUALIFIED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"
    DISQUALIFIED = "DISQUALIFIED"


class LeadFollowUpType(str, Enum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    MEETING = "MEETING"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    OTHER = "OTHER"


class LeadConsentType(str, Enum):
    MARKETING = "MARKETING"
    DATA_PROCESSING = "DATA_PROCESSING"
    THIRD_PARTY_SHARING = "THIRD_PARTY_SHARING"
    OTHER = "OTHER"


ALLOWED_LEAD_TRANSITIONS = {
    LeadStatus.NEW.value: {
        LeadStatus.CONTACTED.value,
        LeadStatus.UNQUALIFIED.value,
        LeadStatus.LOST.value,
        LeadStatus.DISQUALIFIED.value,
    },
    LeadStatus.CONTACTED.value: {
        LeadStatus.QUALIFIED.value,
        LeadStatus.UNQUALIFIED.value,
        LeadStatus.LOST.value,
        LeadStatus.DISQUALIFIED.value,
    },
    LeadStatus.QUALIFIED.value: {
        LeadStatus.CONVERTED.value,
        LeadStatus.LOST.value,
        LeadStatus.DISQUALIFIED.value,
    },
    LeadStatus.UNQUALIFIED.value: set(),
    LeadStatus.CONVERTED.value: set(),
    LeadStatus.LOST.value: set(),
    LeadStatus.DISQUALIFIED.value: set(),
}

TERMINAL_LEAD_STATUSES = {
    LeadStatus.UNQUALIFIED.value,
    LeadStatus.CONVERTED.value,
    LeadStatus.LOST.value,
    LeadStatus.DISQUALIFIED.value,
}
