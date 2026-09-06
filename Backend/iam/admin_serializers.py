from rest_framework import serializers

from common.fields import EnumValueField
from iam.models import AccessScope, UserStatus


class OperatorWriteSerializer(serializers.Serializer):
    """Create/edit an internal operator (identity + organisation + role)."""

    username = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=255)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    team_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=[s.value for s in UserStatus], required=False, default="ACTIVE")
    role_codes = serializers.ListField(child=serializers.CharField(), required=False, default=[])


class OperatorUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    team_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=[s.value for s in UserStatus], required=False)


class OperatorReadSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(allow_null=True)
    department_id = serializers.IntegerField(allow_null=True)
    team_id = serializers.IntegerField(allow_null=True)
    status = EnumValueField()
    role_codes = serializers.ListField(child=serializers.CharField())
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    updated_at = serializers.DateTimeField(allow_null=True, required=False)


class OperatorDetailSerializer(OperatorReadSerializer):
    roles = serializers.ListField(child=serializers.DictField())
    direct_permissions = serializers.ListField(child=serializers.DictField())


class RoleAssignSerializer(serializers.Serializer):
    role_codes = serializers.ListField(child=serializers.CharField())


class DirectPermissionSerializer(serializers.Serializer):
    permission_code = serializers.CharField(max_length=150)
    effect = serializers.ChoiceField(choices=["ALLOW", "DENY"])
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class RoleWriteSerializer(serializers.Serializer):
    """Create/edit a role.

    Supports both the internal ``permission_codes``/``access_policy_codes``
    contract and the Roles & Rights spec surface: ``rights`` (alias for
    ``permission_codes``), ``scope`` (single scope value), ``status``
    (ACTIVE/INACTIVE alias for ``is_active``). ``code`` is optional and derived
    from ``name`` when omitted.
    """

    name = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)
    is_system_role = serializers.BooleanField(required=False, default=False)
    status = serializers.ChoiceField(choices=["ACTIVE", "INACTIVE"], required=False)
    permission_codes = serializers.ListField(child=serializers.CharField(), required=False, default=[])
    rights = serializers.ListField(child=serializers.CharField(), required=False, default=[])
    scope = serializers.ChoiceField(
        choices=[s.value for s in AccessScope], required=False, allow_null=True
    )
    access_policy_codes = serializers.ListField(child=serializers.CharField(), required=False, default=[])


class RoleReadSerializer(serializers.Serializer):
    role_id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()
    is_system_role = serializers.BooleanField()
    permission_codes = serializers.ListField(child=serializers.CharField())
    scope_codes = serializers.ListField(child=serializers.CharField())
    effective_scope = EnumValueField()
    operator_count = serializers.IntegerField(required=False, default=0)
    created_at = serializers.DateTimeField(allow_null=True, required=False)
    updated_at = serializers.DateTimeField(allow_null=True, required=False)


class ScopeSerializer(serializers.Serializer):
    scopes = serializers.ListField(child=serializers.CharField())


class AccessReviewSerializer(serializers.Serializer):
    operator = serializers.DictField()
    roles = serializers.ListField(child=serializers.DictField())
    effective_permissions = serializers.ListField(child=serializers.DictField())
    scope = serializers.DictField()


class RightsCatalogueSerializer(serializers.Serializer):
    permissions = serializers.ListField(child=serializers.DictField())


SCOPE_MEANINGS = {
    AccessScope.NONE.value: "No records",
    AccessScope.OWN.value: "Records owned by the operator",
    AccessScope.ASSIGNED.value: "Records assigned to the operator",
    AccessScope.TEAM.value: "Records belonging to the operator's team",
    AccessScope.DEPARTMENT.value: "Records belonging to the operator's department",
    AccessScope.ALL.value: "All records permitted by the system",
}