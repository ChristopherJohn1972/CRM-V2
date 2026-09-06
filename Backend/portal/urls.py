from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from portal.views import (
    PortalChangePasswordView,
    PortalComplaintDetailView,
    PortalComplaintListView,
    PortalComplaintMessageView,
    PortalComplaintTimelineView,
    PortalCustomerDetailView,
    PortalCustomerListView,
    PortalDashboardView,
    PortalDocumentDetailView,
    PortalDocumentDownloadView,
    PortalDocumentListView,
    PortalFaqView,
    PortalForgotPasswordView,
    PortalLoginView,
    PortalLogoutView,
    PortalMeView,
    PortalMomentumHistoryView,
    PortalMomentumView,
    PortalNotificationListView,
    PortalNotificationReadAllView,
    PortalNotificationReadView,
    PortalPaymentDetailView,
    PortalPaymentListView,
    PortalPaymentReceiptView,
    PortalPermissionDetailView,
    PortalPermissionListView,
    PortalProfileView,
    PortalResetPasswordView,
    PortalRewardEligibleView,
    PortalRewardListView,
    PortalRewardRedeemView,
    PortalRewardRedemptionListView,
    PortalSetupPasswordView,
    PortalSupportRequestView,
    PortalUserCustomerLinkView,
    PortalUserCustomerListView,
    PortalUserDetailView,
    PortalUserListView,
    PortalUserPasswordView,
    PortalUserStatusView,
)
from portal.portal_phase4_views import (
    PortalCampaignListView,
    PortalCampaignDetailView,
    PortalLeadSelfRegisterView,
    PortalReferralCodeListView,
    PortalReferralTrackingView,
    PortalMomentumBalanceView,
    PortalMomentumHistoryView as PortalMomentumBalanceHistoryView,
)
from portal.portal_quote_views import (
    PortalQuoteAcceptView,
    PortalQuoteAcknowledgeView,
    PortalQuoteChangeRequestView,
    PortalQuoteDeclineView,
    PortalQuoteDetailView,
    PortalQuoteDocumentView,
    PortalQuoteEventsView,
    PortalQuoteListView,
)

urlpatterns = [
    # Auth
    path("portal/auth/login", csrf_exempt(PortalLoginView.as_view()), name="portal-auth-login"),
    path("portal/auth/logout", csrf_exempt(PortalLogoutView.as_view()), name="portal-auth-logout"),
    path("portal/auth/change-password", csrf_exempt(PortalChangePasswordView.as_view()), name="portal-auth-change-password"),
    path("portal/auth/setup-password", csrf_exempt(PortalSetupPasswordView.as_view()), name="portal-auth-setup-password"),
    path("portal/auth/forgot-password", csrf_exempt(PortalForgotPasswordView.as_view()), name="portal-auth-forgot-password"),
    path("portal/auth/reset-password", csrf_exempt(PortalResetPasswordView.as_view()), name="portal-auth-reset-password"),

    # Profile
    path("portal/profile", csrf_exempt(PortalProfileView.as_view()), name="portal-profile"),

    # Me
    path("portal/me", csrf_exempt(PortalMeView.as_view()), name="portal-me"),
    path("portal/auth/me", csrf_exempt(PortalMeView.as_view()), name="portal-auth-me"),

    # Dashboard
    path("portal/dashboard", csrf_exempt(PortalDashboardView.as_view()), name="portal-dashboard"),

    # Customer portal views
    path("portal/accounts", csrf_exempt(PortalCustomerListView.as_view()), name="portal-customer-list"),
    path("portal/accounts/<int:customer_account_id>", csrf_exempt(PortalCustomerDetailView.as_view()), name="portal-customer-detail"),

    # Payments
    path("portal/accounts/<int:customer_account_id>/payments", csrf_exempt(PortalPaymentListView.as_view()), name="portal-payment-list"),
    path("portal/accounts/<int:customer_account_id>/payments/<int:payment_id>", csrf_exempt(PortalPaymentDetailView.as_view()), name="portal-payment-detail"),
    path("portal/accounts/<int:customer_account_id>/payments/<int:payment_id>/receipt", csrf_exempt(PortalPaymentReceiptView.as_view()), name="portal-payment-receipt"),

    # Complaints
    path("portal/accounts/<int:customer_account_id>/complaints", csrf_exempt(PortalComplaintListView.as_view()), name="portal-complaint-list"),
    path("portal/accounts/<int:customer_account_id>/complaints/<int:complaint_id>", csrf_exempt(PortalComplaintDetailView.as_view()), name="portal-complaint-detail"),
    path("portal/accounts/<int:customer_account_id>/complaints/<int:complaint_id>/messages", csrf_exempt(PortalComplaintMessageView.as_view()), name="portal-complaint-messages"),
    path("portal/accounts/<int:customer_account_id>/complaints/<int:complaint_id>/timeline", csrf_exempt(PortalComplaintTimelineView.as_view()), name="portal-complaint-timeline"),

    # Documents
    path("portal/accounts/<int:customer_account_id>/documents", csrf_exempt(PortalDocumentListView.as_view()), name="portal-document-list"),
    path("portal/accounts/<int:customer_account_id>/documents/<int:document_id>", csrf_exempt(PortalDocumentDetailView.as_view()), name="portal-document-detail"),
    path("portal/accounts/<int:customer_account_id>/documents/<int:document_id>/download", csrf_exempt(PortalDocumentDownloadView.as_view()), name="portal-document-download"),

    # Notifications
    path("portal/notifications", csrf_exempt(PortalNotificationListView.as_view()), name="portal-notification-list"),
    path("portal/notifications/<int:notification_id>/read", csrf_exempt(PortalNotificationReadView.as_view()), name="portal-notification-read"),
    path("portal/notifications/read-all", csrf_exempt(PortalNotificationReadAllView.as_view()), name="portal-notification-read-all"),

    # Momentum
    path("portal/accounts/<int:customer_account_id>/momentum", csrf_exempt(PortalMomentumView.as_view()), name="portal-momentum"),
    path("portal/accounts/<int:customer_account_id>/momentum/history", csrf_exempt(PortalMomentumHistoryView.as_view()), name="portal-momentum-history"),

    # Rewards
    path("portal/rewards", csrf_exempt(PortalRewardListView.as_view()), name="portal-reward-list"),
    path("portal/accounts/<int:customer_account_id>/rewards/eligible", csrf_exempt(PortalRewardEligibleView.as_view()), name="portal-reward-eligible"),
    path("portal/accounts/<int:customer_account_id>/rewards/<int:reward_id>/redeem", csrf_exempt(PortalRewardRedeemView.as_view()), name="portal-reward-redeem"),
    path("portal/accounts/<int:customer_account_id>/rewards/redemptions", csrf_exempt(PortalRewardRedemptionListView.as_view()), name="portal-reward-redemptions"),

    # Admin: portal user management
    path("portal/users", PortalUserListView.as_view(), name="portal-users"),
    path("portal/users/<int:portal_user_id>", PortalUserDetailView.as_view(), name="portal-user-detail"),
    path("portal/users/<int:portal_user_id>/status", PortalUserStatusView.as_view(), name="portal-user-status"),
    path("portal/users/<int:portal_user_id>/password", PortalUserPasswordView.as_view(), name="portal-user-password"),
    path("portal/users/<int:portal_user_id>/customers", PortalUserCustomerListView.as_view(), name="portal-user-customers"),
    path(
        "portal/users/<int:portal_user_id>/customers/<int:link_id>",
        PortalUserCustomerLinkView.as_view(),
        name="portal-user-customer-link",
    ),
    path("portal/users/<int:portal_user_id>/permissions", PortalPermissionListView.as_view(), name="portal-user-permissions"),
    path(
        "portal/users/<int:portal_user_id>/permissions/<str:permission_code>",
        PortalPermissionDetailView.as_view(),
        name="portal-user-permission-detail",
    ),
    path("portal/support/faqs", csrf_exempt(PortalFaqView.as_view()), name="portal-support-faqs"),
    path("portal/support/request", csrf_exempt(PortalSupportRequestView.as_view()), name="portal-support-request"),

    # Portal Quotes
    path("portal/quotes", csrf_exempt(PortalQuoteListView.as_view()), name="portal-quote-list"),
    path("portal/quotes/<int:quote_id>", csrf_exempt(PortalQuoteDetailView.as_view()), name="portal-quote-detail"),
    path("portal/quotes/<int:quote_id>/document", csrf_exempt(PortalQuoteDocumentView.as_view()), name="portal-quote-document"),
    path("portal/quotes/<int:quote_id>/accept", csrf_exempt(PortalQuoteAcceptView.as_view()), name="portal-quote-accept"),
    path("portal/quotes/<int:quote_id>/reject", csrf_exempt(PortalQuoteDeclineView.as_view()), name="portal-quote-reject"),
    path("portal/quotes/<int:quote_id>/acknowledge", csrf_exempt(PortalQuoteAcknowledgeView.as_view()), name="portal-quote-acknowledge"),
    path("portal/quotes/<int:quote_id>/change-request", csrf_exempt(PortalQuoteChangeRequestView.as_view()), name="portal-quote-change-request"),
    path("portal/quotes/<int:quote_id>/events", csrf_exempt(PortalQuoteEventsView.as_view()), name="portal-quote-events"),

    # Phase 4: Campaigns
    path("portal/campaigns", csrf_exempt(PortalCampaignListView.as_view()), name="portal-campaign-list"),
    path("portal/campaigns/<int:campaign_id>", csrf_exempt(PortalCampaignDetailView.as_view()), name="portal-campaign-detail"),

    # Phase 4: Lead Self-Registration
    path("portal/leads/register", csrf_exempt(PortalLeadSelfRegisterView.as_view()), name="portal-lead-register"),

    # Phase 4: Referrals
    path("portal/referrals/codes", csrf_exempt(PortalReferralCodeListView.as_view()), name="portal-referral-code-list"),
    path("portal/referrals/track/<str:code>", csrf_exempt(PortalReferralTrackingView.as_view()), name="portal-referral-track"),

    # Phase 4: Momentum (Customer-Facing)
    path("portal/momentum/balance", csrf_exempt(PortalMomentumBalanceView.as_view()), name="portal-momentum-balance"),
    path("portal/momentum/history", csrf_exempt(PortalMomentumBalanceHistoryView.as_view()), name="portal-momentum-balance-history"),
]