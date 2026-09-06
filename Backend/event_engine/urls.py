from django.urls import path
from event_engine import views
from event_engine.sse import SSEStreamView

app_name = "event_engine"

urlpatterns = [
    path("sse/stream", SSEStreamView.as_view(), name="sse_stream"),
    path("event-outbox/", views.EventOutboxListView.as_view(), name="event_outbox_list"),
    path("event-outbox/process/", views.EventOutboxProcessView.as_view(), name="event_outbox_process"),
    path("event-outbox/<str:event_id>/retry/", views.EventOutboxRetryView.as_view(), name="event_outbox_retry"),
]
