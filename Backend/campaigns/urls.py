from django.urls import path
from campaigns import views

app_name = "campaigns"

urlpatterns = [
    path("campaigns/", views.CampaignListView.as_view(), name="campaign_list"),
    path("campaigns/dashboard/kpis/", views.CampaignDashboardKPIView.as_view(), name="campaign_dashboard_kpis"),
    path("campaigns/upload-image/", views.CampaignProductImageView.as_view(), name="campaign_upload_image"),
    path("campaigns/<int:campaign_id>/", views.CampaignDetailView.as_view(), name="campaign_detail"),
    path("campaigns/<int:campaign_id>/transition/", views.CampaignTransitionView.as_view(), name="campaign_transition"),
    path("campaigns/<int:campaign_id>/codes/", views.CampaignCodeListView.as_view(), name="campaign_code_list"),
    path("campaigns/<int:campaign_id>/sources/", views.CampaignSourceListView.as_view(), name="campaign_source_list"),
    path("campaigns/<int:campaign_id>/schedule/", views.CampaignScheduleListView.as_view(), name="campaign_schedule_list"),
    # AI Campaign Builder routes
    path("campaigns/<int:campaign_id>/products/", views.CampaignProductView.as_view(), name="campaign_products"),
    path("campaigns/<int:campaign_id>/products/<int:product_id>/", views.CampaignProductView.as_view(), name="campaign_product_detail"),
    path("campaigns/<int:campaign_id>/audience/", views.CampaignAudienceView.as_view(), name="campaign_audience"),
    path("campaigns/<int:campaign_id>/offer/", views.CampaignOfferView.as_view(), name="campaign_offer"),
    path("campaigns/<int:campaign_id>/channels/", views.CampaignChannelView.as_view(), name="campaign_channels"),
    path("campaigns/<int:campaign_id>/channels/<int:channel_id>/", views.CampaignChannelView.as_view(), name="campaign_channel_detail"),
    path("campaigns/<int:campaign_id>/budget/", views.CampaignBudgetView.as_view(), name="campaign_budget"),
    path("campaigns/<int:campaign_id>/ai/generate/", views.CampaignAIGenerateView.as_view(), name="campaign_ai_generate"),
    path("campaigns/<int:campaign_id>/ai/jobs/<int:job_id>/", views.CampaignAIJobView.as_view(), name="campaign_ai_job"),
    path("campaigns/<int:campaign_id>/concepts/", views.CampaignConceptsView.as_view(), name="campaign_concepts"),
    path("campaigns/<int:campaign_id>/concepts/<int:concept_id>/select/", views.CampaignConceptSelectView.as_view(), name="campaign_concept_select"),
    path("campaigns/<int:campaign_id>/creative/", views.CampaignCreativeView.as_view(), name="campaign_creative"),
    path("campaigns/<int:campaign_id>/creative/all/", views.CampaignCreativeAllView.as_view(), name="campaign_creative_all"),
    path("campaigns/<int:campaign_id>/creative/<int:creative_id>/regenerate/", views.CampaignCreativeRegenerateView.as_view(), name="campaign_creative_regenerate"),
    path("campaigns/<int:campaign_id>/readiness/", views.CampaignReadinessView.as_view(), name="campaign_readiness"),
    path("campaigns/<int:campaign_id>/progress/", views.CampaignProgressView.as_view(), name="campaign_progress"),
    path("campaigns/<int:campaign_id>/launch/", views.CampaignLaunchView.as_view(), name="campaign_launch"),
    path("campaigns/<int:campaign_id>/analytics/", views.CampaignAnalyticsView.as_view(), name="campaign_analytics"),
    path("campaigns/<int:campaign_id>/billboard/", views.CampaignBillboardView.as_view(), name="campaign_billboard"),
]
