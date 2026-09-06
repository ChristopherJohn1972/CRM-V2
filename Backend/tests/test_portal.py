import sqlalchemy as sa


def _create_customer(admin_client, name="Portal Co"):
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


def _create_portal_user(admin_client, username="portal.user", email="portal.user@example.com", **extra):
    payload = {
        "username": username,
        "email": email,
        "first_name": "Portal",
        "last_name": "User",
        "phone": "+254799000002",
    }
    payload.update(extra)
    response = admin_client.post("/api/portal/users", payload, format="json")
    assert response.status_code == 201, response.content
    return response.data


def _portal_login(client, username, password):
    response = client.post(
        "/api/portal/auth/login", {"username": username, "password": password}, format="json"
    )
    return response


def test_onboarding_temp_password_and_forced_change(admin_client, client):
    portal_user = _create_portal_user(admin_client)
    assert portal_user["status"] == "PENDING"
    temp = portal_user["temp_password"]

    # First login with the temp password activates the account and flags change.
    r = _portal_login(client, "portal.user", temp)
    assert r.status_code == 200, r.content
    assert r.data["must_change_password"] is True
    token = r.data["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # Password change works with the temp password as "current".
    r = client.post(
        "/api/portal/auth/change-password",
        {"current_password": temp, "new_password": "Str0ng!PortalPass"},
        format="json",
    )
    assert r.status_code == 204, r.content

    # Old temp password no longer works; new one does and must_change clears.
    bad = _portal_login(client, "portal.user", temp)
    assert bad.status_code == 401

    r = _portal_login(client, "portal.user", "Str0ng!PortalPass")
    assert r.status_code == 200, r.content
    assert r.data["must_change_password"] is False


def test_company_name_is_not_a_valid_password(admin_client, client):
    portal_user = _create_portal_user(admin_client)
    temp = portal_user["temp_password"]
    r = _portal_login(client, "portal.user", temp)
    assert r.status_code == 200, r.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['token']}")

    r = client.post(
        "/api/portal/auth/change-password",
        {"current_password": temp, "new_password": "CRM V2"},
        format="json",
    )
    assert r.status_code == 400
    assert r.data["code"] == "validation_error"


def test_login_lockout_after_failed_attempts(admin_client, client):
    _create_portal_user(admin_client)
    for _ in range(5):
        r = _portal_login(client, "portal.user", "wrong-password")
        assert r.status_code == 401
    # 6th attempt hits the lock window.
    r = _portal_login(client, "portal.user", "wrong-password")
    assert r.status_code == 403
    assert r.data["code"] == "account_locked"


def test_forgot_and_reset_password(admin_client, client):
    _create_portal_user(admin_client)
    r = client.post(
        "/api/portal/auth/forgot-password",
        {"login": "portal.user@example.com"},
        format="json",
    )
    assert r.status_code == 200, r.content
    token = r.data["debug_reset_token"]

    r = client.post(
        "/api/portal/auth/reset-password",
        {"token": token, "new_password": "BrandNew!Pass123"},
        format="json",
    )
    assert r.status_code == 204, r.content

    # Reset token is single-use.
    r = client.post(
        "/api/portal/auth/reset-password",
        {"token": token, "new_password": "Another!Pass456"},
        format="json",
    )
    assert r.status_code == 400
    assert r.data["code"] == "reset_token_used"
    # New password works.
    r = _portal_login(client, "portal.user", "BrandNew!Pass123")
    assert r.status_code == 200, r.content


def test_portal_user_customer_access_isolation(admin_client, client, db):
    c1 = _create_customer(admin_client, "Customer One")
    c2 = _create_customer(admin_client, "Customer Two")
    portal_user = _create_portal_user(admin_client)

    # Admin links the portal user to customer_one only, then grants view.
    r = admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/customers",
        {"customer_id": c1["customer_id"], "relationship_type": "OWNER", "is_primary": True},
        format="json",
    )
    assert r.status_code == 200, r.content
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "ALLOW"},
        format="json",
    )

    temp = portal_user["temp_password"]
    login = _portal_login(client, "portal.user", temp)
    token = login.data["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    client.post(
        "/api/portal/auth/change-password",
        {"current_password": temp, "new_password": "Str0ng!PortalPass"},
        format="json",
    )

    # Re-login with the permanent password.
    login = _portal_login(client, "portal.user", "Str0ng!PortalPass")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    detail = client.get(f"/api/portal/customers/{c1['customer_id']}")
    assert detail.status_code == 200, detail.content
    assert detail.data["customer_number"] == c1["account_number"]

    # The unlinked customer must be denied.
    denied = client.get(f"/api/portal/customers/{c2['customer_id']}")
    assert denied.status_code == 403

    # List only shows the linked customer.
    listing = client.get("/api/portal/customers")
    assert listing.status_code == 200
    assert {row["customer_id"] for row in listing.data["results"]} == {c1["customer_id"]}

    # Audit recorded a PORTAL_USER actor.
    from iam.models import AuditLog

    row = db.execute(
        sa.select(AuditLog).where(AuditLog.actor_type == "PORTAL_USER")
    ).scalars().first()
    assert row is not None
    assert row.actor_portal_user_id == portal_user["portal_user_id"]


def test_portal_permission_deny_wins(admin_client, client, db):
    c1 = _create_customer(admin_client, "Deny Co")
    portal_user = _create_portal_user(admin_client)
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/customers",
        {"customer_id": c1["customer_id"], "relationship_type": "VIEWER", "is_primary": True},
        format="json",
    )
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "ALLOW"},
        format="json",
    )
    # Explicit DENY must override the ALLOW.
    r = admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "DENY"},
        format="json",
    )
    assert r.status_code == 200, r.content

    temp = portal_user["temp_password"]
    login = _portal_login(client, "portal.user", temp)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
    client.post(
        "/api/portal/auth/change-password",
        {"current_password": temp, "new_password": "Str0ng!PortalPass"},
        format="json",
    )
    login = _portal_login(client, "portal.user", "Str0ng!PortalPass")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    denied = client.get(f"/api/portal/customers/{c1['customer_id']}")
    assert denied.status_code == 403


def test_portal_token_cannot_use_internal_admin_apis(admin_client, client):
    c1 = _create_customer(admin_client, "Boundary Co")
    portal_user = _create_portal_user(admin_client)
    temp = portal_user["temp_password"]
    login = _portal_login(client, "portal.user", temp)
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    # Portal token is rejected by the internal client API.
    r = client.get("/api/clients")
    assert r.status_code == 403 or r.status_code == 401

    # And the internal admin cannot manage portal users with a portal token.
    r = client.get(f"/api/portal/users/{portal_user['portal_user_id']}")
    assert r.status_code == 403 or r.status_code == 401


def test_internal_admin_token_cannot_use_portal_api(admin_client):
    internal = admin_client.post(
        "/api/auth/login", {"username": "admin", "password": "AdminPass!123"}, format="json"
    )
    assert internal.status_code == 200, internal.content
    admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {internal.data['token']}")

    r = admin_client.get("/api/portal/me")
    assert r.status_code in (401, 403)


def test_portal_user_status_activate_suspend_deactivate(admin_client, client):
    portal_user = _create_portal_user(admin_client)
    puid = portal_user["portal_user_id"]

    r = admin_client.patch(
        f"/api/portal/users/{puid}/status", {"status": "SUSPENDED"}, format="json"
    )
    assert r.status_code == 200, r.content
    assert r.data["status"] == "SUSPENDED"

    # Suspended portal users cannot log in.
    r = _portal_login(client, "portal.user", portal_user["temp_password"])
    assert r.status_code == 403

    r = admin_client.patch(
        f"/api/portal/users/{puid}/status", {"status": "DEACTIVATED"}, format="json"
    )
    assert r.status_code == 200
    assert r.data["status"] == "DEACTIVATED"


def test_permission_management_requires_internal_iam_manage(admin_client, rep_client, client):
    portal_user = _create_portal_user(admin_client)
    # SALES_REP lacks iam.user.manage.
    r = rep_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "ALLOW"},
        format="json",
    )
    assert r.status_code == 403

    r = admin_client.get(f"/api/portal/users/{portal_user['portal_user_id']}/permissions")
    assert r.status_code == 200, r.content
    codes = {p["code"] for p in r.data["permissions"]}
    assert "portal.customer.view" in codes


def test_deactivated_link_removes_access(admin_client, client):
    c1 = _create_customer(admin_client, "Unlink Co")
    portal_user = _create_portal_user(admin_client)
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/customers",
        {"customer_id": c1["customer_id"], "relationship_type": "OWNER", "is_primary": True},
        format="json",
    )
    admin_client.post(
        f"/api/portal/users/{portal_user['portal_user_id']}/permissions",
        {"permission_code": "portal.customer.view", "effect": "ALLOW"},
        format="json",
    )

    temp = portal_user["temp_password"]
    login = _portal_login(client, "portal.user", temp)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
    client.post(
        "/api/portal/auth/change-password",
        {"current_password": temp, "new_password": "Str0ng!PortalPass"},
        format="json",
    )
    login = _portal_login(client, "portal.user", "Str0ng!PortalPass")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")
    assert client.get(f"/api/portal/customers/{c1['customer_id']}").status_code == 200

    links = admin_client.get(f"/api/portal/users/{portal_user['portal_user_id']}/customers")
    link_id = links.data["results"][0]["portal_user_customer_id"]
    r = admin_client.delete(
        f"/api/portal/users/{portal_user['portal_user_id']}/customers/{link_id}"
    )
    assert r.status_code == 204

    denied = client.get(f"/api/portal/customers/{c1['customer_id']}")
    assert denied.status_code == 403