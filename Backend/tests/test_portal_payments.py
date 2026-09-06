import datetime

import sqlalchemy as sa

from common.db import SessionLocal
from portal.models import Payment, PaymentReceipt
from portal.services import MomentumService


def _create_customer(admin_client, name="Payment Co"):
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


def _create_portal_user(admin_client, customer_id, username="pay.user", email="pay@example.com"):
    response = admin_client.post(
        "/api/portal/users",
        {
            "username": username,
            "email": email,
            "first_name": "Pay",
            "last_name": "User",
            "customers": [{"customer_id": customer_id, "relationship_type": "OWNER", "is_primary": True}],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _setup_portal_user(admin_client, client, portal_user):
    for perm in ["portal.customer.view", "portal.payment.view", "portal.momentum.view"]:
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
    for i, (amount, ref, st, pdate) in enumerate(payments_data):
        p = Payment(
            customer_id=customer_id,
            amount=amount,
            payment_date=pdate,
            reference=ref,
            status=st,
            payment_method="MPESA",
        )
        session.add(p)
    session.flush()


def test_list_payments(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], [
        (10000.0, "PAY-L1", "CONFIRMED", datetime.date(2026, 8, 24)),
        (5000.0, "PAY-L2", "CONFIRMED", datetime.date(2026, 8, 18)),
        (2000.0, "PAY-L3", "PENDING", datetime.date(2026, 8, 10)),
    ])
    db.commit()

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/payments")
    assert r.status_code == 200, r.content
    assert r.data["count"] == 3
    assert r.data["results"][0]["reference"] == "PAY-L1"


def test_filter_payments_by_status(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], [
        (10000.0, "PAY-FS1", "CONFIRMED", datetime.date(2026, 8, 1)),
        (5000.0, "PAY-FS2", "PENDING", datetime.date(2026, 8, 2)),
        (3000.0, "PAY-FS3", "CONFIRMED", datetime.date(2026, 8, 3)),
    ])
    db.commit()

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/payments?status=CONFIRMED")
    assert r.status_code == 200
    assert r.data["count"] == 2


def test_filter_payments_by_date(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], [
        (10000.0, "PAY-FD1", "CONFIRMED", datetime.date(2026, 1, 15)),
        (5000.0, "PAY-FD2", "CONFIRMED", datetime.date(2026, 6, 15)),
        (3000.0, "PAY-FD3", "CONFIRMED", datetime.date(2026, 8, 15)),
    ])
    db.commit()

    r = client.get(
        f"/api/portal/customers/{customer['customer_id']}/payments?date_from=2026-06-01&date_to=2026-08-31"
    )
    assert r.status_code == 200
    assert r.data["count"] == 2


def test_payment_momentum_summary_in_response(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], [
        (25000.0, "PAY-MS1", "CONFIRMED", datetime.date(2026, 8, 1)),
        (10000.0, "PAY-MS2", "CONFIRMED", datetime.date(2026, 8, 2)),
    ])
    db.commit()

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/payments")
    assert r.status_code == 200
    assert r.data["total_qualifying"] == 35000.0
    assert r.data["momentum"] == 35


def test_payment_detail(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], [
        (10000.0, "PAY-D1", "CONFIRMED", datetime.date(2026, 8, 24)),
    ])
    db.commit()

    payment = db.execute(
        sa.select(Payment).where(Payment.reference == "PAY-D1")
    ).scalar_one()

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/payments/{payment.payment_id}")
    assert r.status_code == 200
    assert r.data["reference"] == "PAY-D1"
    assert float(r.data["amount"]) == 10000.0


def test_payment_receipt(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], [
        (10000.0, "PAY-R1", "CONFIRMED", datetime.date(2026, 8, 24)),
    ])
    db.commit()

    payment = db.execute(
        sa.select(Payment).where(Payment.reference == "PAY-R1")
    ).scalar_one()

    receipt = PaymentReceipt(
        payment_id=payment.payment_id,
        receipt_number="RCT-2026-000001",
        issued_at=datetime.datetime(2026, 8, 24, 10, 0, 0),
        file_name="receipt.pdf",
        storage_key="receipts/receipt.pdf",
    )
    db.add(receipt)
    db.commit()

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/payments/{payment.payment_id}/receipt")
    assert r.status_code == 200
    assert r.data["receipt_number"] == "RCT-2026-000001"


def test_payment_isolation(admin_client, client, db):
    c1 = _create_customer(admin_client, "Pay Isolation 1")
    c2 = _create_customer(admin_client, "Pay Isolation 2")
    p1 = _create_portal_user(admin_client, c1["customer_id"], "iso.user1", "iso1@example.com")
    _setup_portal_user(admin_client, client, p1)

    _seed_payments(db, c2["customer_id"], [
        (99999.0, "PAY-ISO-C2", "CONFIRMED", datetime.date(2026, 8, 1)),
    ])
    db.commit()

    r = client.get(f"/api/portal/customers/{c2['customer_id']}/payments")
    assert r.status_code == 403
