from decimal import Decimal

from rest_framework import serializers

from common.fields import EnumValueField


# ---------------------------------------------------------------------------
# Item Serializers
# ---------------------------------------------------------------------------

class SalesOrderItemWriteSerializer(serializers.Serializer):
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


class SalesOrderItemReadSerializer(serializers.Serializer):
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


# ---------------------------------------------------------------------------
# Order Serializers
# ---------------------------------------------------------------------------

class SalesOrderWriteSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    order_date = serializers.DateField(required=False, allow_null=True)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    currency = serializers.CharField(max_length=10, default="KES")
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    terms_and_conditions = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_term_id = serializers.IntegerField(required=False, allow_null=True)
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
    items = SalesOrderItemWriteSerializer(many=True, required=False, default=[])


class SalesOrderReadSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    sequence_value = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    source = serializers.CharField()
    quote_id = serializers.IntegerField(allow_null=True)
    status = EnumValueField()
    order_date = serializers.DateField(allow_null=True)
    expected_delivery_date = serializers.DateField(allow_null=True)
    currency = serializers.CharField()
    subtotal = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_type = serializers.CharField(allow_null=True)
    discount_value = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    additional_charges = serializers.DecimalField(max_digits=18, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=18, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=18, decimal_places=2)
    balance_due = serializers.DecimalField(max_digits=18, decimal_places=2)
    payment_status = EnumValueField()
    notes = serializers.CharField(allow_null=True)
    internal_notes = serializers.CharField(allow_null=True)
    terms_and_conditions = serializers.CharField(allow_null=True)
    payment_term_id = serializers.IntegerField(allow_null=True)
    company_profile_id = serializers.IntegerField(allow_null=True)
    owner_user_id = serializers.IntegerField()
    assigned_user_id = serializers.IntegerField(allow_null=True)
    assigned_team_id = serializers.IntegerField(allow_null=True)
    approved_by = serializers.IntegerField(allow_null=True)
    approved_at = serializers.DateTimeField(allow_null=True)
    confirmed_by = serializers.IntegerField(allow_null=True)
    confirmed_at = serializers.DateTimeField(allow_null=True)
    cancelled_by = serializers.IntegerField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    cancellation_reason = serializers.CharField(allow_null=True)
    version = serializers.IntegerField()
    created_by = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    items = SalesOrderItemReadSerializer(many=True, required=False, default=[])


class SalesOrderUpdateSerializer(serializers.Serializer):
    order_date = serializers.DateField(required=False, allow_null=True)
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    internal_notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    terms_and_conditions = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    payment_term_id = serializers.IntegerField(required=False, allow_null=True)
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


# ---------------------------------------------------------------------------
# Calculation Serializers
# ---------------------------------------------------------------------------

class CalculationRequestSerializer(serializers.Serializer):
    items = SalesOrderItemWriteSerializer(many=True)
    adjustments = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    order_discount_type = serializers.ChoiceField(
        choices=["PERCENTAGE", "FIXED"], required=False, allow_null=True
    )
    order_discount_value = serializers.DecimalField(
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


# ---------------------------------------------------------------------------
# Workflow Serializers
# ---------------------------------------------------------------------------

class OrderActionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)


# ---------------------------------------------------------------------------
# Payment Serializers
# ---------------------------------------------------------------------------

class PaymentWriteSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    payment_method = serializers.ChoiceField(
        choices=["MPESA", "BANK_TRANSFER", "CARD", "CASH", "CHEQUE", "OTHER"]
    )
    payment_reference = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    gateway_reference = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class PaymentReadSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    payment_reference = serializers.CharField(allow_null=True)
    order_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    payment_method = serializers.CharField()
    status = EnumValueField()
    gateway_reference = serializers.CharField(allow_null=True)
    notes = serializers.CharField(allow_null=True)
    received_at = serializers.DateTimeField(allow_null=True)
    confirmed_at = serializers.DateTimeField(allow_null=True)
    confirmed_by = serializers.IntegerField(allow_null=True)
    reversed_at = serializers.DateTimeField(allow_null=True)
    reversed_by = serializers.IntegerField(allow_null=True)
    reversal_reason = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


# ---------------------------------------------------------------------------
# Receipt Serializers
# ---------------------------------------------------------------------------

class ReceiptReadSerializer(serializers.Serializer):
    receipt_id = serializers.IntegerField()
    receipt_number = serializers.CharField()
    payment_id = serializers.IntegerField()
    order_id = serializers.IntegerField()
    customer_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    status = EnumValueField()
    verification_token = serializers.CharField()
    issued_at = serializers.DateTimeField(allow_null=True)
    voided_at = serializers.DateTimeField(allow_null=True)
    voided_by = serializers.IntegerField(allow_null=True)
    void_reason = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ReceiptVoidSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)


class ReceiptVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
