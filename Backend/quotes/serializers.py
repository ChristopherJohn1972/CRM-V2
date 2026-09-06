from decimal import Decimal

from rest_framework import serializers

from common.fields import EnumValueField


class QuoteItemWriteSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(
        choices=["PRODUCT", "SERVICE", "CUSTOM"], default="CUSTOM"
    )
    reference_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    sku = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(max_length=500)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FIXED"], required=False, allow_null=True
    )
    discount_value = serializers.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00"), required=False
    )
    tax_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    sort_order = serializers.IntegerField(required=False, default=0)
    unit_of_measure = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class QuoteItemReadSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    item_type = serializers.CharField()
    reference_id = serializers.CharField(allow_null=True)
    sku = serializers.CharField(allow_null=True)
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_type = serializers.CharField(allow_null=True)
    discount_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    tax_code = serializers.CharField(allow_null=True)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    gross_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=18, decimal_places=2)
    sort_order = serializers.IntegerField()
    unit_of_measure = serializers.CharField(allow_null=True)
    notes = serializers.CharField(allow_null=True)


class QuoteWriteSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    quote_type = serializers.ChoiceField(choices=["PRODUCT", "SERVICE", "PROJECT"])
    title = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    currency = serializers.CharField(max_length=10, default="KES")
    quote_date = serializers.DateField(required=False, allow_null=True)
    valid_until = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    terms_and_conditions = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_term_id = serializers.IntegerField(required=False, allow_null=True)
    template_id = serializers.IntegerField(required=False, allow_null=True)
    company_profile_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_user_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_team_id = serializers.IntegerField(required=False, allow_null=True)
    discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FIXED"], required=False, allow_null=True
    )
    discount_value = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    additional_charges = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    items = QuoteItemWriteSerializer(many=True, required=False, default=[])


class QuoteReadSerializer(serializers.Serializer):
    quote_id = serializers.IntegerField()
    quote_number = serializers.CharField()
    sequence_value = serializers.IntegerField()
    revision = serializers.IntegerField()
    quote_type = EnumValueField()
    title = serializers.CharField(allow_null=True)
    customer_id = serializers.IntegerField()
    status = EnumValueField()
    currency = serializers.CharField()
    quote_date = serializers.DateField(allow_null=True)
    valid_until = serializers.DateField(allow_null=True)
    subtotal = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_type = EnumValueField(allow_null=True)
    discount_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    additional_charges = serializers.DecimalField(max_digits=18, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=18, decimal_places=2)
    notes = serializers.CharField(allow_null=True)
    terms_and_conditions = serializers.CharField(allow_null=True)
    payment_term_id = serializers.IntegerField(allow_null=True)
    template_id = serializers.IntegerField(allow_null=True)
    company_profile_id = serializers.IntegerField(allow_null=True)
    owner_user_id = serializers.IntegerField()
    assigned_user_id = serializers.IntegerField(allow_null=True)
    assigned_team_id = serializers.IntegerField(allow_null=True)
    approved_by = serializers.IntegerField(allow_null=True)
    approved_at = serializers.DateTimeField(allow_null=True)
    sent_at = serializers.DateTimeField(allow_null=True)
    viewed_at = serializers.DateTimeField(allow_null=True)
    accepted_at = serializers.DateTimeField(allow_null=True)
    rejected_at = serializers.DateTimeField(allow_null=True)
    expired_at = serializers.DateTimeField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    version = serializers.IntegerField()
    created_by = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    items = QuoteItemReadSerializer(many=True, required=False, default=[])


class QuoteUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    quote_date = serializers.DateField(required=False, allow_null=True)
    valid_until = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    terms_and_conditions = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_term_id = serializers.IntegerField(required=False, allow_null=True)
    template_id = serializers.IntegerField(required=False, allow_null=True)
    company_profile_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_user_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_team_id = serializers.IntegerField(required=False, allow_null=True)
    discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FIXED"], required=False, allow_null=True
    )
    discount_value = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    additional_charges = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    version = serializers.IntegerField(required=False)


class CalculationRequestSerializer(serializers.Serializer):
    items = QuoteItemWriteSerializer(many=True)
    discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FIXED"], required=False, allow_null=True
    )
    discount_value = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=Decimal("0.00")
    )
    additional_charges = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=Decimal("0.00")
    )
    currency = serializers.CharField(max_length=10, default="KES")


class CalculationLineSerializer(serializers.Serializer):
    gross_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=18, decimal_places=2)


class CalculationResponseSerializer(serializers.Serializer):
    currency = serializers.CharField()
    lines = CalculationLineSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_discount = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_tax = serializers.DecimalField(max_digits=18, decimal_places=2)
    additional_charges = serializers.DecimalField(max_digits=18, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=18, decimal_places=2)


class QuoteTemplateWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)
    template_type = serializers.ChoiceField(
        choices=["DEFAULT", "PRODUCT", "SERVICE", "PROJECT", "CUSTOM"], default="DEFAULT"
    )
    content_config = serializers.JSONField(required=False, allow_null=True)
    is_default = serializers.BooleanField(default=False)


class QuoteTemplateReadSerializer(serializers.Serializer):
    template_id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    template_type = EnumValueField()
    status = EnumValueField()
    current_version = serializers.IntegerField()
    is_default = serializers.BooleanField()
    content_config = serializers.JSONField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class QuoteActionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)


class QuotePortalQuoteReadSerializer(serializers.Serializer):
    quote_id = serializers.IntegerField()
    quote_number = serializers.CharField()
    quote_type = EnumValueField()
    title = serializers.CharField(allow_null=True)
    status = EnumValueField()
    currency = serializers.CharField()
    quote_date = serializers.DateField(allow_null=True)
    valid_until = serializers.DateField(allow_null=True)
    subtotal = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=18, decimal_places=2)
    items = QuoteItemReadSerializer(many=True, required=False, default=[])
    terms_and_conditions = serializers.CharField(allow_null=True)
    notes = serializers.CharField(allow_null=True)
    accepted_at = serializers.DateTimeField(allow_null=True)
    rejected_at = serializers.DateTimeField(allow_null=True)
    valid_until = serializers.DateField(allow_null=True)


class ClientResponseSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class QuotePortalEventReadSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    event_type = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    occurred_at = serializers.DateTimeField()
