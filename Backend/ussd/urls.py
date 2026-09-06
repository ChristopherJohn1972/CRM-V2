from django.urls import path
from ussd import views

app_name = "ussd"

urlpatterns = [
    path("ussd/gateway/", views.UssdGatewayView.as_view(), name="ussd_gateway"),
    path("ussd/sessions/", views.UssdSessionListView.as_view(), name="ussd_session_list"),
]
