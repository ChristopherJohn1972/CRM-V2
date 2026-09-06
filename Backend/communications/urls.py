from django.urls import path

from communications.views import (
    CallView,
    CommunicationHistoryView,
    EmailView,
    SmsView,
    SmsWebhookView,
)

urlpatterns = [
    path(
        "clients/<int:customer_id>/communications",
        CommunicationHistoryView.as_view(),
        name="client-communications",
    ),
    path("clients/<int:customer_id>/sms", SmsView.as_view(), name="client-sms"),
    path("clients/<int:customer_id>/email", EmailView.as_view(), name="client-email"),
    path("clients/<int:customer_id>/calls", CallView.as_view(), name="client-calls"),
    path("communications/webhooks/sms", SmsWebhookView.as_view(), name="webhook-sms"),
]
