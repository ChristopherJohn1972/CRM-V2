from rest_framework import serializers

from common.fields import EnumValueField


class SmsSerializer(serializers.Serializer):
    sms_message_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    provider = serializers.CharField()
    provider_message_id = serializers.CharField()
    direction = serializers.CharField()
    from_number = serializers.CharField()
    to_number = serializers.CharField()
    body = serializers.CharField()
    status = serializers.CharField()
    failure_reason = serializers.CharField()
    attempts = serializers.IntegerField()
    provider_reference = serializers.CharField()
    sent_at = serializers.DateTimeField()
    delivered_at = serializers.DateTimeField()
    last_attempt_at = serializers.DateTimeField()
    created_by = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class SmsSendSerializer(serializers.Serializer):
    to_number = serializers.CharField(max_length=50)
    body = serializers.CharField()
    from_number = serializers.CharField(max_length=50, required=False, allow_blank=True)


class EmailSerializer(serializers.Serializer):
    email_message_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    provider = serializers.CharField()
    provider_message_id = serializers.CharField()
    message_id = serializers.CharField()
    direction = serializers.CharField()
    from_address = serializers.CharField()
    to_address = serializers.CharField()
    cc_address = serializers.CharField()
    bcc_address = serializers.CharField()
    subject = serializers.CharField()
    body = serializers.CharField()
    status = serializers.CharField()
    failure_reason = serializers.CharField()
    attempts = serializers.IntegerField()
    provider_reference = serializers.CharField()
    sent_at = serializers.DateTimeField()
    delivered_at = serializers.DateTimeField()
    last_attempt_at = serializers.DateTimeField()
    created_by = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class EmailSendSerializer(serializers.Serializer):
    to_address = serializers.EmailField()
    subject = serializers.CharField(max_length=500, required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True)
    cc_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    bcc_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    from_address = serializers.EmailField(required=False, allow_null=True)


class CallSerializer(serializers.Serializer):
    call_log_id = serializers.IntegerField(read_only=True)
    customer_id = serializers.IntegerField(read_only=True)
    direction = serializers.ChoiceField(
        choices=["INBOUND", "OUTBOUND"], required=False, default="OUTBOUND"
    )
    phone_number = serializers.CharField(max_length=50, required=False, allow_null=True)
    staff_user_id = serializers.IntegerField(required=False, allow_null=True)
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    ended_at = serializers.DateTimeField(required=False, allow_null=True)
    duration_seconds = serializers.IntegerField(required=False, allow_null=True)
    outcome = serializers.CharField(max_length=100, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class CommunicationItemSerializer(serializers.Serializer):
    channel = serializers.CharField()
    id = serializers.IntegerField()
    occurred_at = serializers.DateTimeField()
    summary = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    reference = serializers.CharField(allow_null=True)