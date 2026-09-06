import datetime

import sqlalchemy as sa

from common.db import SessionLocal
from portal.models import Complaint, Payment
from portal.services import ComplaintService, MomentumService


def _create_customer(admin_client, name="Complaint Co"):
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


def _create_portal_user(admin_client, customer_id, username="comp.user", email="comp@example.com"):
    response = admin_client.post(
        "/api/portal/users",
        {
            "username": username,
            "email": email,
            "first_name": "Comp",
            "last_name": "User",
            "customers": [{"customer_id": customer_id, "relationship_type": "OWNER", "is_primary": True}],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _setup_portal_user(admin_client, client, portal_user):
    for perm in ["portal.customer.view", "portal.complaint.create", "portal.complaint.view", "portal.complaint.respond"]:
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


def test_create_complaint(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/complaints",
        {
            "subject": "Service quality issue",
            "category": "Service",
            "description": "The service was below expectations",
            "priority": "HIGH",
            "preferred_contact": "EMAIL",
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    assert r.data["complaint_number"].startswith("CMP-")
    assert r.data["status"] == "SUBMITTED"
    assert r.data["subject"] == "Service quality issue"


def test_list_complaints(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    for i in range(3):
        client.post(
            f"/api/portal/customers/{customer['customer_id']}/complaints",
            {"subject": f"Issue {i}", "priority": "MEDIUM"},
            format="json",
        )

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/complaints")
    assert r.status_code == 200
    assert len(r.data["results"]) == 3


def test_complaint_detail(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    create_r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/complaints",
        {"subject": "Detail test", "priority": "LOW"},
        format="json",
    )
    complaint_id = create_r.data["complaint_id"]

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/complaints/{complaint_id}")
    assert r.status_code == 200
    assert r.data["subject"] == "Detail test"
    assert r.data["priority"] == "LOW"


def test_add_complaint_message(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    create_r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/complaints",
        {"subject": "Message test", "priority": "MEDIUM"},
        format="json",
    )
    complaint_id = create_r.data["complaint_id"]

    r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/complaints/{complaint_id}/messages",
        {"message": "Additional information about the issue"},
        format="json",
    )
    assert r.status_code == 201, r.content
    assert r.data["message"] == "Additional information about the issue"
    assert r.data["sender_type"] == "PORTAL_USER"


def test_complaint_timeline(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    create_r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/complaints",
        {"subject": "Timeline test", "priority": "HIGH"},
        format="json",
    )
    complaint_id = create_r.data["complaint_id"]

    client.post(
        f"/api/portal/customers/{customer['customer_id']}/complaints/{complaint_id}/messages",
        {"message": "First follow-up"},
        format="json",
    )

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/complaints/{complaint_id}/timeline")
    assert r.status_code == 200
    timeline = r.data["timeline"]
    assert len(timeline) >= 2
    assert timeline[0]["type"] == "status_change"
    assert timeline[0]["new_status"] == "SUBMITTED"
    assert timeline[1]["type"] == "message"


def test_complaint_isolation_between_customers(admin_client, client, db):
    """Customer A cannot see Customer B's complaints."""
    c1 = _create_customer(admin_client, "C1 Complaints")
    c2 = _create_customer(admin_client, "C2 Complaints")
    p1 = _create_portal_user(admin_client, c1["customer_id"], "user.c1", "c1@example.com")
    _setup_portal_user(admin_client, client, p1)

    client.post(
        f"/api/portal/customers/{c1['customer_id']}/complaints",
        {"subject": "C1 complaint"},
        format="json",
    )

    r = client.get(f"/api/portal/customers/{c2['customer_id']}/complaints")
    assert r.status_code == 403


def test_complaint_requires_permission(admin_client, client, db):
    customer = _create_customer(admin_client, "NoPerm Co")
    p = _create_portal_user(admin_client, customer["customer_id"], "noperm.user", "noperm@example.com")
    admin_client.post(
        f"/api/portal/users/{p['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "ALLOW"},
        format="json",
    )
    temp = p["temp_password"]
    login = client.post("/api/portal/auth/login", {"username": p["username"], "password": temp}, format="json")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
    client.post(
        "/api/portal/auth/change-password",
        {"current_password": temp, "new_password": "Str0ng!PortalPass"},
        format="json",
    )
    login = client.post(
        "/api/portal/auth/login", {"username": p["username"], "password": "Str0ng!PortalPass"}, format="json"
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/complaints",
        {"subject": "Should fail"},
        format="json",
    )
    assert r.status_code == 403


def test_complaint_number_format(db):
    """Complaint numbers follow CMP-{year}-{6-digit} format."""
    from clients.models import Customer
    import random
    import string

    account = "C" + "".join(random.choices(string.digits, k=4))
    customer = Customer(
        customer_number=account,
        customer_type="BUSINESS",
        legal_name="Format Co",
        display_name="Format Co",
        email="formatco@example.com",
        phone="+254799000001",
    )
    db.add(customer)
    db.flush()
    c = ComplaintService.create(db, customer_id=customer.customer_id, subject="Test")
    year = datetime.datetime.utcnow().year
    assert c.complaint_number.startswith(f"CMP-{year}-")
    assert len(c.complaint_number.split("-")[-1]) == 6
