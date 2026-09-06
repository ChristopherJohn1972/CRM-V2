from enum import Enum


class AttributionEventType(str, Enum):
    IMPRESSION = "IMPRESSION"
    CLICK = "CLICK"
    LEAD_CREATION = "LEAD_CREATION"
    CONVERSION = "CONVERSION"
    PURCHASE = "PURCHASE"


class AttributionModelType(str, Enum):
    LAST_TOUCH = "LAST_TOUCH"
    FIRST_TOUCH = "FIRST_TOUCH"
    LINEAR = "LINEAR"
    POSITION_BASED = "POSITION_BASED"
    TIME_DECAY = "TIME_DECAY"
    CUSTOM = "CUSTOM"
