from decimal import Decimal
from rest_framework import serializers

from common.fields import EnumValueField


class CampaignWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.ChoiceField(
        choices=["DRAFT", "SCHEDULED", "ACTIVE", "PAUSED", "COMPLETED", "CANCELLED"],
        required=False, allow_null=True, default="DRAFT",
    )
    campaign_type = serializers.ChoiceField(
        choices=["PROMOTIONAL", "SEASONAL", "PRODUCT_LAUNCH", "REFERRAL_BOOST", "LOYALTY", "CUSTOM"],
        required=False, allow_null=True, default="CUSTOM",
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    budget = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True)
    owner_user_id = serializers.IntegerField(required=False, allow_null=True)
    target_products = serializers.JSONField(required=False, allow_null=True)


class CampaignUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    campaign_type = serializers.ChoiceField(
        choices=["PROMOTIONAL", "SEASONAL", "PRODUCT_LAUNCH", "REFERRAL_BOOST", "LOYALTY", "CUSTOM"],
        required=False, allow_null=True,
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    budget = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True)
    owner_user_id = serializers.IntegerField(required=False, allow_null=True)
    target_products = serializers.JSONField(required=False, allow_null=True)


class CampaignReadSerializer(serializers.Serializer):
    campaign_id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    status = EnumValueField()
    campaign_type = EnumValueField()
    start_date = serializers.DateField(allow_null=True, required=False)
    end_date = serializers.DateField(allow_null=True, required=False)
    budget = serializers.DecimalField(max_digits=18, decimal_places=2, allow_null=True, required=False)
    owner_user_id = serializers.IntegerField(allow_null=True, required=False)
    target_products = serializers.JSONField(allow_null=True, required=False)
    created_by = serializers.IntegerField(allow_null=True, required=False)
    updated_by = serializers.IntegerField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CampaignTransitionSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(
        choices=["DRAFT", "SCHEDULED", "ACTIVE", "PAUSED", "COMPLETED", "CANCELLED"]
    )
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CampaignCodeWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    type = serializers.ChoiceField(
        choices=["COUPON", "PROMO", "AFFILIATE", "CUSTOM"],
        required=False, allow_null=True, default="CUSTOM",
    )
    max_uses = serializers.IntegerField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class CampaignCodeReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    code = serializers.CharField()
    type = EnumValueField()
    max_uses = serializers.IntegerField(allow_null=True, required=False)
    use_count = serializers.IntegerField()
    expires_at = serializers.DateTimeField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class CampaignSourceWriteSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(
        choices=["WEBSITE", "SOCIAL", "EMAIL", "SMS", "REFERRAL", "DIRECT", "PARTNER", "CUSTOM"]
    )
    source_identifier = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    tracking_url = serializers.CharField(max_length=2000, required=False, allow_blank=True, allow_null=True)


class CampaignSourceReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    source_type = EnumValueField()
    source_identifier = serializers.CharField(allow_null=True, required=False)
    tracking_url = serializers.CharField(allow_null=True, required=False)
    click_count = serializers.IntegerField()


class CampaignScheduleWriteSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["ACTIVATE", "PAUSE", "COMPLETE", "CANCEL"])
    scheduled_at = serializers.DateTimeField()


# ============================================================================
# AI Campaign Builder Serializers
# ============================================================================

class CampaignProductWriteSerializer(serializers.Serializer):
    product_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
    discount_type = serializers.CharField(required=False, allow_null=True)
    discount_value = serializers.FloatField(required=False, allow_null=True)


class CampaignProductReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    product_reference = serializers.JSONField()
    discount_type = serializers.CharField(allow_null=True, required=False)
    discount_value = serializers.FloatField(allow_null=True, required=False)


class CampaignAudienceWriteSerializer(serializers.Serializer):
    audience_type = serializers.CharField(required=True)
    configuration = serializers.JSONField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)


class CampaignAudienceReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    audience_type = serializers.CharField()
    configuration = serializers.JSONField(allow_null=True, required=False)
    description = serializers.CharField(allow_null=True, required=False)
    recommendation = serializers.CharField(allow_null=True, required=False)
    recommendation_reason = serializers.CharField(allow_null=True, required=False)
    confidence = serializers.FloatField(allow_null=True, required=False)
    user_action = serializers.CharField(allow_null=True, required=False)


class CampaignOfferWriteSerializer(serializers.Serializer):
    offer_type = serializers.CharField(required=True)
    value = serializers.FloatField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)


class CampaignOfferReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    offer_type = serializers.CharField()
    value = serializers.FloatField(allow_null=True, required=False)
    description = serializers.CharField(allow_null=True, required=False)
    start_at = serializers.DateTimeField(allow_null=True, required=False)
    end_at = serializers.DateTimeField(allow_null=True, required=False)
    recommendation = serializers.CharField(allow_null=True, required=False)
    recommendation_reason = serializers.CharField(allow_null=True, required=False)
    confidence = serializers.FloatField(allow_null=True, required=False)
    user_action = serializers.CharField(allow_null=True, required=False)


class CampaignChannelWriteSerializer(serializers.Serializer):
    channel = serializers.CharField(required=True)
    configuration = serializers.JSONField(required=False, allow_null=True)


class CampaignChannelReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    channel = serializers.CharField()
    configuration = serializers.JSONField(allow_null=True, required=False)


class CampaignBudgetWriteSerializer(serializers.Serializer):
    amount = serializers.FloatField(required=True)
    currency = serializers.CharField(required=False, default="KES")
    period = serializers.CharField(required=False, default="CAMPAIGN")


class CampaignBudgetReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    amount = serializers.FloatField()
    currency = serializers.CharField()
    period = serializers.CharField()


class CreativeConceptReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    strategy = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    recommendation_reason = serializers.CharField(allow_null=True, required=False)
    is_selected = serializers.BooleanField()


class CreativeFieldSerializer(serializers.Serializer):
    value = serializers.CharField()
    source = serializers.CharField()


class CreativeReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    concept_id = serializers.IntegerField(allow_null=True, required=False)
    version = serializers.IntegerField()
    status = EnumValueField()
    headline = serializers.JSONField(allow_null=True, required=False)
    subheadline = serializers.JSONField(allow_null=True, required=False)
    cta = serializers.JSONField(allow_null=True, required=False)
    visual_direction = serializers.CharField(allow_null=True, required=False)
    source = serializers.CharField()
    is_selected = serializers.BooleanField()
    ai_model = serializers.CharField(allow_null=True, required=False)
    generation_version = serializers.IntegerField(allow_null=True, required=False)


class CreativeWriteSerializer(serializers.Serializer):
    headline = serializers.CharField(required=False, allow_null=True)
    subheadline = serializers.CharField(required=False, allow_null=True)
    cta = serializers.CharField(required=False, allow_null=True)
    visual_direction = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField(required=False, allow_null=True)


class CreativeAssetReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    creative_id = serializers.IntegerField()
    asset_type = serializers.CharField()
    storage_key = serializers.CharField()
    thumbnail_key = serializers.CharField(allow_null=True, required=False)
    mime_type = serializers.CharField(allow_null=True, required=False)
    width = serializers.IntegerField(allow_null=True, required=False)
    height = serializers.IntegerField(allow_null=True, required=False)
    aspect_ratio = serializers.CharField(allow_null=True, required=False)
    channel = serializers.CharField(allow_null=True, required=False)


class AIGenerationJobReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    creative_id = serializers.IntegerField(allow_null=True, required=False)
    job_type = serializers.CharField()
    model = serializers.CharField(allow_null=True, required=False)
    status = EnumValueField()
    error_message = serializers.CharField(allow_null=True, required=False)
    token_count = serializers.IntegerField(allow_null=True, required=False)
    cost = serializers.FloatField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True, required=False)


class CampaignReadinessSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    checks = serializers.ListField(child=serializers.DictField())


class CampaignProgressSerializer(serializers.Serializer):
    campaign_id = serializers.IntegerField()
    status = EnumValueField()
    progress = serializers.DictField()
    readiness = serializers.DictField()


class CampaignLaunchReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    status = serializers.CharField()
    validation_result = serializers.JSONField(allow_null=True, required=False)
    channel_results = serializers.JSONField(allow_null=True, required=False)
    error_message = serializers.CharField(allow_null=True, required=False)
    launched_at = serializers.DateTimeField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class AIGenerateRequestSerializer(serializers.Serializer):
    model = serializers.CharField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(required=False, allow_null=True)
