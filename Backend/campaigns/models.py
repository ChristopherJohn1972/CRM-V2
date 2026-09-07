import sqlalchemy as sa
from sqlalchemy import JSON

from common.db import Base
from campaigns.enums import (
    AudienceType,
    AssetType,
    BudgetPeriod,
    CampaignCodeType,
    CampaignObjective,
    CampaignScheduleAction,
    CampaignSourceType,
    CampaignStatus,
    CampaignType,
    Channel,
    ConceptStrategy,
    CreativeSource,
    CreativeStatus,
    DiscountType,
    GenerationJobStatus,
    GenerationJobType,
    OfferType,
    RecommendationAction,
)


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text)
    status = sa.Column(sa.Enum(CampaignStatus), nullable=False, server_default=CampaignStatus.DRAFT.value)
    campaign_type = sa.Column(sa.Enum(CampaignType), nullable=False, server_default=CampaignType.CUSTOM.value)
    objective = sa.Column(sa.Enum(CampaignObjective))
    start_date = sa.Column(sa.Date)
    end_date = sa.Column(sa.Date)
    budget = sa.Column(sa.Numeric(18, 2))
    owner_user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    target_products = sa.Column(JSON)
    metadata_ = sa.Column("metadata", JSON)
    created_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    deleted_at = sa.Column(sa.DateTime)
    deleted_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class CampaignProduct(Base):
    __tablename__ = "campaign_products"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    product_reference = sa.Column(JSON, nullable=False)
    discount_type = sa.Column(sa.Enum(DiscountType))
    discount_value = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))


class CampaignCode(Base):
    __tablename__ = "campaign_codes"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    code = sa.Column(sa.String(100), nullable=False, unique=True)
    type = sa.Column(sa.Enum(CampaignCodeType), nullable=False, server_default=CampaignCodeType.CUSTOM.value)
    max_uses = sa.Column(sa.Integer)
    use_count = sa.Column(sa.Integer, nullable=False, server_default=sa.text("0"))
    expires_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CampaignSource(Base):
    __tablename__ = "campaign_sources"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    source_type = sa.Column(sa.Enum(CampaignSourceType), nullable=False, server_default=CampaignSourceType.CUSTOM.value)
    source_identifier = sa.Column(sa.String(255))
    tracking_url = sa.Column(sa.String(2000))
    click_count = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))


class CampaignShortUrl(Base):
    __tablename__ = "campaign_short_urls"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    short_code = sa.Column(sa.String(50), nullable=False, unique=True)
    destination_url = sa.Column(sa.String(2000), nullable=False)
    click_count = sa.Column(sa.BigInteger, nullable=False, server_default=sa.text("0"))


class CampaignQrCode(Base):
    __tablename__ = "campaign_qr_codes"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    qr_data = sa.Column(sa.Text, nullable=False)
    image_url = sa.Column(sa.String(2000))
    short_url_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaign_short_urls.id", ondelete="SET NULL"))


class CampaignStateHistory(Base):
    __tablename__ = "campaign_state_history"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    old_status = sa.Column(sa.Enum(CampaignStatus))
    new_status = sa.Column(sa.Enum(CampaignStatus), nullable=False)
    changed_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    changed_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    reason = sa.Column(sa.Text)


class CampaignSchedule(Base):
    __tablename__ = "campaign_schedules"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    action = sa.Column(sa.Enum(CampaignScheduleAction), nullable=False)
    scheduled_at = sa.Column(sa.DateTime, nullable=False)
    executed_at = sa.Column(sa.DateTime)
    executed_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))


class CampaignAudience(Base):
    __tablename__ = "campaign_audiences"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    audience_type = sa.Column(sa.Enum(AudienceType), nullable=False, server_default=AudienceType.BROAD.value)
    configuration = sa.Column(JSON)
    description = sa.Column(sa.Text)
    recommendation = sa.Column(sa.Text)
    recommendation_reason = sa.Column(sa.Text)
    confidence = sa.Column(sa.Numeric(5, 2))
    user_action = sa.Column(sa.Enum(RecommendationAction))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CampaignOffer(Base):
    __tablename__ = "campaign_offers"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    offer_type = sa.Column(sa.Enum(OfferType), nullable=False, server_default=OfferType.NONE.value)
    value = sa.Column(sa.Numeric(18, 2))
    description = sa.Column(sa.Text)
    start_at = sa.Column(sa.DateTime)
    end_at = sa.Column(sa.DateTime)
    recommendation = sa.Column(sa.Text)
    recommendation_reason = sa.Column(sa.Text)
    confidence = sa.Column(sa.Numeric(5, 2))
    user_action = sa.Column(sa.Enum(RecommendationAction))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CampaignChannel(Base):
    __tablename__ = "campaign_channels"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    channel = sa.Column(sa.Enum(Channel), nullable=False)
    configuration = sa.Column(JSON)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CampaignBudget(Base):
    __tablename__ = "campaign_budgets"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    amount = sa.Column(sa.Numeric(18, 2), nullable=False, server_default=sa.text("0.00"))
    currency = sa.Column(sa.String(3), nullable=False, server_default="KES")
    period = sa.Column(sa.Enum(BudgetPeriod), nullable=False, server_default=BudgetPeriod.CAMPAIGN.value)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CreativeConcept(Base):
    __tablename__ = "creative_concepts"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    strategy = sa.Column(sa.Enum(ConceptStrategy), nullable=False)
    description = sa.Column(sa.Text)
    recommendation_reason = sa.Column(sa.Text)
    is_selected = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class Creative(Base):
    __tablename__ = "creatives"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    concept_id = sa.Column(sa.BigInteger, sa.ForeignKey("creative_concepts.id", ondelete="SET NULL"))
    version = sa.Column(sa.Integer, nullable=False, server_default=sa.text("1"))
    status = sa.Column(sa.Enum(CreativeStatus), nullable=False, server_default=CreativeStatus.DRAFT.value)
    headline = sa.Column(JSON)
    subheadline = sa.Column(JSON)
    cta = sa.Column(JSON)
    visual_direction = sa.Column(sa.Text)
    image_url = sa.Column(sa.String(2000))
    source = sa.Column(sa.Enum(CreativeSource), nullable=False, server_default=CreativeSource.AI.value)
    is_selected = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    ai_model = sa.Column(sa.String(100))
    generation_version = sa.Column(sa.Integer)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    updated_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CreativeAsset(Base):
    __tablename__ = "creative_assets"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    creative_id = sa.Column(sa.BigInteger, sa.ForeignKey("creatives.id", ondelete="CASCADE"), nullable=False)
    asset_type = sa.Column(sa.Enum(AssetType), nullable=False)
    storage_key = sa.Column(sa.String(500), nullable=False)
    thumbnail_key = sa.Column(sa.String(500))
    mime_type = sa.Column(sa.String(100))
    width = sa.Column(sa.Integer)
    height = sa.Column(sa.Integer)
    aspect_ratio = sa.Column(sa.String(20))
    channel = sa.Column(sa.String(50))
    generation_job_id = sa.Column(sa.BigInteger)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class AIGenerationJob(Base):
    __tablename__ = "ai_generation_jobs"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    creative_id = sa.Column(sa.BigInteger, sa.ForeignKey("creatives.id", ondelete="SET NULL"))
    job_type = sa.Column(sa.Enum(GenerationJobType), nullable=False)
    model = sa.Column(sa.String(100))
    status = sa.Column(sa.Enum(GenerationJobStatus), nullable=False, server_default=GenerationJobStatus.PENDING.value)
    request_payload = sa.Column(JSON)
    response_payload = sa.Column(JSON)
    error_message = sa.Column(sa.Text)
    token_count = sa.Column(sa.Integer)
    cost = sa.Column(sa.Numeric(10, 4))
    idempotency_key = sa.Column(sa.String(255))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
    completed_at = sa.Column(sa.DateTime)


class CampaignLaunch(Base):
    __tablename__ = "campaign_launches"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    idempotency_key = sa.Column(sa.String(255), nullable=False, unique=True)
    status = sa.Column(sa.String(20), nullable=False, server_default="PENDING")
    validation_result = sa.Column(JSON)
    channel_results = sa.Column(JSON)
    error_message = sa.Column(sa.Text)
    launched_by = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    launched_at = sa.Column(sa.DateTime)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())


class CampaignAnalyticsEvent(Base):
    __tablename__ = "campaign_analytics_events"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    campaign_id = sa.Column(sa.BigInteger, sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"), nullable=False)
    event_type = sa.Column(sa.String(100), nullable=False)
    event_data = sa.Column(JSON)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=sa.func.now())
