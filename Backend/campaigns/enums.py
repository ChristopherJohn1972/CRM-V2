from enum import Enum


# ---------------------------------------------------------------------------
# Campaign Lifecycle
# ---------------------------------------------------------------------------

class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    PRODUCT_SELECTED = "PRODUCT_SELECTED"
    CONFIGURING = "CONFIGURING"
    CREATIVE_GENERATING = "CREATIVE_GENERATING"
    CREATIVE_READY = "CREATIVE_READY"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    APPROVED = "APPROVED"
    LAUNCHING = "LAUNCHING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ABANDONED = "ABANDONED"
    GENERATION_FAILED = "GENERATION_FAILED"


class CampaignType(str, Enum):
    PROMOTIONAL = "PROMOTIONAL"
    SEASONAL = "SEASONAL"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    REFERRAL_BOOST = "REFERRAL_BOOST"
    LOYALTY = "LOYALTY"
    CUSTOM = "CUSTOM"


class CampaignObjective(str, Enum):
    AWARENESS = "AWARENESS"
    CONVERSION = "CONVERSION"
    LEAD_GENERATION = "LEAD_GENERATION"
    ENGAGEMENT = "ENGAGEMENT"
    RETENTION = "RETENTION"
    CUSTOM = "CUSTOM"


# ---------------------------------------------------------------------------
# Campaign Configuration
# ---------------------------------------------------------------------------

class AudienceType(str, Enum):
    BROAD = "BROAD"
    DEMOGRAPHIC = "DEMOGRAPHIC"
    INTEREST = "INTEREST"
    BEHAVIORAL = "BEHAVIORAL"
    LOOKALIKE = "LOOKALIKE"
    CUSTOM = "CUSTOM"


class OfferType(str, Enum):
    PERCENTAGE_DISCOUNT = "PERCENTAGE_DISCOUNT"
    FIXED_DISCOUNT = "FIXED_DISCOUNT"
    BUY_X_GET_Y = "BUY_X_GET_Y"
    FREE_SHIPPING = "FREE_SHIPPING"
    BUNDLE = "BUNDLE"
    NONE = "NONE"


class Channel(str, Enum):
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    TWITTER = "TWITTER"
    LINKEDIN = "LINKEDIN"
    TIKTOK = "TIKTOK"
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBSITE = "WEBSITE"
    GOOGLE_ADS = "GOOGLE_ADS"
    YOUTUBE = "YOUTUBE"
    CUSTOM = "CUSTOM"


class BudgetPeriod(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    LIFETIME = "LIFETIME"
    CAMPAIGN = "CAMPAIGN"


# ---------------------------------------------------------------------------
# Creative
# ---------------------------------------------------------------------------

class ConceptStrategy(str, Enum):
    PRODUCT_FOCUSED = "PRODUCT_FOCUSED"
    OFFER_FOCUSED = "OFFER_FOCUSED"
    LIFESTYLE = "LIFESTYLE"
    SOCIAL_PROOF = "SOCIAL_PROOF"
    URGENCY = "URGENCY"
    EDUCATIONAL = "EDUCATIONAL"
    CUSTOM = "CUSTOM"


class CreativeStatus(str, Enum):
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    READY = "READY"
    STALE = "STALE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class CreativeSource(str, Enum):
    AI = "AI"
    USER = "USER"
    HYBRID = "HYBRID"


class AssetType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    LOGO = "LOGO"
    PRODUCT_IMAGE = "PRODUCT_IMAGE"
    BACKGROUND = "BACKGROUND"
    BANNER = "BANNER"
    BILLBOARD = "BILLBOARD"
    SOCIAL_POST = "SOCIAL_POST"
    STORY = "STORY"
    REEL = "REEL"


# ---------------------------------------------------------------------------
# AI Generation
# ---------------------------------------------------------------------------

class GenerationJobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class GenerationJobType(str, Enum):
    CONCEPT = "CONCEPT"
    HEADLINE = "HEADLINE"
    IMAGE = "IMAGE"
    FULL_CREATIVE = "FULL_CREATIVE"


# ---------------------------------------------------------------------------
# User Action Tracking
# ---------------------------------------------------------------------------

class RecommendationAction(str, Enum):
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"
    IGNORED = "IGNORED"


# ---------------------------------------------------------------------------
# Discount (for campaign products)
# ---------------------------------------------------------------------------

class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


# ---------------------------------------------------------------------------
# Existing enums (preserved)
# ---------------------------------------------------------------------------

class CampaignCodeType(str, Enum):
    COUPON = "COUPON"
    PROMO = "PROMO"
    AFFILIATE = "AFFILIATE"
    CUSTOM = "CUSTOM"


class CampaignSourceType(str, Enum):
    WEBSITE = "WEBSITE"
    SOCIAL = "SOCIAL"
    EMAIL = "EMAIL"
    SMS = "SMS"
    REFERRAL = "REFERRAL"
    DIRECT = "DIRECT"
    PARTNER = "PARTNER"
    CUSTOM = "CUSTOM"


class CampaignScheduleAction(str, Enum):
    ACTIVATE = "ACTIVATE"
    PAUSE = "PAUSE"
    COMPLETE = "COMPLETE"
    CANCEL = "CANCEL"


# ---------------------------------------------------------------------------
# State Transitions
# ---------------------------------------------------------------------------

ALLOWED_CAMPAIGN_TRANSITIONS = {
    CampaignStatus.DRAFT.value: {
        CampaignStatus.PRODUCT_SELECTED.value,
        CampaignStatus.CANCELLED.value,
        CampaignStatus.ABANDONED.value,
    },
    CampaignStatus.PRODUCT_SELECTED.value: {
        CampaignStatus.CONFIGURING.value,
        CampaignStatus.CREATIVE_GENERATING.value,
        CampaignStatus.CANCELLED.value,
        CampaignStatus.ABANDONED.value,
    },
    CampaignStatus.CONFIGURING.value: {
        CampaignStatus.CREATIVE_GENERATING.value,
        CampaignStatus.READY_FOR_REVIEW.value,
        CampaignStatus.CANCELLED.value,
        CampaignStatus.ABANDONED.value,
    },
    CampaignStatus.CREATIVE_GENERATING.value: {
        CampaignStatus.CREATIVE_READY.value,
        CampaignStatus.GENERATION_FAILED.value,
        CampaignStatus.CANCELLED.value,
    },
    CampaignStatus.CREATIVE_READY.value: {
        CampaignStatus.READY_FOR_REVIEW.value,
        CampaignStatus.CREATIVE_GENERATING.value,
        CampaignStatus.CANCELLED.value,
    },
    CampaignStatus.READY_FOR_REVIEW.value: {
        CampaignStatus.APPROVED.value,
        CampaignStatus.CHANGES_REQUIRED.value,
        CampaignStatus.CANCELLED.value,
    },
    CampaignStatus.CHANGES_REQUIRED.value: {
        CampaignStatus.CONFIGURING.value,
        CampaignStatus.CREATIVE_GENERATING.value,
        CampaignStatus.CANCELLED.value,
    },
    CampaignStatus.APPROVED.value: {
        CampaignStatus.LAUNCHING.value,
        CampaignStatus.CHANGES_REQUIRED.value,
        CampaignStatus.CANCELLED.value,
    },
    CampaignStatus.LAUNCHING.value: {
        CampaignStatus.ACTIVE.value,
        CampaignStatus.GENERATION_FAILED.value,
    },
    CampaignStatus.ACTIVE.value: {
        CampaignStatus.PAUSED.value,
        CampaignStatus.COMPLETED.value,
    },
    CampaignStatus.PAUSED.value: {
        CampaignStatus.ACTIVE.value,
        CampaignStatus.COMPLETED.value,
        CampaignStatus.CANCELLED.value,
    },
    CampaignStatus.GENERATION_FAILED.value: {
        CampaignStatus.CREATIVE_GENERATING.value,
        CampaignStatus.CONFIGURING.value,
        CampaignStatus.CANCELLED.value,
    },
    CampaignStatus.COMPLETED.value: set(),
    CampaignStatus.CANCELLED.value: set(),
    CampaignStatus.ABANDONED.value: set(),
}

TERMINAL_CAMPAIGN_STATUSES = {
    CampaignStatus.COMPLETED.value,
    CampaignStatus.CANCELLED.value,
    CampaignStatus.ABANDONED.value,
}
