from django.urls import path
from leads import views

app_name = "leads"

urlpatterns = [
    path("leads/", views.LeadListView.as_view(), name="lead_list"),
    path("leads/<int:lead_id>/", views.LeadDetailView.as_view(), name="lead_detail"),
    path("leads/<int:lead_id>/transition/", views.LeadTransitionView.as_view(), name="lead_transition"),
    path("leads/<int:lead_id>/qualify/", views.LeadQualifyView.as_view(), name="lead_qualify"),
    path("leads/<int:lead_id>/follow-ups/", views.LeadFollowUpListView.as_view(), name="lead_follow_up_list"),
    path("leads/<int:lead_id>/follow-ups/<int:follow_up_id>/complete/", views.LeadFollowUpCompleteView.as_view(), name="lead_follow_up_complete"),
    path("leads/<int:lead_id>/consent/", views.LeadConsentView.as_view(), name="lead_consent"),
]
