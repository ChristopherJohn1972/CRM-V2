from rest_framework import serializers

from common.fields import EnumValueField


class LeadWriteSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    company = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    source_campaign_id = serializers.IntegerField(required=False, allow_null=True)
    source_channel = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    assigned_user_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_team_id = serializers.IntegerField(required=False, allow_null=True)
    tags = serializers.JSONField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    consent_given = serializers.BooleanField(required=False, default=False)


class LeadUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    company = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    source_campaign_id = serializers.IntegerField(required=False, allow_null=True)
    source_channel = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    assigned_user_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_team_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=["NEW", "CONTACTED", "QUALIFIED", "UNQUALIFIED", "CONVERTED", "LOST"],
        required=False, allow_null=True,
    )
    tags = serializers.JSONField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class LeadReadSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    first_name = serializers.CharField(allow_null=True, required=False)
    last_name = serializers.CharField(allow_null=True, required=False)
    email = serializers.CharField(allow_null=True, required=False)
    phone = serializers.CharField(allow_null=True, required=False)
    company = serializers.CharField(allow_null=True, required=False)
    source_campaign_id = serializers.IntegerField(allow_null=True, required=False)
    source_channel = serializers.CharField(allow_null=True, required=False)
    status = EnumValueField()
    assigned_user_id = serializers.IntegerField(allow_null=True, required=False)
    assigned_team_id = serializers.IntegerField(allow_null=True, required=False)
    qualification_score = serializers.IntegerField(allow_null=True, required=False)
    tags = serializers.JSONField(allow_null=True, required=False)
    notes = serializers.CharField(allow_null=True, required=False)
    consent_given = serializers.BooleanField()
    consent_date = serializers.DateTimeField(allow_null=True, required=False)
    created_by = serializers.IntegerField(allow_null=True, required=False)
    updated_by = serializers.IntegerField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class LeadQualifySerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=0, max_value=100)
    criteria = serializers.JSONField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class LeadFollowUpWriteSerializer(serializers.Serializer):
    follow_up_type = serializers.ChoiceField(
        choices=["CALL", "EMAIL", "MEETING", "SMS", "WHATSAPP", "OTHER"]
    )
    scheduled_at = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    assigned_to = serializers.IntegerField(required=False, allow_null=True)


class LeadFollowUpReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    lead_id = serializers.IntegerField()
    follow_up_type = serializers.CharField()
    scheduled_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True, required=False)
    outcome = serializers.CharField(allow_null=True, required=False)
    notes = serializers.CharField(allow_null=True, required=False)
    assigned_to = serializers.IntegerField(allow_null=True, required=False)


class LeadConsentWriteSerializer(serializers.Serializer):
    consent_type = serializers.ChoiceField(
        choices=["MARKETING", "DATA_PROCESSING", "THIRD_PARTY_SHARING", "OTHER"]
    )
    granted = serializers.BooleanField()
    ip_address = serializers.CharField(max_length=45, required=False, allow_blank=True, allow_null=True)
    source = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
