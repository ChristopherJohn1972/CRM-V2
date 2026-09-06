from django.urls import path

from customer360.views import Customer360View

urlpatterns = [
    path("clients/<int:customer_id>/360", Customer360View.as_view(), name="client-360"),
]
