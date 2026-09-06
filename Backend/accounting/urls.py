from django.urls import path

from accounting.views import (
    CustomerAccountingSummaryView,
    CustomerAccountingTransactionsView,
)

urlpatterns = [
    path(
        "clients/<int:customer_id>/accounting-summary",
        CustomerAccountingSummaryView.as_view(),
        name="client-accounting-summary",
    ),
    path(
        "clients/<int:customer_id>/accounting-transactions",
        CustomerAccountingTransactionsView.as_view(),
        name="client-accounting-transactions",
    ),
]
