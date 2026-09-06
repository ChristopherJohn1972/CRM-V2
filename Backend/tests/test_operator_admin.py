def _create_operator(client, username, role_codes=None, **kwargs):
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "first_name": kwargs.get("first_name", "Test"),
        "last_name": kwargs.get("last_name", "Operator"),
        "status": "ACTIVE",
    }
    if role_codes:
        payload["role_codes"] = role_codes
    return client.post("/api/iam/operators", payload, format="json")


def test_operator_created_with_temp_password_and_preview(admin_client):
    response = _create_operator(admin_client, "op.create", role_codes=["SALES_REP"])
    assert response.status_code == 201, response.content
    body = response.data
    assert body["operator"]["username"] == "op.create"
    assert body["operator"]["role_codes"] == ["SALES_REP"]
    assert body["temporary_password"]
    preview = body["rights_preview"]
    codes = {p["code"] for p in preview}
    assert "clients.customer.read" in codes
    assert "clients.customer.status.change" not in codes


def test_new_operator_can_log_in_with_temp_password(admin_client, client):
    response = _create_operator(admin_client, "op.logins")
    temp_password = response.data["temporary_password"]
    login = client.post(
        "/api/auth/login",
        {"username": "op.logins", "password": temp_password},
        format="json",
    )
    assert login.status_code == 200, login.content


def test_operator_duplicate_username_rejected(admin_client, create_user):
    create_user("op.dup", "op.dup@example.com", "Pass!123")
    response = _create_operator(admin_client, "op.dup")
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"


def test_invalid_role_rejected(admin_client):
    response = _create_operator(admin_client, "op.badrole", role_codes=["NO_SUCH_ROLE"])
    assert response.status_code == 400
    assert response.data["field_errors"]["role_codes"]


def test_operator_list_and_detail(admin_client, create_user):
    user_id = create_user("op.list", "op.list@example.com", "Pass!123", role_code="SALES_REP")
    listing = admin_client.get("/api/iam/operators")
    assert listing.status_code == 200
    assert listing.data["count"] >= 1

    detail = admin_client.get(f"/api/iam/operators/{user_id}")
    assert detail.status_code == 200, detail.content
    body = detail.data
    assert body["username"] == "op.list"
    assert [r["code"] for r in body["roles"]] == ["SALES_REP"]
    assert body["effective_scope"] in {"NONE", "ASSIGNED"}
    assert body["direct_permissions"] == []


def test_operator_patch_and_role_assign(admin_client, create_user):
    user_id = create_user("op.patch", "op.patch@example.com", "Pass!123", role_code="SALES_REP")

    patched = admin_client.patch(
        f"/api/iam/operators/{user_id}",
        {"last_name": "Renamed", "status": "SUSPENDED"},
        format="json",
    )
    assert patched.status_code == 200, patched.content
    assert patched.data["last_name"] == "Renamed"
    assert patched.data["status"] == "SUSPENDED"

    assigned = admin_client.put(
        f"/api/iam/operators/{user_id}/roles",
        {"role_codes": ["READ_ONLY"]},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content
    assert assigned.data["role_codes"] == ["READ_ONLY"]
    preview = {p["code"] for p in assigned.data["rights_preview"]}
    assert "clients.customer.read" in preview
    assert "clients.customer.create" not in preview

    detail = admin_client.get(f"/api/iam/operators/{user_id}")
    assert [r["code"] for r in detail.data["roles"]] == ["READ_ONLY"]


def test_direct_permission_allow_deny_lifecycle(admin_client, create_user):
    user_id = create_user("op.direct", "op.direct@example.com", "Pass!123", role_code="SALES_REP")

    denied = admin_client.post(
        f"/api/iam/operators/{user_id}/permissions",
        {
            "permission_code": "clients.customer.update",
            "effect": "DENY",
            "reason": "Sensitive account - no edits in this sprint",
        },
        format="json",
    )
    assert denied.status_code == 200, denied.content
    assert denied.data["effect"] == "DENY"

    listing = admin_client.get(f"/api/iam/operators/{user_id}/permissions")
    assert listing.status_code == 200
    assert len(listing.data["direct_permissions"]) == 1
    assert listing.data["direct_permissions"][0]["reason"].startswith("Sensitive account")

    removed = admin_client.delete(
        f"/api/iam/operators/{user_id}/permissions/clients.customer.update"
    )
    assert removed.status_code == 204
    listing = admin_client.get(f"/api/iam/operators/{user_id}/permissions")
    assert listing.data["direct_permissions"] == []


def test_access_review_shows_sources_and_deny_wins(admin_client, create_user):
    user_id = create_user(
        "op.review", "op.review@example.com", "Pass!123", role_code="SALES_REP"
    )
    admin_client.post(
        f"/api/iam/operators/{user_id}/permissions",
        {"permission_code": "clients.customer.update", "effect": "DENY", "reason": "override"},
        format="json",
    )

    review = admin_client.get(f"/api/iam/operators/{user_id}/access-review")
    assert review.status_code == 200, review.content
    body = review.data

    updated = next(p for p in body["permissions"] if p["code"] == "clients.customer.update")
    assert updated["effective"] == "DENY"
    source_types = {s["source"] for s in updated["sources"]}
    assert source_types == {"role", "direct"}
    role_source = next(s for s in updated["sources"] if s["source"] == "role")
    assert role_source["role_code"] == "SALES_REP"
    direct_source = next(s for s in updated["sources"] if s["source"] == "direct")
    assert direct_source["reason"] == "override"

    read = next(p for p in body["permissions"] if p["code"] == "clients.customer.read")
    assert read["effective"] == "ALLOW"

    create = next(p for p in body["permissions"] if p["code"] == "clients.customer.create")
    assert create["effective"] == "ALLOW"

    sensitive = next(
        p for p in body["permissions"] if p["code"] == "clients.customer.sensitive.read"
    )
    assert sensitive["effective"] == "NONE"
    assert sensitive["sources"] == []

    assert body["rights_by_resource"]["clients"]
    scope = body["scope"]
    assert scope["effective"] in {"NONE", "ASSIGNED"}


def test_effective_scope_none_for_unassigned_operator(admin_client, create_user):
    user_id = create_user("op.noscope", "op.noscope@example.com", "Pass!123")
    review = admin_client.get(f"/api/iam/operators/{user_id}/access-review")
    assert review.status_code == 200
    assert review.data["scope"]["effective"] == "NONE"


def test_role_crud_creates_lists_updates(admin_client):
    created = admin_client.post(
        "/api/iam/roles",
        {
            "name": "Ops Coordinator",
            "code": "OPS_COORDINATOR",
            "description": "Office operations coordination",
            "permission_codes": ["clients.customer.read", "clients.contact.read"],
            "access_policy_codes": ["SCOPE_DEPARTMENT"],
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    role_id = created.data["role_id"]
    assert created.data["effective_scope"] == "DEPARTMENT"
    assert set(created.data["permission_codes"]) == {"clients.customer.read", "clients.contact.read"}

    listing = admin_client.get("/api/iam/roles")
    assert listing.status_code == 200
    assert any(r["code"] == "OPS_COORDINATOR" for r in listing.data["roles"])

    updated = admin_client.patch(
        f"/api/iam/roles/{role_id}",
        {"permission_codes": ["clients.customer.read", "clients.customer.update"]},
        format="json",
    )
    assert updated.status_code == 200, updated.content
    assert set(updated.data["permission_codes"]) == {
        "clients.customer.read",
        "clients.customer.update",
    }

    detail = admin_client.get(f"/api/iam/roles/{role_id}")
    assert detail.status_code == 200
    assert detail.data["code"] == "OPS_COORDINATOR"
    assert detail.data["is_active"] is True


def test_rights_catalogue_lists_all_active_permissions(admin_client):
    response = admin_client.get("/api/iam/rights")
    assert response.status_code == 200, response.content
    codes = {p["code"] for p in response.data["permissions"]}
    assert "clients.customer.read" in codes
    assert "iam.user.manage" in codes
    assert "iam.role.manage" in codes
    assert "iam.permission.audit" in codes


def test_scope_catalogue(admin_client):
    response = admin_client.get("/api/iam/scopes")
    assert response.status_code == 200
    codes = {s["code"] for s in response.data["scopes"]}
    assert codes == {"NONE", "OWN", "ASSIGNED", "TEAM", "DEPARTMENT", "ALL"}


def test_non_admin_denied(rep_client, sales_rep_user):
    assert rep_client.get("/api/iam/operators").status_code == 403
    assert rep_client.get("/api/iam/roles").status_code == 403
    assert rep_client.get("/api/iam/rights").status_code == 403
    assert rep_client.get(f"/api/iam/operators/{sales_rep_user}/access-review").status_code == 403
    response = _create_operator(rep_client, "op.sneaky")
    assert response.status_code == 403


def test_anonymous_denied(client):
    assert client.get("/api/iam/operators").status_code in (401, 403)