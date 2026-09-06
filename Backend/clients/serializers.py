from rest_framework import serializers

from clients.enums import CustomerStatus, CustomerType
from common.fields import EnumValueField, EnumValueMixin


def mask_identifier(value, keep_front=3, keep_back=2):
    if not value:
        return value
    if len(value) <= keep_front + keep_back:
        return "*" * len(value)
    return value[:keep_front] + "*" * (len(value) - keep_front - keep_back) + value[-keep_back:]


ADDRESS_TYPES = ["BILLING", "SHIPPING", "OFFICE", "HOME", "OTHER"]
ACCESS_CLASSIFICATIONS = ["PUBLIC", "INTERNAL", "RESTRICTED", "CONFIDENTIAL"]


class AddressSerializer(EnumValueMixin, serializers.Serializer):
    address_id = serializers.IntegerField(read_only=True)
    address_type = serializers.ChoiceField(
        choices=ADDRESS_TYPES, required=False, default="OFFICE"
    )
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100, required=False, allow_null=True)
    postal_code = serializers.CharField(max_length=30, required=False, allow_null=True)
    country = serializers.CharField(max_length=100, required=False, allow_null=True)
    is_primary = serializers.BooleanField(required=False, default=False)


class CustomerWriteSerializer(serializers.Serializer):
    customer_type = serializers.ChoiceField(
        choices=[c.value for c in CustomerType], default=CustomerType.BUSINESS.value
    )
    first_name = serializers.CharField(max_length=100, required=False, allow_null=True)
    middle_name = serializers.CharField(max_length=100, required=False, allow_null=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_null=True)
    legal_name = serializers.CharField(max_length=255, required=False, allow_null=True)
    email = serializers.EmailField(max_length=255, required=False, allow_null=True)
    phone = serializers.CharField(max_length=50, required=False, allow_null=True)
    customer_category = serializers.CharField(max_length=100, required=False, allow_null=True)
    segment = serializers.CharField(max_length=100, required=False, allow_null=True)
    industry = serializers.CharField(max_length=150, required=False, allow_null=True)
    registration_number = serializers.CharField(max_length=100, required=False, allow_null=True)
    tax_identifier = serializers.CharField(max_length=100, required=False, allow_null=True)
    addresses = AddressSerializer(many=True, required=False)
    version = serializers.IntegerField(required=False)

    def validate(self, attrs):
        customer_type = attrs.get("customer_type", CustomerType.BUSINESS.value)
        is_partial_update = self.partial
        if customer_type == CustomerType.INDIVIDUAL.value:
            if not is_partial_update or "first_name" in attrs or "legal_name" in attrs:
                if not attrs.get("first_name") and not attrs.get("legal_name"):
                    raise serializers.ValidationError(
                        {"first_name": "Individual customers require a first name or legal name."}
                    )
        else:
            if not is_partial_update or "legal_name" in attrs:
                if not attrs.get("legal_name"):
                    raise serializers.ValidationError(
                        {"legal_name": "Business customers require a legal name."}
                    )
        return attrs


class CustomerSerializer(EnumValueMixin, serializers.Serializer):
    customer_id = serializers.IntegerField()
    account_number = serializers.CharField(source="customer_number")
    customer_number = serializers.CharField()
    account_number_status = EnumValueField()
    customer_type = EnumValueField()
    first_name = serializers.CharField()
    middle_name = serializers.CharField()
    last_name = serializers.CharField()
    legal_name = serializers.CharField()
    email = serializers.CharField()
    phone = serializers.CharField()
    customer_category = serializers.CharField()
    segment = serializers.CharField()
    industry = serializers.CharField()
    registration_number = serializers.SerializerMethodField()
    tax_identifier = serializers.SerializerMethodField()
    status = EnumValueField()
    status_reason = serializers.CharField()
    assigned_user_id = serializers.IntegerField()
    assigned_team_id = serializers.IntegerField()
    branch_id = serializers.IntegerField()
    version = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    deleted_at = serializers.DateTimeField(required=False, allow_null=True)

    def _can_read_sensitive(self):
        principal = self.context.get("principal")
        if principal is None:
            return False
        return principal.has_permission("clients.customer.sensitive.read")

    def get_tax_identifier(self, obj):
        if self._can_read_sensitive():
            return obj.tax_identifier
        return mask_identifier(obj.tax_identifier)

    def get_registration_number(self, obj):
        if self._can_read_sensitive():
            return obj.registration_number
        return mask_identifier(obj.registration_number)


class ContactSerializer(serializers.Serializer):
    contact_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    job_title = serializers.CharField()
    email = serializers.CharField()
    phone = serializers.CharField()
    mobile = serializers.CharField()
    role_id = serializers.IntegerField()
    role_code = serializers.SerializerMethodField()
    is_primary = serializers.BooleanField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_role_code(self, obj):
        role = getattr(obj, "role", None)
        return getattr(role, "code", None)


class ContactWriteSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    job_title = serializers.CharField(max_length=150, required=False, allow_null=True)
    email = serializers.EmailField(max_length=255, required=False, allow_null=True)
    phone = serializers.CharField(max_length=50, required=False, allow_null=True)
    mobile = serializers.CharField(max_length=50, required=False, allow_null=True)
    role_id = serializers.IntegerField(required=False, allow_null=True)
    is_primary = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)


class RelationshipSerializer(serializers.Serializer):
    relationship_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    related_customer_id = serializers.IntegerField()
    relationship_type = serializers.CharField()
    description = serializers.CharField()
    related_display_name = serializers.SerializerMethodField()
    related_account_number = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_related_display_name(self, obj):
        related = self.context.get("related_map", {}).get(obj.related_customer_id)
        if related is None:
            return None
        return related.get_display_name()

    def get_related_account_number(self, obj):
        related = self.context.get("related_map", {}).get(obj.related_customer_id)
        return related.customer_number if related else None


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c.value for c in CustomerStatus])
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class OwnershipTransferSerializer(serializers.Serializer):
    assigned_user_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_team_id = serializers.IntegerField(required=False, allow_null=True)
