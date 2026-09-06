from enum import Enum


class ReferralCodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXHAUSTED = "EXHAUSTED"
    EXPIRED = "EXPIRED"


class ReferralEventType(str, Enum):
    CODE_GENERATED = "CODE_GENERATED"
    CODE_SHARED = "CODE_SHARED"
    CODE_CLICKED = "CODE_CLICKED"
    REGISTRATION = "REGISTRATION"
    FIRST_PURCHASE = "FIRST_PURCHASE"
    REWARD_ISSUED = "REWARD_ISSUED"


ALLOWED_REFERRAL_CODE_TRANSITIONS = {
    ReferralCodeStatus.ACTIVE.value: {
        ReferralCodeStatus.INACTIVE.value,
        ReferralCodeStatus.EXHAUSTED.value,
        ReferralCodeStatus.EXPIRED.value,
    },
    ReferralCodeStatus.INACTIVE.value: {
        ReferralCodeStatus.ACTIVE.value,
    },
    ReferralCodeStatus.EXHAUSTED.value: set(),
    ReferralCodeStatus.EXPIRED.value: set(),
}

TERMINAL_REFERRAL_STATUSES = {
    ReferralCodeStatus.EXHAUSTED.value,
    ReferralCodeStatus.EXPIRED.value,
}
