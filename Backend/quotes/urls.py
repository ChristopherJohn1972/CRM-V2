from django.urls import path

from quotes.views import (
    QuoteActivityView,
    QuoteApprovalsListView,
    QuoteApproveView,
    QuoteCalculationView,
    QuoteCancelView,
    QuoteConvertToOrderView,
    QuoteDetailView,
    QuoteDocumentsListView,
    QuoteDuplicateView,
    QuoteItemDetailView,
    QuoteItemListView,
    QuoteListView,
    QuotePdfView,
    QuotePreviewView,
    QuoteRecalculateView,
    QuoteRejectView,
    QuoteSendView,
    QuoteSubmitApprovalView,
    QuoteTemplateActivateView,
    QuoteTemplateDeactivateView,
    QuoteTemplateDetailView,
    QuoteTemplateListView,
    TaxRuleListView,
)

urlpatterns = [
    # Quotes CRUD
    path("quotes", QuoteListView.as_view(), name="quote-list"),
    path("quotes/<int:quote_id>", QuoteDetailView.as_view(), name="quote-detail"),

    # Quote items
    path("quotes/<int:quote_id>/items", QuoteItemListView.as_view(), name="quote-items"),
    path(
        "quotes/<int:quote_id>/items/<int:item_id>",
        QuoteItemDetailView.as_view(),
        name="quote-item-detail",
    ),

    # Calculation
    path("quotes/calculate", QuoteCalculationView.as_view(), name="quote-calculate"),
    path("quotes/<int:quote_id>/recalculate", QuoteRecalculateView.as_view(), name="quote-recalculate"),

    # Workflow actions
    path("quotes/<int:quote_id>/submit-approval", QuoteSubmitApprovalView.as_view(), name="quote-submit-approval"),
    path("quotes/<int:quote_id>/approve", QuoteApproveView.as_view(), name="quote-approve"),
    path("quotes/<int:quote_id>/reject", QuoteRejectView.as_view(), name="quote-reject"),
    path("quotes/<int:quote_id>/send", QuoteSendView.as_view(), name="quote-send"),
    path("quotes/<int:quote_id>/cancel", QuoteCancelView.as_view(), name="quote-cancel"),
    path("quotes/<int:quote_id>/duplicate", QuoteDuplicateView.as_view(), name="quote-duplicate"),

    # Documents / preview
    path("quotes/<int:quote_id>/preview", QuotePreviewView.as_view(), name="quote-preview"),
    path("quotes/<int:quote_id>/pdf", QuotePdfView.as_view(), name="quote-pdf"),
    path("quotes/<int:quote_id>/activity", QuoteActivityView.as_view(), name="quote-activity"),
    path("quotes/<int:quote_id>/approvals", QuoteApprovalsListView.as_view(), name="quote-approvals"),
    path("quotes/<int:quote_id>/documents", QuoteDocumentsListView.as_view(), name="quote-documents"),
    path("quotes/<int:quote_id>/convert-to-order", QuoteConvertToOrderView.as_view(), name="quote-convert-to-order"),

    # Templates
    path("quote-templates", QuoteTemplateListView.as_view(), name="quote-template-list"),
    path("quote-templates/<int:template_id>", QuoteTemplateDetailView.as_view(), name="quote-template-detail"),
    path("quote-templates/<int:template_id>/activate", QuoteTemplateActivateView.as_view(), name="quote-template-activate"),
    path("quote-templates/<int:template_id>/deactivate", QuoteTemplateDeactivateView.as_view(), name="quote-template-deactivate"),

    # Tax rules
    path("tax-rules", TaxRuleListView.as_view(), name="tax-rule-list"),
]
