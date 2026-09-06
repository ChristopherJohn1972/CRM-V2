from django.urls import path

from documents.views import (
    DocumentDetailView,
    DocumentDownloadView,
    DocumentListView,
    DocumentServeView,
    DocumentVersionListView,
)

urlpatterns = [
    path("clients/<int:customer_id>/documents", DocumentListView.as_view(), name="client-documents"),
    path(
        "clients/<int:customer_id>/documents/<int:document_id>",
        DocumentDetailView.as_view(),
        name="client-document-detail",
    ),
    path(
        "clients/<int:customer_id>/documents/<int:document_id>/download",
        DocumentDownloadView.as_view(),
        name="client-document-download",
    ),
    path(
        "clients/<int:customer_id>/documents/<int:document_id>/versions",
        DocumentVersionListView.as_view(),
        name="client-document-versions",
    ),
    path(
        "clients/<int:customer_id>/documents/<int:document_id>/versions/<int:version_num>/download",
        DocumentDownloadView.as_view(),
        name="client-document-version-download",
    ),
    path("documents/serve", DocumentServeView.as_view(), name="document-serve"),
]
