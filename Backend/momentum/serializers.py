from rest_framework import serializers


class MomentumRuleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    code = serializers.CharField(max_length=100)
    trigger_type = serializers.ChoiceField(
        choices=["PURCHASE", "REFERRAL", "SIGNUP", "CAMPAIGN", "MANUAL", "CUSTOM"]
    )
    config = serializers.JSONField()
    is_active = serializers.BooleanField(required=False, default=True)
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField(required=False, allow_null=True)


class MomentumRuleReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    trigger_type = serializers.CharField()
    config = serializers.JSONField()
    is_active = serializers.BooleanField()
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class MomentumEntryReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    entry_type = serializers.CharField()
    points = serializers.IntegerField()
    balance_after = serializers.IntegerField()
    source_type = serializers.CharField()
    source_id = serializers.CharField(allow_null=True, required=False)
    rule_id = serializers.IntegerField(allow_null=True, required=False)
    description = serializers.CharField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class MomentumBalanceReadSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    balance = serializers.IntegerField()
