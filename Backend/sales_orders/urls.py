from django.urls import path

from sales_orders import views

urlpatterns = [
    # Orders
    path("sales-orders/", views.SalesOrderListView.as_view(), name="sales_order_list"),
    path("sales-orders/<int:order_id>/", views.SalesOrderDetailView.as_view(), name="sales_order_detail"),

    # Order Items
    path("sales-orders/<int:order_id>/items/", views.SalesOrderItemListView.as_view(), name="sales_order_item_list"),
    path("sales-orders/<int:order_id>/items/<int:item_id>/", views.SalesOrderItemDetailView.as_view(), name="sales_order_item_detail"),

    # Calculation
    path("sales-orders/calculate/", views.SalesOrderCalculationView.as_view(), name="sales_order_calculate"),

    # Workflow
    path("sales-orders/<int:order_id>/confirm/", views.SalesOrderConfirmView.as_view(), name="sales_order_confirm"),
    path("sales-orders/<int:order_id>/cancel/", views.SalesOrderCancelView.as_view(), name="sales_order_cancel"),
    path("sales-orders/<int:order_id>/submit-approval/", views.SalesOrderSubmitApprovalView.as_view(), name="sales_order_submit_approval"),
    path("sales-orders/<int:order_id>/approve/", views.SalesOrderApproveView.as_view(), name="sales_order_approve"),
    path("sales-orders/<int:order_id>/processing/", views.SalesOrderProcessingView.as_view(), name="sales_order_processing"),
    path("sales-orders/<int:order_id>/fulfilled/", views.SalesOrderFulfilledView.as_view(), name="sales_order_fulfilled"),

    # Activity
    path("sales-orders/<int:order_id>/activity/", views.SalesOrderActivityView.as_view(), name="sales_order_activity"),

    # Payments (nested under order)
    path("sales-orders/<int:order_id>/payments/", views.PaymentListByOrderView.as_view(), name="sales_order_payment_list"),

    # Payments (top-level)
    path("sales-orders/payments/", views.PaymentListView.as_view(), name="payment_list"),
    path("sales-orders/payments/<int:payment_id>/confirm/", views.PaymentConfirmView.as_view(), name="payment_confirm"),
    path("sales-orders/payments/<int:payment_id>/reverse/", views.PaymentReverseView.as_view(), name="payment_reverse"),

    # Receipts (nested under order)
    path("sales-orders/<int:order_id>/receipts/", views.ReceiptListView.as_view(), name="sales_order_receipt_list"),

    # Receipts (top-level)
    path("sales-orders/receipts/<int:receipt_id>/", views.ReceiptDetailView.as_view(), name="receipt_detail"),
    path("sales-orders/receipts/<int:receipt_id>/void/", views.ReceiptVoidView.as_view(), name="receipt_void"),
    path("sales-orders/receipts/<int:receipt_id>/pdf/", views.ReceiptPdfView.as_view(), name="receipt_pdf"),
    path("sales-orders/receipts/verify/", views.ReceiptVerifyView.as_view(), name="receipt_verify"),

    # Quote Conversion
    path("sales-orders/convert-quote/<int:quote_id>/", views.QuoteConvertToOrderView.as_view(), name="quote_convert_to_order"),
]
