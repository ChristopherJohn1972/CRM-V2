from rest_framework import serializers

from common.fields import EnumValueField


class ReferralCodeWriteSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False)
    code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    campaign_id = serializers.IntegerField(required=False, allow_null=True)
    max_referrals = serializers.IntegerField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class ReferralCodeReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    referrer_customer_id = serializers.IntegerField()
    campaign_id = serializers.IntegerField(allow_null=True, required=False)
    status = EnumValueField()
    max_referrals = serializers.IntegerField(allow_null=True, required=False)
    referral_count = serializers.IntegerField()
    expires_at = serializers.DateTimeField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()


class ReferralEventReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    referral_code_id = serializers.IntegerField()
    referred_customer_id = serializers.IntegerField()
    event_type = serializers.CharField()
    occurred_at = serializers.DateTimeField()


class ReferralQualificationReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    referral_id = serializers.IntegerField()
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    qualified_at = serializers.DateTimeField()
    reward_issued = serializers.BooleanField()
    reward_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
