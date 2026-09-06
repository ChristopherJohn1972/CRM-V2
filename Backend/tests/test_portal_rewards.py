import datetime

import sqlalchemy as sa

from common.db import SessionLocal
from portal.models import Payment, Reward, RewardRedemption
from portal.services import MomentumService, RewardService


def _create_customer(admin_client, name="Reward Co"):
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


def _create_portal_user(admin_client, customer_id, username="rew.user", email="rew@example.com"):
    response = admin_client.post(
        "/api/portal/users",
        {
            "username": username,
            "email": email,
            "first_name": "Rew",
            "last_name": "User",
            "customers": [{"customer_id": customer_id, "relationship_type": "OWNER", "is_primary": True}],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _setup_portal_user(admin_client, client, portal_user):
    for perm in ["portal.customer.view", "portal.momentum.view", "portal.reward.view", "portal.reward.redeem"]:
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


def _seed_payments(session, customer_id, total):
    p = Payment(
        customer_id=customer_id,
        amount=total,
        payment_date=datetime.date(2026, 8, 1),
        reference=f"PAY-REW-{total}",
        status="CONFIRMED",
        payment_method="MPESA",
    )
    session.add(p)
    session.flush()


def _seed_reward(session, name, required_momentum, status="ACTIVE", limit=1):
    r = Reward(
        name=name,
        description=f"Test reward: {name}",
        required_momentum=required_momentum,
        status=status,
        redemption_limit=limit,
    )
    session.add(r)
    session.flush()
    return r


def test_list_all_rewards(admin_client, client, db):
    customer = _create_customer(admin_client, "ListRew Co")
    portal_user = _create_portal_user(admin_client, customer["customer_id"], "listrew.user", "listrew@example.com")
    _setup_portal_user(admin_client, client, portal_user)

    _seed_reward(db, "Starter Reward", 100)
    _seed_reward(db, "Standard Reward", 250)
    _seed_reward(db, "Enhanced Reward", 500)
    _seed_reward(db, "Major Reward", 1000)
    _seed_reward(db, "Premium Reward", 2500)
    _seed_reward(db, "Elite Reward", 5000)
    _seed_reward(db, "Exceptional Reward", 10000)
    db.commit()

    r = client.get("/api/portal/rewards")
    assert r.status_code == 200
    assert len(r.data["results"]) >= 7


def test_eligible_rewards(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_reward(db, "Standard Reward", 250)
    _seed_reward(db, "Enhanced Reward", 500)
    _seed_reward(db, "Major Reward", 1000)
    db.commit()

    _seed_payments(db, customer["customer_id"], 500000.0)
    db.commit()

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/rewards/eligible")
    assert r.status_code == 200
    assert r.data["customer_momentum"] == 500
    names = [rw["name"] for rw in r.data["eligible_rewards"]]
    assert "Enhanced Reward" in names or "Standard Reward" in names


def test_redeem_reward(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], 1000000.0)
    reward = _seed_reward(db, "Test Redeem", 100)
    db.commit()

    r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/rewards/{reward.reward_id}/redeem",
        format="json",
    )
    assert r.status_code == 201, r.content
    assert r.data["momentum_used"] == 100
    assert r.data["status"] == "PENDING"


def test_redeem_insufficient_momentum(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], 50000.0)
    reward = _seed_reward(db, "Too Expensive", 1000)
    db.commit()

    r = client.post(
        f"/api/portal/customers/{customer['customer_id']}/rewards/{reward.reward_id}/redeem",
        format="json",
    )
    assert r.status_code == 400
    assert r.data["code"] == "insufficient_momentum"


def test_redeem_limit_reached(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], 500000.0)
    reward = _seed_reward(db, "Limited", 100, limit=1)
    db.commit()

    r1 = client.post(
        f"/api/portal/customers/{customer['customer_id']}/rewards/{reward.reward_id}/redeem",
        format="json",
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/portal/customers/{customer['customer_id']}/rewards/{reward.reward_id}/redeem",
        format="json",
    )
    assert r2.status_code == 400
    assert r2.data["code"] == "redemption_limit"


def test_list_redemptions(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_payments(db, customer["customer_id"], 500000.0)
    reward = _seed_reward(db, "History Test", 100)
    db.commit()

    client.post(
        f"/api/portal/customers/{customer['customer_id']}/rewards/{reward.reward_id}/redeem",
        format="json",
    )

    r = client.get(f"/api/portal/customers/{customer['customer_id']}/rewards/redemptions")
    assert r.status_code == 200
    assert len(r.data["results"]) >= 1
    assert r.data["results"][0]["reward_name"] == "History Test"


def test_reward_service_no_ledger(db):
    """Momentum is calculated from payments, no separate ledger."""
    from clients.models import Customer
    import random
    import string

    account = "C" + "".join(random.choices(string.digits, k=4))
    customer = Customer(
        customer_number=account,
        customer_type="BUSINESS",
        legal_name="NoLedger Co",
        display_name="NoLedger Co",
        email="nolegderco@example.com",
        phone="+254799000001",
    )
    db.add(customer)
    db.flush()
    _seed_reward(db, "Starter Reward", 100)
    _seed_payments(db, customer.customer_id, 100000.0)
    db.commit()

    momentum = MomentumService.calculate_momentum(db, customer.customer_id)
    assert momentum == 100
    rewards = RewardService.list_available(db, momentum)
    assert len(rewards) > 0
