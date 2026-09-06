from rest_framework import serializers

from common.fields import EnumValueField


class Customer360Serializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    account_number = serializers.CharField()
    display_name = serializers.CharField()
    customer_type = serializers.CharField()
    status = EnumValueField()
    summary = serializers.DictField()
    addresses = serializers.ListField()
    contacts = serializers.ListField()
    portal_access = serializers.DictField(required=False, allow_null=True)
    notifications_summary = serializers.DictField(required=False, allow_null=True)
    recent_notes = serializers.ListField()
    accounting = serializers.DictField(required=False, allow_null=True)
    urls = serializers.DictField()
    permissions = serializers.DictField(required=False, allow_null=True)
