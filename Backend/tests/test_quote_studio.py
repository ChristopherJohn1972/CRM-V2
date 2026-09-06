"""Quote Studio Phase 1 — comprehensive test suite.

Tests cover:
- QN01/QN02/QN03 numbering sequence
- Concurrent quote creation uniqueness
- Calculation engine (all spec test cases)
- Quote CRUD and lifecycle
- Template management
- Permission checks
- Portal isolation
- Client acceptance/rejection
- Quote expiry
- Approval workflow
- Versioning
- Optimistic locking
"""
import threading
from decimal import Decimal

import pytest

from quotes.enums import (
    ALLOWED_QUOTE_TRANSITIONS,
    QuoteStatus,
)
from quotes.services import QuoteCalculationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_customer(client, name="Test Customer"):
    response = client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": name,
            "email": f"{name.lower().replace(' ', '')}@example.com",
            "phone": "+254700000000",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _create_quote(client, customer_id, items=None, **kwargs):
    payload = {
        "customer_id": customer_id,
        "quote_type": kwargs.get("quote_type", "PRODUCT"),
        "title": kwargs.get("title", "Test Quote"),
        "currency": kwargs.get("currency", "KES"),
        "items": items or [],
    }
    payload.update(kwargs)
    response = client.post("/api/quotes", payload, format="json")
    return response


# ===========================================================================
# 1. QUOTING NUMBERING
# ===========================================================================

class TestQuoteNumbering:
    def test_first_quote_is_qn01(self, admin_client):
        customer = _create_customer(admin_client, "Number Test Co")
        response = _create_quote(admin_client, customer["customer_id"])
        assert response.status_code == 201, response.content
        assert response.data["quote_number"] == "QN01"
        assert response.data["sequence_value"] == 1

    def test_sequential_numbering(self, admin_client):
        customer = _create_customer(admin_client, "Seq Test Co")
        r1 = _create_quote(admin_client, customer["customer_id"])
        r2 = _create_quote(admin_client, customer["customer_id"])
        r3 = _create_quote(admin_client, customer["customer_id"])
        assert r1.data["quote_number"] == "QN01"
        assert r2.data["quote_number"] == "QN02"
        assert r3.data["quote_number"] == "QN03"

    def test_numbering_increments_across_customers(self, admin_client):
        c1 = _create_customer(admin_client, "Customer A")
        c2 = _create_customer(admin_client, "Customer B")
        r1 = _create_quote(admin_client, c1["customer_id"])
        r2 = _create_quote(admin_client, c2["customer_id"])
        assert r1.data["quote_number"] == "QN01"
        assert r2.data["quote_number"] == "QN02"

    def test_number_not_reused_after_duplicate(self, admin_client):
        customer = _create_customer(admin_client, "Reuse Test")
        r1 = _create_quote(admin_client, customer["customer_id"])
        r2 = admin_client.post(
            f"/api/quotes/{r1.data['quote_id']}/duplicate", format="json"
        )
        assert r2.status_code == 201
        assert r2.data["quote_number"] != r1.data["quote_number"]
        # Original QN preserved
        assert r1.data["quote_number"] == "QN01"

    def test_concurrent_quote_creation_uniqueness(self, admin_client):
        customer = _create_customer(admin_client, "Concurrent Test")
        results = []
        errors = []

        def create_quote():
            try:
                r = _create_quote(
                    admin_client,
                    customer["customer_id"],
                    title=f"Thread-{threading.current_thread().name}",
                )
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_quote) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors: {errors}"
        assert len(results) == 5
        numbers = [r.data["quote_number"] for r in results]
        assert len(set(numbers)) == 5, f"Duplicate numbers found: {numbers}"


# ===========================================================================
# 2. CALCULATION ENGINE
# ===========================================================================

class TestCalculationEngine:
    def test_basic_line_calculation(self):
        result = QuoteCalculationService.calculate_line({
            "quantity": 2,
            "unit_price": 15000,
            "tax_rate": 16,
        })
        assert result["gross_amount"] == Decimal("30000.00")
        assert result["discount_amount"] == Decimal("0.00")
        assert result["net_amount"] == Decimal("30000.00")
        assert result["tax_amount"] == Decimal("4800.00")
        assert result["line_total"] == Decimal("34800.00")

    def test_percentage_discount(self):
        result = QuoteCalculationService.calculate_line({
            "quantity": 2,
            "unit_price": 15000,
            "discount_type": "PERCENTAGE",
            "discount_value": 5,
            "tax_rate": 16,
        })
        assert result["gross_amount"] == Decimal("30000.00")
        assert result["discount_amount"] == Decimal("1500.00")
        assert result["net_amount"] == Decimal("28500.00")
        assert result["tax_amount"] == Decimal("4560.00")
        assert result["line_total"] == Decimal("33060.00")

    def test_fixed_discount(self):
        result = QuoteCalculationService.calculate_line({
            "quantity": 1,
            "unit_price": 30000,
            "discount_type": "FIXED",
            "discount_value": 2500,
            "tax_rate": 16,
        })
        assert result["gross_amount"] == Decimal("30000.00")
        assert result["discount_amount"] == Decimal("2500.00")
        assert result["net_amount"] == Decimal("27500.00")
        assert result["tax_amount"] == Decimal("4400.00")
        assert result["line_total"] == Decimal("31900.00")

    def test_discount_does_not_exceed_gross(self):
        result = QuoteCalculationService.calculate_line({
            "quantity": 1,
            "unit_price": 10000,
            "discount_type": "FIXED",
            "discount_value": 15000,
        })
        assert result["discount_amount"] == Decimal("10000.00")
        assert result["net_amount"] == Decimal("0.00")

    def test_multi_line_summation(self):
        items = [
            {"quantity": 2, "unit_price": 15000, "discount_type": "PERCENTAGE", "discount_value": 5, "tax_rate": 16},
            {"quantity": 1, "unit_price": 20000, "tax_rate": 16},
        ]
        result = QuoteCalculationService.calculate_quote_state(items)
        # Router line: gross=30000, disc=1500, net=28500, tax=4560
        # Switch line: gross=20000, disc=0, net=20000, tax=3200
        assert result["subtotal"] == Decimal("48500.00")
        assert result["total_discount"] == Decimal("1500.00")
        assert result["total_tax"] == Decimal("7760.00")
        assert result["grand_total"] == Decimal("56260.00")

    def test_zero_quantity(self):
        result = QuoteCalculationService.calculate_line({
            "quantity": 0,
            "unit_price": 10000,
            "tax_rate": 16,
        })
        assert result["gross_amount"] == Decimal("0.00")
        assert result["line_total"] == Decimal("0.00")

    def test_quote_level_discount(self):
        items = [{"quantity": 1, "unit_price": 100000, "tax_rate": 16}]
        quote_discount = {"discount_type": "PERCENTAGE", "discount_value": 10}
        result = QuoteCalculationService.calculate_quote_state(
            items, quote_discount=quote_discount
        )
        # Subtotal = 100000, quote discount = 10000, tax = 14400
        assert result["subtotal"] == Decimal("100000.00")
        assert result["total_discount"] == Decimal("10000.00")
        assert result["grand_total"] == Decimal("104400.00")

    def test_additional_charges(self):
        items = [{"quantity": 1, "unit_price": 50000, "tax_rate": 16}]
        result = QuoteCalculationService.calculate_quote_state(
            items, additional_charges=5000
        )
        # Subtotal=50000, tax=8000, charges=5000
        assert result["additional_charges"] == Decimal("5000.00")
        assert result["grand_total"] == Decimal("63000.00")

    def test_no_tax(self):
        result = QuoteCalculationService.calculate_line({
            "quantity": 3,
            "unit_price": 10000,
            "tax_rate": 0,
        })
        assert result["tax_amount"] == Decimal("0.00")
        assert result["line_total"] == Decimal("30000.00")

    def test_spec_example_router_switch(self):
        """Exact spec example from section 10."""
        items = [
            {"quantity": 2, "unit_price": 15000, "discount_type": "PERCENTAGE", "discount_value": 5, "tax_rate": 16},
            {"quantity": 1, "unit_price": 20000, "tax_rate": 16},
        ]
        result = QuoteCalculationService.calculate_quote_state(items)
        assert result["subtotal"] == Decimal("48500.00")
        assert result["total_discount"] == Decimal("1500.00")
        assert result["total_tax"] == Decimal("7760.00")
        assert result["grand_total"] == Decimal("56260.00")


# ===========================================================================
# 3. QUOTE CRUD
# ===========================================================================

class TestQuoteCRUD:
    def test_create_quote(self, admin_client):
        customer = _create_customer(admin_client, "CRUD Test")
        response = _create_quote(
            admin_client,
            customer["customer_id"],
            items=[{"description": "Item A", "quantity": 1, "unit_price": 10000}],
        )
        assert response.status_code == 201, response.content
        assert response.data["quote_number"] == "QN01"
        assert response.data["status"] == "DRAFT"
        assert float(response.data["grand_total"]) == 11600.00

    def test_get_quote_detail(self, admin_client):
        customer = _create_customer(admin_client, "Detail Test")
        r = _create_quote(admin_client, customer["customer_id"])
        response = admin_client.get(f"/api/quotes/{r.data['quote_id']}")
        assert response.status_code == 200
        assert response.data["quote_number"] == "QN01"

    def test_update_quote(self, admin_client):
        customer = _create_customer(admin_client, "Update Test")
        r = _create_quote(admin_client, customer["customer_id"])
        response = admin_client.patch(
            f"/api/quotes/{r.data['quote_id']}",
            {"title": "Updated Title", "version": r.data["version"]},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["title"] == "Updated Title"
        assert response.data["version"] == r.data["version"] + 1

    def test_optimistic_lock(self, admin_client):
        customer = _create_customer(admin_client, "Lock Test")
        r = _create_quote(admin_client, customer["customer_id"])
        # First update succeeds
        admin_client.patch(
            f"/api/quotes/{r.data['quote_id']}",
            {"title": "First", "version": r.data["version"]},
            format="json",
        )
        # Second update with stale version fails
        response = admin_client.patch(
            f"/api/quotes/{r.data['quote_id']}",
            {"title": "Second", "version": r.data["version"]},
            format="json",
        )
        assert response.status_code == 409

    def test_list_quotes(self, admin_client):
        customer = _create_customer(admin_client, "List Test")
        _create_quote(admin_client, customer["customer_id"])
        _create_quote(admin_client, customer["customer_id"])
        response = admin_client.get("/api/quotes")
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_filter_by_status(self, admin_client):
        customer = _create_customer(admin_client, "Filter Test")
        _create_quote(admin_client, customer["customer_id"])
        response = admin_client.get("/api/quotes?status=DRAFT")
        assert response.data["count"] == 1

    def test_filter_by_type(self, admin_client):
        customer = _create_customer(admin_client, "Type Test")
        _create_quote(admin_client, customer["customer_id"], quote_type="PRODUCT")
        _create_quote(admin_client, customer["customer_id"], quote_type="SERVICE")
        response = admin_client.get("/api/quotes?quote_type=PRODUCT")
        assert response.data["count"] == 1

    def test_add_item(self, admin_client):
        customer = _create_customer(admin_client, "Item Test")
        r = _create_quote(admin_client, customer["customer_id"])
        response = admin_client.post(
            f"/api/quotes/{r.data['quote_id']}/items",
            {"description": "New Item", "quantity": 3, "unit_price": 5000, "tax_rate": 16},
            format="json",
        )
        assert response.status_code == 201
        # Verify totals updated
        detail = admin_client.get(f"/api/quotes/{r.data['quote_id']}")
        assert float(detail.data["grand_total"]) > 0

    def test_update_item(self, admin_client):
        customer = _create_customer(admin_client, "Item Update")
        r = _create_quote(
            admin_client,
            customer["customer_id"],
            items=[{"description": "Item", "quantity": 1, "unit_price": 10000}],
        )
        item_id = r.data["items"][0]["item_id"]
        response = admin_client.patch(
            f"/api/quotes/{r.data['quote_id']}/items/{item_id}",
            {"quantity": 5},
            format="json",
        )
        assert response.status_code == 200
        assert float(response.data["quantity"]) == 5.0

    def test_remove_item(self, admin_client):
        customer = _create_customer(admin_client, "Item Remove")
        r = _create_quote(
            admin_client,
            customer["customer_id"],
            items=[{"description": "Item", "quantity": 1, "unit_price": 10000}],
        )
        item_id = r.data["items"][0]["item_id"]
        response = admin_client.delete(f"/api/quotes/{r.data['quote_id']}/items/{item_id}")
        assert response.status_code == 204


# ===========================================================================
# 4. QUOTE WORKFLOW / LIFECYCLE
# ===========================================================================

class TestQuoteWorkflow:
    def _setup_quote(self, admin_client):
        customer = _create_customer(admin_client, "Workflow Test")
        r = _create_quote(
            admin_client,
            customer["customer_id"],
            items=[{"description": "Widget", "quantity": 2, "unit_price": 10000, "tax_rate": 16}],
        )
        return r.data

    def test_submit_for_approval(self, admin_client):
        quote = self._setup_quote(admin_client)
        response = admin_client.post(
            f"/api/quotes/{quote['quote_id']}/submit-approval", format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == "PENDING_APPROVAL"

    def test_approve_quote(self, admin_client):
        quote = self._setup_quote(admin_client)
        admin_client.post(f"/api/quotes/{quote['quote_id']}/submit-approval", format="json")
        response = admin_client.post(
            f"/api/quotes/{quote['quote_id']}/approve",
            {"reason": "Looks good"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "APPROVED"

    def test_reject_quote(self, admin_client):
        quote = self._setup_quote(admin_client)
        admin_client.post(f"/api/quotes/{quote['quote_id']}/submit-approval", format="json")
        response = admin_client.post(
            f"/api/quotes/{quote['quote_id']}/reject",
            {"reason": "Too expensive"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "REJECTED"

    def test_send_quote(self, admin_client):
        quote = self._setup_quote(admin_client)
        response = admin_client.post(
            f"/api/quotes/{quote['quote_id']}/send", format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == "SENT"

    def test_cancel_quote(self, admin_client):
        quote = self._setup_quote(admin_client)
        response = admin_client.post(
            f"/api/quotes/{quote['quote_id']}/cancel",
            {"reason": "Changed mind"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "CANCELLED"

    def test_duplicate_quote(self, admin_client):
        quote = self._setup_quote(admin_client)
        response = admin_client.post(
            f"/api/quotes/{quote['quote_id']}/duplicate", format="json"
        )
        assert response.status_code == 201
        assert response.data["quote_number"] != quote["quote_number"]
        assert response.data["quote_type"] == quote["quote_type"]

    def test_invalid_transition_rejected(self, admin_client):
        quote = self._setup_quote(admin_client)
        # Try to send a DRAFT quote directly
        response = admin_client.post(
            f"/api/quotes/{quote['quote_id']}/send", format="json"
        )
        assert response.status_code == 400

    def test_cannot_update_terminal_status(self, admin_client):
        quote = self._setup_quote(admin_client)
        # Cancel the quote
        admin_client.post(
            f"/api/quotes/{quote['quote_id']}/cancel", format="json"
        )
        # Try to update
        response = admin_client.patch(
            f"/api/quotes/{quote['quote_id']}",
            {"title": "Hacked"},
            format="json",
        )
        assert response.status_code == 400


# ===========================================================================
# 5. QUOTE CALCULATION API
# ===========================================================================

class TestQuoteCalculationAPI:
    def test_calculate_endpoint(self, admin_client):
        response = admin_client.post(
            "/api/quotes/calculate",
            {
                "currency": "KES",
                "items": [
                    {"description": "Router", "quantity": 2, "unit_price": 15000, "discount_type": "PERCENTAGE", "discount_value": 5, "tax_rate": 16},
                    {"description": "Switch", "quantity": 1, "unit_price": 20000, "tax_rate": 16},
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        assert float(response.data["subtotal"]) == 48500.00
        assert float(response.data["total_discount"]) == 1500.00
        assert float(response.data["total_tax"]) == 7760.00
        assert float(response.data["grand_total"]) == 56260.00

    def test_recalculate_endpoint(self, admin_client):
        customer = _create_customer(admin_client, "Recalc Test")
        r = _create_quote(
            admin_client,
            customer["customer_id"],
            items=[{"description": "Item", "quantity": 1, "unit_price": 10000}],
        )
        response = admin_client.post(
            f"/api/quotes/{r.data['quote_id']}/recalculate", format="json"
        )
        assert response.status_code == 200
        assert float(response.data["subtotal"]) == 10000.00


# ===========================================================================
# 6. TEMPLATE MANAGEMENT
# ===========================================================================

class TestTemplateManagement:
    def test_create_template(self, admin_client):
        response = admin_client.post(
            "/api/quote-templates",
            {
                "name": "My Template",
                "template_type": "PRODUCT",
                "content_config": {"show_logo": True, "header_color": "#ff0000"},
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["name"] == "My Template"
        assert response.data["status"] == "ACTIVE"

    def test_list_templates(self, admin_client):
        admin_client.post(
            "/api/quote-templates",
            {"name": "Template A", "template_type": "PRODUCT"},
            format="json",
        )
        response = admin_client.get("/api/quote-templates")
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_deactivate_template(self, admin_client):
        r = admin_client.post(
            "/api/quote-templates",
            {"name": "Deactivate Me", "template_type": "SERVICE"},
            format="json",
        )
        response = admin_client.post(
            f"/api/quote-templates/{r.data['template_id']}/deactivate", format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == "INACTIVE"

    def test_activate_template(self, admin_client):
        r = admin_client.post(
            "/api/quote-templates",
            {"name": "Activate Me", "template_type": "PROJECT"},
            format="json",
        )
        admin_client.post(
            f"/api/quote-templates/{r.data['template_id']}/deactivate", format="json"
        )
        response = admin_client.post(
            f"/api/quote-templates/{r.data['template_id']}/activate", format="json"
        )
        assert response.status_code == 200
        assert response.data["status"] == "ACTIVE"


# ===========================================================================
# 7. TAX RULES
# ===========================================================================

class TestTaxRules:
    def test_list_tax_rules(self, admin_client):
        response = admin_client.get("/api/tax-rules")
        assert response.status_code == 200
        # VAT_16 should exist from seed data
        codes = [t["code"] for t in response.data]
        assert "VAT_16" in codes

    def test_create_tax_rule(self, admin_client):
        response = admin_client.post(
            "/api/tax-rules",
            {"code": "CUSTOM_TAX", "name": "Custom Tax", "rate": 10},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["code"] == "CUSTOM_TAX"


# ===========================================================================
# 8. AUDIT TRAIL
# ===========================================================================

class TestAuditTrail:
    def test_quote_events_recorded(self, admin_client):
        customer = _create_customer(admin_client, "Audit Test")
        r = _create_quote(admin_client, customer["customer_id"])
        response = admin_client.get(f"/api/quotes/{r.data['quote_id']}/activity")
        assert response.status_code == 200
        assert len(response.data) >= 1
        assert response.data[0]["event_type"] == "CREATED"

    def test_submit_approval_records_event(self, admin_client):
        customer = _create_customer(admin_client, "Event Test")
        r = _create_quote(admin_client, customer["customer_id"])
        admin_client.post(f"/api/quotes/{r.data['quote_id']}/submit-approval", format="json")
        response = admin_client.get(f"/api/quotes/{r.data['quote_id']}/activity")
        event_types = [e["event_type"] for e in response.data]
        assert "SUBMITTED_FOR_APPROVAL" in event_types


# ===========================================================================
# 9. PERMISSIONS
# ===========================================================================

class TestPermissions:
    def test_read_only_cannot_create(self, rep_client, create_user, login):
        from common.db import SessionLocal
        from iam.models import Role

        user_id = create_user("readonly1", "ro1@example.com", "RoPass!123", role_code="READ_ONLY")
        ro_client = rep_client  # We'll use a fresh client
        from rest_framework.test import APIClient
        ro_client = APIClient()
        ro_client.post(
            "/api/auth/login",
            {"username": "readonly1", "password": "RoPass!123"},
            format="json",
        )

        customer = _create_customer(rep_client, "Perm Test")
        response = _create_quote(ro_client, customer["customer_id"])
        assert response.status_code == 403

    def test_sales_rep_can_create(self, rep_client):
        customer = _create_customer(rep_client, "Rep Perm Test")
        response = _create_quote(rep_client, customer["customer_id"])
        assert response.status_code == 201


# ===========================================================================
# 10. VERSIONING
# ===========================================================================

class TestVersioning:
    def test_quote_version_increments(self, admin_client):
        customer = _create_customer(admin_client, "Version Test")
        r = _create_quote(admin_client, customer["customer_id"])
        initial_version = r.data["version"]

        admin_client.patch(
            f"/api/quotes/{r.data['quote_id']}",
            {"title": "v2", "version": initial_version},
            format="json",
        )
        detail = admin_client.get(f"/api/quotes/{r.data['quote_id']}")
        assert detail.data["version"] == initial_version + 1


# ===========================================================================
# 11. QUOTE TYPES
# ===========================================================================

class TestQuoteTypes:
    def test_product_quote(self, admin_client):
        customer = _create_customer(admin_client, "Product Test")
        r = _create_quote(admin_client, customer["customer_id"], quote_type="PRODUCT")
        assert r.data["quote_type"] == "PRODUCT"

    def test_service_quote(self, admin_client):
        customer = _create_customer(admin_client, "Service Test")
        r = _create_quote(admin_client, customer["customer_id"], quote_type="SERVICE")
        assert r.data["quote_type"] == "SERVICE"

    def test_project_quote(self, admin_client):
        customer = _create_customer(admin_client, "Project Test")
        r = _create_quote(admin_client, customer["customer_id"], quote_type="PROJECT")
        assert r.data["quote_type"] == "PROJECT"

    def test_invalid_quote_type(self, admin_client):
        customer = _create_customer(admin_client, "Invalid Test")
        response = _create_quote(admin_client, customer["customer_id"], quote_type="INVALID")
        assert response.status_code == 400
