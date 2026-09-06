import datetime
import random
import string

import sqlalchemy as sa

from common.db import SessionLocal
from portal.models import Payment
from portal.services import MomentumService


def _create_customer_orm(session, name="Momentum Co"):
    """Create a customer directly through the ORM for unit tests."""
    from clients.models import Customer

    account = "C" + "".join(random.choices(string.digits, k=4))
    customer = Customer(
        customer_number=account,
        customer_type="BUSINESS",
        legal_name=name,
        display_name=name,
        email=f"{name.lower().replace(' ', '')}@example.com",
        phone="+254799000001",
    )
    session.add(customer)
    session.flush()
    return customer


def _create_customer(admin_client, name="Momentum Co"):
    response = admin_client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": name,
            "display_name": name,
            "email": f"{name.lower().replace(' ', '')}@example.com",
            "phone": "+254799000001",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _create_portal_user(admin_client, customer_id, username="mom.user", email="mom@example.com"):
    response = admin_client.post(
        "/api/portal/users",
        {
            "username": username,
            "email": email,
            "first_name": "Mom",
            "last_name": "User",
            "customers": [{"customer_id": customer_id, "relationship_type": "OWNER", "is_primary": True}],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _setup_portal_user(admin_client, client, portal_user, customer_id):
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "ALLOW"},
        format="json",
    )
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.payment.view", "effect": "ALLOW"},
        format="json",
    )
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.momentum.view", "effect": "ALLOW"},
        format="json",
    )
    temp = portal_user["temp_password"]
    login = client.post("/api/portal/auth/login", {"username": portal_user["username"], "password": temp}, format="json")
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
    client.post(
        "/api/portal/auth/change-password",
        {"current_password": temp, "new_password": "Str0ng!PortalPass"},
        format="json",
    )
    login = client.post(
        "/api/portal/auth/login",
        {"username": portal_user["username"], "password": "Str0ng!PortalPass"},
        format="json",
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")


def _seed_payments(session, customer_id, payments_data):
    for i, (amount, ref, status) in enumerate(payments_data):
        p = Payment(
            customer_id=customer_id,
            amount=amount,
            payment_date=datetime.date(2026, 1, 15) + datetime.timedelta(days=i * 30),
            reference=ref,
            status=status,
            payment_method="MPESA",
        )
        session.add(p)
    session.flush()


# --- Momentum formula tests (spec section 11, 28, 31, 32) ---


def test_momentum_zero_payments(db):
    """No payments = 0 momentum."""
    customer = _create_customer_orm(db, "Zero Co")
    momentum = MomentumService.calculate_momentum(db, customer.customer_id)
    assert momentum == 0


def test_momentum_formula_exact_1000(db):
    customer = _create_customer_orm(db, "Exact Co")
    _seed_payments(db, customer.customer_id, [
        (1000.0, "PAY-001", "CONFIRMED"),
    ])
    db.commit()
    momentum = MomentumService.calculate_momentum(db, customer.customer_id)
    assert momentum == 1


def test_momentum_formula_below_1000(db):
    customer = _create_customer_orm(db, "Below Co")
    _seed_payments(db, customer.customer_id, [
        (999.0, "PAY-002", "CONFIRMED"),
    ])
    db.commit()
    momentum = MomentumService.calculate_momentum(db, customer.customer_id)
    assert momentum == 0


def test_momentum_formula_15500(db):
    """Spec section 28: 15,500 -> 15 momentum, 500 remainder."""
    customer = _create_customer_orm(db, "Spec28 Co")
    _seed_payments(db, customer.customer_id, [
        (15500.0, "PAY-003", "CONFIRMED"),
    ])
    db.commit()
    summary = MomentumService.get_summary(db, customer.customer_id)
    assert summary["momentum"] == 15
    assert summary["remainder"] == 500.0
    assert summary["next_momentum_required"] == 500.0


def test_momentum_formula_100000(db):
    """Spec section 32: 100,000 -> 100 momentum."""
    customer = _create_customer_orm(db, "Spec32 Co")
    _seed_payments(db, customer.customer_id, [
        (25000.0, "PAY-P1", "CONFIRMED"),
        (10000.0, "PAY-P2", "CONFIRMED"),
        (7500.0, "PAY-P3", "CONFIRMED"),
        (15000.0, "PAY-P4", "CONFIRMED"),
        (42500.0, "PAY-P5", "CONFIRMED"),
    ])
    db.commit()
    summary = MomentumService.get_summary(db, customer.customer_id)
    assert summary["total_qualifying"] == 100000.0
    assert summary["momentum"] == 100


def test_momentum_formula_345700(db):
    """Spec section 28: 345,700 -> 345 momentum, 700 remainder, 300 to next."""
    customer = _create_customer_orm(db, "Spec28B Co")
    _seed_payments(db, customer.customer_id, [
        (345700.0, "PAY-004", "CONFIRMED"),
    ])
    db.commit()
    summary = MomentumService.get_summary(db, customer.customer_id)
    assert summary["momentum"] == 345
    assert summary["remainder"] == 700.0
    assert summary["next_momentum_required"] == 300.0


def test_momentum_only_confirmed_payments_count(db):
    """PENDING and FAILED payments do not count toward momentum."""
    customer = _create_customer_orm(db, "Status Co")
    _seed_payments(db, customer.customer_id, [
        (5000.0, "PAY-S1", "CONFIRMED"),
        (3000.0, "PAY-S2", "PENDING"),
        (2000.0, "PAY-S3", "FAILED"),
        (1000.0, "PAY-S4", "CANCELLED"),
    ])
    db.commit()
    summary = MomentumService.get_summary(db, customer.customer_id)
    assert summary["total_qualifying"] == 5000.0
    assert summary["momentum"] == 5


def test_momentum_never_expires(db):
    """Momentum never expires (spec section 14)."""
    customer = _create_customer_orm(db, "Expire Co")
    _seed_payments(db, customer.customer_id, [
        (50000.0, "PAY-E1", "CONFIRMED"),
    ])
    db.commit()
    summary = MomentumService.get_summary(db, customer.customer_id)
    assert summary["never_expires"] is True


def test_momentum_payment_filtering_by_date(db):
    customer = _create_customer_orm(db, "Filter Co")
    _seed_payments(db, customer.customer_id, [
        (10000.0, "PAY-F1", "CONFIRMED"),
        (5000.0, "PAY-F2", "CONFIRMED"),
    ])
    db.commit()
    total = MomentumService.get_qualifying_total(
        db, customer.customer_id,
        date_from=datetime.date(2026, 2, 1),
        date_to=datetime.date(2026, 3, 1),
    )
    assert total == 5000.0


def test_momentum_api_endpoint(admin_client, client, db):
    """GET /api/portal/customers/{id}/momentum returns correct data."""
    customer = _create_customer(admin_client, "MomentumAPI Co")
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user, customer["customer_id"])

    _seed_payments(db, customer["customer_id"], [
        (25000.0, "PAY-A1", "CONFIRMED"),
        (10000.0, "PAY-A2", "CONFIRMED"),
    ])
    db.commit()

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/momentum")
    assert r.status_code == 200, r.content
    assert r.data["momentum"] == 35
    assert r.data["remainder"] == 0.0
    assert r.data["never_expires"] is True
