from django.urls import path
from momentum import views

app_name = "momentum"

urlpatterns = [
    path("momentum/balance/<int:customer_id>/", views.MomentumBalanceView.as_view(), name="momentum_balance"),
    path("momentum/ledger/<int:customer_id>/", views.MomentumLedgerView.as_view(), name="momentum_ledger"),
    path("momentum/earn/", views.MomentumEarnView.as_view(), name="momentum_earn"),
    path("momentum/adjust/", views.MomentumAdjustView.as_view(), name="momentum_adjust"),
    path("momentum/rules/", views.MomentumRuleListView.as_view(), name="momentum_rule_list"),
    path("momentum/rules/<int:rule_id>/", views.MomentumRuleDetailView.as_view(), name="momentum_rule_detail"),
]
