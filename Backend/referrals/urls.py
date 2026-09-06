from django.urls import path
from referrals import views

app_name = "referrals"

urlpatterns = [
    path("referrals/codes/", views.ReferralCodeListView.as_view(), name="referral_code_list"),
    path("referrals/codes/<int:code_id>/", views.ReferralCodeDetailView.as_view(), name="referral_code_detail"),
    path("referrals/codes/<int:code_id>/events/", views.ReferralEventListView.as_view(), name="referral_event_list"),
    path("referrals/track/<str:code>/", views.ReferralTrackView.as_view(), name="referral_track"),
]
