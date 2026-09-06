from django.urls import path

from clients.views import (
    CustomerActionView,
    CustomerAddressDetailView,
    CustomerAddressListView,
    CustomerContactDetailView,
    CustomerContactListView,
    CustomerDetailView,
    CustomerListView,
    CustomerNotificationsView,
    CustomerPortalAccessView,
    CustomerRelationshipDetailView,
    CustomerRelationshipListView,
)

urlpatterns = [
    path("clients", CustomerListView.as_view(), name="client-list"),
    path("clients/<int:customer_id>", CustomerDetailView.as_view(), name="client-detail"),
    path("clients/<int:customer_id>/status", CustomerActionView.as_view(action="status"), name="client-status"),
    path("clients/<int:customer_id>/close", CustomerActionView.as_view(action="close"), name="client-close"),
    path("clients/<int:customer_id>/transfer", CustomerActionView.as_view(action="transfer"), name="client-transfer"),
    path("clients/<int:customer_id>/contacts", CustomerContactListView.as_view(), name="client-contacts"),
    path(
        "clients/<int:customer_id>/contacts/<int:contact_id>",
        CustomerContactDetailView.as_view(),
        name="client-contact-detail",
    ),
    path(
        "clients/<int:customer_id>/relationships",
        CustomerRelationshipListView.as_view(),
        name="client-relationships",
    ),
    path(
        "clients/<int:customer_id>/relationships/<int:relationship_id>",
        CustomerRelationshipDetailView.as_view(),
        name="client-relationship-detail",
    ),
    path("clients/<int:customer_id>/addresses", CustomerAddressListView.as_view(), name="client-addresses"),
    path(
        "clients/<int:customer_id>/addresses/<int:address_id>",
        CustomerAddressDetailView.as_view(),
        name="client-address-detail",
    ),
    path(
        "clients/<int:customer_id>/portal-access",
        CustomerPortalAccessView.as_view(),
        name="client-portal-access",
    ),
    path(
        "clients/<int:customer_id>/notifications",
        CustomerNotificationsView.as_view(),
        name="client-notifications",
    ),
]
