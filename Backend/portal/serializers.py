from rest_framework import serializers

from common.fields import EnumValueField
from portal.enums import PortalRelationshipType, PortalUserStatus


class PortalLoginRequestSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=50)
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(max_length=255, write_only=True)


class PortalLoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField()
    must_change_password = serializers.BooleanField()
    portal_user = serializers.DictField()


class PortalChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=255, write_only=True)
    new_password = serializers.CharField(max_length=255, write_only=True)


class PortalSetupPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=255, write_only=True)


class PortalForgotPasswordSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=50)
    email = serializers.EmailField(max_length=255)


class PortalResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    new_password = serializers.CharField(max_length=255, write_only=True)


class PortalUserWriteSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    customer_account_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=[r.value for r in PortalRelationshipType], required=False, default="CONTACT"
    )
    send_temp_password = serializers.BooleanField(default=False)


class PortalUserReadSerializer(serializers.Serializer):
    portal_user_id = serializers.IntegerField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    status = EnumValueField()
    email_verified_at = serializers.DateTimeField(allow_null=True)
    last_login_at = serializers.DateTimeField(allow_null=True)


class PortalUserStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[s.value for s in PortalUserStatus])


class PortalCustomerAccessWriteSerializer(serializers.Serializer):
    customer_account_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=[r.value for r in PortalRelationshipType], required=False, default="CONTACT"
    )
    is_primary = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)


class PortalCustomerAccessUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=[r.value for r in PortalRelationshipType], required=False
    )
    is_primary = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class PortalCustomerAccessReadSerializer(serializers.Serializer):
    portal_user_customer_id = serializers.IntegerField()
    portal_user_id = serializers.IntegerField()
    customer_account_id = serializers.IntegerField()
    account_number = serializers.CharField(allow_null=True)
    customer_name = serializers.CharField(allow_null=True)
    role = EnumValueField()
    is_primary = serializers.BooleanField()
    is_active = serializers.BooleanField()


class PortalPermissionAssignSerializer(serializers.Serializer):
    permission_code = serializers.CharField(max_length=150)
    effect = serializers.ChoiceField(choices=["ALLOW", "DENY"], required=False, default="ALLOW")


class PortalPermissionReadSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    resource = serializers.CharField()
    action = serializers.CharField()
    effect = serializers.CharField(allow_null=True)


class PortalMeSerializer(serializers.Serializer):
    portal_user_id = serializers.IntegerField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField())
    customer_account_ids = serializers.ListField(child=serializers.IntegerField())
    must_change_password = serializers.BooleanField()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class PortalDashboardSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    customer_number = serializers.CharField()
    display_name = serializers.CharField()
    account_status = EnumValueField()
    outstanding_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    momentum = serializers.IntegerField()
    momentum_remainder = serializers.DecimalField(max_digits=15, decimal_places=2)
    next_momentum_required = serializers.DecimalField(max_digits=15, decimal_places=2)
    payments_count = serializers.IntegerField()
    open_complaints = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    recent_activity = serializers.ListField(child=serializers.DictField())


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class PortalPaymentReadSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    payment_date = serializers.DateField()
    reference = serializers.CharField()
    payment_method = serializers.CharField(allow_null=True)
    status = EnumValueField()
    description = serializers.CharField(allow_null=True)
    has_receipt = serializers.BooleanField()


class PortalPaymentFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["PENDING", "CONFIRMED", "FAILED", "CANCELLED"], required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    page = serializers.IntegerField(required=False, default=1)
    page_size = serializers.IntegerField(required=False, default=20)


class PortalPaymentListResponseSerializer(serializers.Serializer):
    results = PortalPaymentReadSerializer(many=True)
    total_qualifying = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    momentum = serializers.IntegerField()
    remainder = serializers.DecimalField(max_digits=15, decimal_places=2)
    count = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------

class PortalComplaintCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH", "URGENT"], default="MEDIUM")
    preferred_contact = serializers.ChoiceField(choices=["EMAIL", "PHONE", "PORTAL"], default="PORTAL")


class PortalComplaintReadSerializer(serializers.Serializer):
    complaint_id = serializers.IntegerField()
    complaint_number = serializers.CharField()
    subject = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    priority = serializers.CharField()
    status = EnumValueField()
    preferred_contact = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class PortalComplaintMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField()


class PortalComplaintTimelineEntrySerializer(serializers.Serializer):
    type = serializers.CharField()
    old_status = serializers.CharField(allow_null=True)
    new_status = serializers.CharField(allow_null=True)
    sender_type = serializers.CharField(allow_null=True)
    portal_user_id = serializers.IntegerField(allow_null=True)
    user_id = serializers.IntegerField(allow_null=True)
    message = serializers.CharField(allow_null=True)
    changed_by = serializers.IntegerField(allow_null=True)
    changer_type = serializers.CharField(allow_null=True)
    note = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class PortalNotificationReadSerializer(serializers.Serializer):
    notification_id = serializers.IntegerField()
    type = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField(allow_null=True)
    reference_type = serializers.CharField(allow_null=True)
    reference_id = serializers.IntegerField(allow_null=True)
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class PortalNotificationListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    results = PortalNotificationReadSerializer(many=True)


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

class PortalMomentumSummarySerializer(serializers.Serializer):
    total_qualifying = serializers.DecimalField(max_digits=15, decimal_places=2)
    momentum = serializers.IntegerField()
    remainder = serializers.DecimalField(max_digits=15, decimal_places=2)
    next_momentum_required = serializers.DecimalField(max_digits=15, decimal_places=2)
    never_expires = serializers.BooleanField()


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

class PortalRewardReadSerializer(serializers.Serializer):
    reward_id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    required_momentum = serializers.IntegerField()
    status = EnumValueField()
    redemption_limit = serializers.IntegerField()
    available_from = serializers.DateField(allow_null=True)
    available_until = serializers.DateField(allow_null=True)


class PortalRewardRedemptionReadSerializer(serializers.Serializer):
    redemption_id = serializers.IntegerField()
    reward_id = serializers.IntegerField()
    reward_name = serializers.CharField()
    momentum_used = serializers.IntegerField()
    status = EnumValueField()
    redeemed_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()