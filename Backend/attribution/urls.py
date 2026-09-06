from django.urls import path
from attribution import views

app_name = "attribution"

urlpatterns = [
    path("attribution/touchpoints/", views.AttributionTouchpointListView.as_view(), name="attribution_touchpoint_list"),
    path("attribution/touchpoints/record/", views.AttributionTouchpointView.as_view(), name="attribution_touchpoint_record"),
    path("attribution/compute/", views.AttributionComputeView.as_view(), name="attribution_compute"),
    path("attribution/revenue-by-campaign/", views.AttributionRevenueByCampaignView.as_view(), name="attribution_revenue_by_campaign"),
]
