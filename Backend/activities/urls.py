from django.urls import path

from activities.views import (
    CustomerActivityDetailView,
    CustomerActivityListView,
    CustomerNoteDetailView,
    CustomerNoteListView,
    CustomerTimelineView,
)

urlpatterns = [
    path("clients/<int:customer_id>/activities", CustomerActivityListView.as_view(), name="client-activities"),
    path(
        "clients/<int:customer_id>/activities/<int:activity_id>",
        CustomerActivityDetailView.as_view(),
        name="client-activity-detail",
    ),
    path(
        "clients/<int:customer_id>/activities/<int:activity_id>/complete",
        CustomerActivityDetailView.as_view(action="complete"),
        name="client-activity-complete",
    ),
    path("clients/<int:customer_id>/notes", CustomerNoteListView.as_view(), name="client-notes"),
    path(
        "clients/<int:customer_id>/notes/<int:note_id>",
        CustomerNoteDetailView.as_view(),
        name="client-note-detail",
    ),
    path("clients/<int:customer_id>/timeline", CustomerTimelineView.as_view(), name="client-timeline"),
]
