from portal.services import NotificationService


def _create_customer(admin_client, name="Notif Co"):
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


def _create_portal_user(admin_client, customer_id, username="notif.user", email="notif@example.com"):
    response = admin_client.post(
        "/api/portal/users",
        {
            "username": username,
            "email": email,
            "first_name": "Notif",
            "last_name": "User",
            "customers": [{"customer_id": customer_id, "relationship_type": "OWNER", "is_primary": True}],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def _setup_portal_user(admin_client, client, portal_user):
    for perm in ["portal.customer.view", "portal.notification.view", "portal.notification.read"]:
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


def _seed_notification(session, portal_user_id, notif_type="PAYMENT_RECEIVED", title="Test", is_read=False):
    from portal.models import Notification

    n = Notification(
        portal_user_id=portal_user_id,
        type=notif_type,
        title=title,
        is_read=is_read,
    )
    session.add(n)
    session.flush()
    return n


def test_list_notifications(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_notification(db, portal_user["portal_user_id"], title="Notif 1")
    _seed_notification(db, portal_user["portal_user_id"], title="Notif 2", is_read=True)
    db.commit()

    r = client.get("/api/portal/notifications")
    assert r.status_code == 200
    assert r.data["count"] == 2


def test_filter_unread_notifications(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    _seed_notification(db, portal_user["portal_user_id"], title="Unread")
    _seed_notification(db, portal_user["portal_user_id"], title="Read", is_read=True)
    db.commit()

    r = client.get("/api/portal/notifications?unread_only=true")
    assert r.status_code == 200
    assert r.data["count"] == 1
    assert r.data["results"][0]["title"] == "Unread"


def test_mark_notification_read(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    n = _seed_notification(db, portal_user["portal_user_id"], title="To read")
    db.commit()

    r = client.post(f"/api/portal/notifications/{n.notification_id}/read")
    assert r.status_code == 204

    r = client.get("/api/portal/notifications?unread_only=true")
    assert r.data["count"] == 0


def test_mark_all_read(admin_client, client, db):
    customer = _create_customer(admin_client)
    portal_user = _create_portal_user(admin_client, customer["customer_id"])
    _setup_portal_user(admin_client, client, portal_user)

    for i in range(5):
        _seed_notification(db, portal_user["portal_user_id"], title=f"N{i}")
    db.commit()

    r = client.post("/api/portal/notifications/read-all")
    assert r.status_code == 204

    r = client.get("/api/portal/notifications?unread_only=true")
    assert r.data["count"] == 0


def test_notification_service_create(db):
    from iam.models import User
    from clients.models import Customer
    import random
    import string

    account = "C" + "".join(random.choices(string.digits, k=4))
    customer = Customer(
        customer_number=account,
        customer_type="BUSINESS",
        legal_name="SvcNotif Co",
        display_name="SvcNotif Co",
        email="svcnotif@example.com",
        phone="+254799000001",
    )
    db.add(customer)
    db.flush()
    user = User(username="svcnotif", email="svcnotif@example.com", first_name="S", last_name="N", status="ACTIVE")
    db.add(user)
    db.flush()

    from portal.models import PortalUser

    pu = PortalUser(username="svcnotif.p", email="svcnotif.p@example.com", first_name="S", last_name="N", status="ACTIVE")
    db.add(pu)
    db.flush()

    notif = NotificationService.create(
        db,
        portal_user_id=pu.portal_user_id,
        notification_type="COMPLAINT_RESOLVED",
        title="Your complaint has been resolved",
        body="CMP-2026-000001 is now closed",
        customer_id=customer.customer_id,
        reference_type="complaint",
        reference_id=1,
    )
    assert notif.notification_id is not None
    assert notif.type == "COMPLAINT_RESOLVED"
