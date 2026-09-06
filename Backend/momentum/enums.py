from enum import Enum


class MomentumTriggerType(str, Enum):
    PURCHASE = "PURCHASE"
    REFERRAL = "REFERRAL"
    SIGNUP = "SIGNUP"
    CAMPAIGN = "CAMPAIGN"
    MANUAL = "MANUAL"
    CUSTOM = "CUSTOM"


class MomentumEntryType(str, Enum):
    EARN = "EARN"
    REDEEM = "REDEEM"
    EXPIRE = "EXPIRE"
    ADJUST = "ADJUST"
    FORFEIT = "FORFEIT"
