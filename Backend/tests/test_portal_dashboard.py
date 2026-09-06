import datetime

import sqlalchemy as sa

from common.db import SessionLocal
from portal.models import Payment


def _create_customer(admin_client, name="Dash Co"):
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


def _create_portal_user(admin_client, customer_id, username="dash.user", email="dash@example.com"):
    response = admin_client.post(
        "/api/portal/users",
        {
            "username": username,
            "email": email,
            "first_name": "Dash",
            "last_name": "User",
            "customers": [{"customer_id": customer_id, "relationship_type": "OWNER", "is_primary": True}],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _setup_portal_user(admin_client, client, portal_user):
    for perm in ["portal.customer.view", "portal.payment.view", "portal.momentum.view", "portal.notification.view"]:
        admin_client.post(
            f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
            {"permission_code": perm, "effect": "ALLOW"},
            format="json",
        )
    temp = portal_user["temp_password"]
    login = client.post("/api/portal/auth/login", {"username": portal_user["username"], "password": temp}, format="json")
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
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")


def _seed_payments(session, customer_id, payments_data):
    for amount, ref in payments_data:
        p = Payment(
            customer_id=customer_id,
            amount=amount,
            payment_date=datetime.date(2026, 8, 1),
            reference=ref,
            status="CONFIRMED",
            payment_method="MPESA",
        )
        session.add(p)
    session.flush()


def test_dashboard_basic(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], [
        (25000.0, "PAY-D1"),
        (10000.0, "PAY-D2"),
    ])
    db.commit()

    r = client.get("/api/portal/dashboard")
    assert r.status_code == 200, r.content
    assert len(r.data["customers"]) == 1
    assert r.data["customers"][0]["customer_number"] == customer["account_number"]
    assert r.data["customers"][0]["payments_count"] == 2
    assert r.data["total_momentum"] == 35


def test_dashboard_multiple_customers(admin_client, client, db):
    c1 = _create_customer(admin_client, "Dash Multi 1")
    c2 = _create_customer(admin_client, "Dash Multi 2")

    p = _create_portal_user(admin_client, c1["customer_id"], "multi.user", "multi@example.com")
    admin_client.post(
        f"/api/portal/users/{p['portal_user_id']}/customers",
        {"customer_id": c2["customer_id"], "relationship_type": "OWNER"},
        format="json",
    )
    _setup_portal_user(admin_client, client, p)

    _seed_payments(db, c1["customer_id"], [(100000.0, "PAY-M1")])
    _seed_payments(db, c2["customer_id"], [(200000.0, "PAY-M2")])
    db.commit()

    r = client.get("/api/portal/dashboard")
    assert r.status_code == 200
    assert len(r.data["customers"]) == 2
    assert r.data["total_momentum"] == 300


def test_dashboard_empty_customers(admin_client, client, db):
    """Portal user with no linked customers gets empty dashboard."""
    p = _create_portal_user.__wrapped__ if hasattr(_create_portal_user, "__wrapped__") else None

    response = admin_client.post(
        "/api/portal/users",
        {
            "username": "empty.dash",
            "email": "empty.dash@example.com",
            "first_name": "Empty",
            "last_name": "Dash",
        },
        format="json",
    )
    assert response.status_code == 201
    portal_user = response.data

    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "ALLOW"},
        format="json",
    )
    temp = portal_user["temp_password"]
    login = client.post("/api/portal/auth/login", {"username": portal_user["username"], "password": temp}, format="json")
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
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    r = client.get("/api/portal/dashboard")
    assert r.status_code == 200
    assert r.data["customers"] == []
    assert r.data["total_momentum"] == 0
