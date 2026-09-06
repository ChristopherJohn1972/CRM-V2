from rest_framework import serializers


class AttributionEventWriteSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    source_id = serializers.IntegerField(required=False, allow_null=True)
    event_type = serializers.ChoiceField(
        choices=["IMPRESSION", "CLICK", "LEAD_CREATION", "CONVERSION", "PURCHASE"]
    )
    touch_point_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, allow_null=True)
    session_id = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)


class AttributionEventReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    source_id = serializers.IntegerField(allow_null=True, required=False)
    event_type = serializers.CharField()
    touch_point_at = serializers.DateTimeField()
    session_id = serializers.CharField(allow_null=True, required=False)


class AttributionResultReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    campaign_id = serializers.IntegerField()
    model_type = serializers.CharField()
    attributed_revenue = serializers.DecimalField(max_digits=18, decimal_places=2)
    attributed_weight = serializers.DecimalField(max_digits=5, decimal_places=4)
    computed_at = serializers.DateTimeField()
