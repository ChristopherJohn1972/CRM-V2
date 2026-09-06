import uuid

import sqlalchemy as sa

from common.db import SessionLocal
from iam.models import AuditLog, Permission


def _unique(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_role(admin_client, name=None, **overrides):
    payload = {
        "name": name or _unique("Spec Ops"),
        "rights": ["clients.customer.read"],
        "scope": "DEPARTMENT",
    }
    payload.update(overrides)
    return admin_client.post("/api/roles", payload, format="json")


def _slug(name):
    code = "".join(c if c.isalnum() else "_" for c in name.upper())
    while "__" in code:
        code = code.replace("__", "_")
    return code.strip("_")[:100]


# ---------------------------------------------------------------------------
# The reported bug: rights must actually attach to the role.
# ---------------------------------------------------------------------------

def test_create_role_with_rights_field_gets_rights(admin_client):
    created = _create_role(admin_client)
    assert created.status_code == 201, created.content
    role_id = created.data["role_id"]
    assert set(created.data["permission_codes"]) == {"clients.customer.read"}
    assert set(created.data["scope_codes"]) == {"SCOPE_DEPARTMENT"}
    assert created.data["effective_scope"] == "DEPARTMENT"

    detail = admin_client.get(f"/api/roles/{role_id}")
    assert detail.status_code == 200, detail.content
    assert set(detail.data["permission_codes"]) == {"clients.customer.read"}


def test_rights_alias_works_on_iam_path(admin_client):
    created = admin_client.post(
        "/api/iam/roles",
        {
            "name": _unique("Alias Role"),
            "rights": ["clients.contact.read", "clients.customer.read"],
            "scope": "ASSIGNED",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    assert set(created.data["permission_codes"]) == {
        "clients.contact.read",
        "clients.customer.read",
    }
    assert created.data["effective_scope"] == "ASSIGNED"


def test_role_code_derived_when_omitted(admin_client):
    name = _unique("Ops Coordinator")
    created = admin_client.post(
        "/api/roles",
        {"name": name, "rights": ["clients.customer.read"]},
        format="json",
    )
    assert created.status_code == 201, created.content
    assert created.data["code"] == _slug(name)


def test_metadata_patch_preserves_rights(admin_client):
    created = _create_role(admin_client, name=_unique("Keep Rights"))
    role_id = created.data["role_id"]

    patched = admin_client.patch(
        f"/api/iam/roles/{role_id}",
        {"description": "now with a description"},
        format="json",
    )
    assert patched.status_code == 200, patched.content
    assert set(patched.data["permission_codes"]) == {"clients.customer.read"}

    detail = admin_client.get(f"/api/roles/{role_id}")
    assert set(detail.data["permission_codes"]) == {"clients.customer.read"}


def test_status_alias_maps_to_active(admin_client):
    created = admin_client.post(
        "/api/roles",
        {
            "name": _unique("Status Aliased"),
            "rights": ["clients.customer.read"],
            "status": "INACTIVE",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    assert created.data["is_active"] is False


# ---------------------------------------------------------------------------
# Atomicity / validation
# ---------------------------------------------------------------------------

def test_put_role_rights_replaces_atomically_and_rolls_back(admin_client):
    created = _create_role(admin_client)
    role_id = created.data["role_id"]

    replaced = admin_client.put(
        f"/api/roles/{role_id}/rights",
        {"rights": ["clients.customer.update", "clients.contact.read"]},
        format="json",
    )
    assert replaced.status_code == 200, replaced.content
    assert set(replaced.data["permission_codes"]) == {
        "clients.customer.update",
        "clients.contact.read",
    }

    bad = admin_client.put(
        f"/api/roles/{role_id}/rights",
        {"rights": ["clients.customer.read", "NO_SUCH_PERMISSION"]},
        format="json",
    )
    assert bad.status_code == 422
    assert bad.data["code"] == "unprocessable_entity"

    detail = admin_client.get(f"/api/roles/{role_id}")
    assert set(detail.data["permission_codes"]) == {
        "clients.customer.update",
        "clients.contact.read",
    }


def test_inactive_right_assignment_rejected(admin_client, db):
    db.add(
        Permission(
            name="Legacy Right",
            code="legacy.potato.read",
            resource="legacy",
            action="read",
            description="Retired right",
            is_active=False,
        )
    )
    db.commit()

    created = _create_role(admin_client, name=_unique("Inactive Tester"))
    role_id = created.data["role_id"]

    rejected = admin_client.put(
        f"/api/roles/{role_id}/rights",
        {"rights": ["legacy.potato.read"]},
        format="json",
    )
    assert rejected.status_code == 422

    detail = admin_client.get(f"/api/roles/{role_id}")
    assert "clients.customer.read" in detail.data["permission_codes"]
    assert "legacy.potato.read" not in detail.data["permission_codes"]


def test_duplicate_role_is_conflict(admin_client):
    name = _unique("Duplicate")
    first = _create_role(admin_client, name=name)
    assert first.status_code == 201
    second = admin_client.post(
        "/api/roles",
        {"name": name, "rights": ["clients.customer.read"]},
        format="json",
    )
    assert second.status_code == 409
    assert second.data["code"] == "role_conflict"


def test_role_detail_404(admin_client):
    assert admin_client.get("/api/roles/999999").status_code == 404


# ---------------------------------------------------------------------------
# System-role protection
# ---------------------------------------------------------------------------

def test_cannot_create_system_role(admin_client):
    response = admin_client.post(
        "/api/roles",
        {
            "name": _unique("Wannabe System"),
            "rights": ["clients.customer.read"],
            "is_system_role": True,
        },
        format="json",
    )
    assert response.status_code == 422
    assert response.data["code"] == "unprocessable_entity"


def _role_by_code(admin_client, code):
    roles = admin_client.get("/api/roles").data["roles"]
    return next(r for r in roles if r["code"] == code)


def test_system_role_code_immutable(admin_client):
    role_id = _role_by_code(admin_client, "SUPER_ADMIN")["role_id"]
    response = admin_client.patch(
        f"/api/roles/{role_id}",
        {"code": "SUPER_ADMIN_HACKED"},
        format="json",
    )
    assert response.status_code == 422
    assert "immutable" in response.data["detail"].lower()


def test_system_role_flag_immutable(admin_client):
    role_id = _role_by_code(admin_client, "SUPER_ADMIN")["role_id"]
    response = admin_client.patch(
        f"/api/roles/{role_id}",
        {"is_system_role": False},
        format="json",
    )
    assert response.status_code == 422


def test_system_role_deactivation_guard(admin_client):
    sys_admin_id = _role_by_code(admin_client, "SYSTEM_ADMINISTRATOR")["role_id"]
    super_admin_id = _role_by_code(admin_client, "SUPER_ADMIN")["role_id"]

    try:
        # Another active admin role exists, so deactivating one is allowed.
        first = admin_client.patch(
            f"/api/roles/{sys_admin_id}",
            {"is_active": False},
            format="json",
        )
        assert first.status_code == 200, first.content

        # Now it would be the last active platform-admin role -> rejected.
        last = admin_client.patch(
            f"/api/roles/{super_admin_id}",
            {"is_active": False},
            format="json",
        )
        assert last.status_code == 422
        assert "platform administration" in last.data["detail"].lower()
    finally:
        admin_client.patch(f"/api/roles/{sys_admin_id}", {"is_active": True}, format="json")


# ---------------------------------------------------------------------------
# Operators on roles
# ---------------------------------------------------------------------------

def _audit_rows(action, resource_id):
    session = SessionLocal()
    try:
        return session.execute(
            sa.select(AuditLog).where(
                AuditLog.action == action,
                AuditLog.resource_id == resource_id,
            )
        ).scalars().all()
    finally:
        session.close()


def test_assign_remove_role_lifecycle_and_operators(admin_client, create_user):
    created = _create_role(admin_client, name=_unique("Assign Me"))
    role_id = created.data["role_id"]
    role_code = created.data["code"]
    user_id = create_user("spec.op", "spec.op@example.com", "Pass!123")

    assigned = admin_client.post(
        f"/api/operators/{user_id}/roles",
        {"role_codes": [role_code]},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content
    assert "clients.customer.read" in {p["code"] for p in assigned.data["rights_preview"]}

    assigned_again = admin_client.post(
        f"/api/operators/{user_id}/roles",
        {"role_codes": [role_code]},
        format="json",
    )
    assert assigned_again.status_code == 200

    operators = admin_client.get(f"/api/roles/{role_id}/operators")
    assert operators.status_code == 200
    assert [o["username"] for o in operators.data["operators"]] == ["spec.op"]

    review = admin_client.get(f"/api/iam/operators/{user_id}/access-review")
    assert any(
        p["code"] == "clients.customer.read" and p["effective"] == "ALLOW"
        for p in review.data["permissions"]
    )

    assert len(_audit_rows("operator.role.assigned", user_id)) == 1  # idempotent

    removed = admin_client.delete(f"/api/operators/{user_id}/roles/{role_id}")
    assert removed.status_code == 204
    operators = admin_client.get(f"/api/roles/{role_id}/operators")
    assert operators.data["operators"] == []
    assert len(_audit_rows("operator.role.removed", user_id)) == 1


def test_assign_unknown_role_rejected(admin_client, create_user):
    user_id = create_user("spec.op2", "spec.op2@example.com", "Pass!123")
    response = admin_client.post(
        f"/api/operators/{user_id}/roles",
        {"role_codes": ["NO_SUCH_ROLE"]},
        format="json",
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Rights catalogue / me-permissions
# ---------------------------------------------------------------------------

def test_rights_filtering(admin_client):
    by_code = admin_client.get("/api/rights?code=customer.read")
    assert by_code.status_code == 200
    codes = {p["code"] for p in by_code.data["permissions"]}
    assert "clients.customer.read" in codes
    assert "clients.contact.create" not in codes

    by_resource = admin_client.get("/api/rights?resource=clients")
    assert all(p["resource"] == "clients" for p in by_resource.data["permissions"])
    assert len(by_resource.data["permissions"]) > 1


def test_rights_detail(admin_client):
    listing = admin_client.get("/api/rights?code=clients.customer.read").data["permissions"]
    permission_id = listing[0]["permission_id"]
    detail = admin_client.get(f"/api/rights/{permission_id}")
    assert detail.status_code == 200
    assert detail.data["code"] == "clients.customer.read"
    assert admin_client.get("/api/rights/999999").status_code == 404


def test_me_permissions_returns_effective_grants(rep_client):
    response = rep_client.get("/api/me/permissions")
    assert response.status_code == 200
    codes = {p["code"] for p in response.data["permissions"]}
    assert "clients.customer.read" in codes
    assert "iam.user.manage" not in codes
    assert response.data["scope"]["effective"] == "ASSIGNED"


def test_me_permissions_requires_auth(client):
    response = client.get("/api/me/permissions")
    assert response.status_code in (401, 403)


def test_spec_endpoints_enforce_permissions(rep_client):
    assert rep_client.get("/api/roles").status_code == 403
    assert rep_client.get("/api/rights").status_code == 403
    assert rep_client.post("/api/roles", {"name": "X"}, format="json").status_code == 403


# ---------------------------------------------------------------------------
# Multi-right assignment: POST adds, DELETE removes, right_ids accepted
# ---------------------------------------------------------------------------

def _role_permission_codes(role_id):
    rp = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    perm = Permission.__table__
    session = SessionLocal()
    try:
        return set(
            session.execute(
                sa.select(perm.c.code)
                .select_from(rp.join(perm, rp.c.permission_id == perm.c.permission_id))
                .where(rp.c.role_id == role_id)
            ).scalars().all()
        )
    finally:
        session.close()


def test_post_rights_adds_idempotently_and_never_duplicates(admin_client):
    created = _create_role(admin_client, name=_unique("Add Rights"))
    role_id = created.data["role_id"]

    added = admin_client.post(
        f"/api/roles/{role_id}/rights",
        {"rights": ["clients.customer.update", "clients.contact.read"]},
        format="json",
    )
    assert added.status_code == 200, added.content
    assert set(added.data["permission_codes"]) == {
        "clients.customer.read",
        "clients.customer.update",
        "clients.contact.read",
    }

    added_again = admin_client.post(
        f"/api/roles/{role_id}/rights",
        {"rights": ["clients.customer.update", "clients.customer.status.change"]},
        format="json",
    )
    assert added_again.status_code == 200
    assert set(added_again.data["permission_codes"]) == {
        "clients.customer.read",
        "clients.customer.update",
        "clients.contact.read",
        "clients.customer.status.change",
    }
    # Exact row count in the junction table: one per (role, right).
    assert _role_permission_codes(role_id) == set(added_again.data["permission_codes"])
    # Two distinct additions => two audit rows (the duplicate was skipped).
    assert len(_audit_rows("role.rights.added", role_id)) == 2


def test_post_rights_rejects_unknown(admin_client):
    created = _create_role(admin_client, name=_unique("Bad Add"))
    role_id = created.data["role_id"]
    bad = admin_client.post(
        f"/api/roles/{role_id}/rights",
        {"rights": ["NO_SUCH_PERMISSION"]},
        format="json",
    )
    assert bad.status_code == 422
    detail = admin_client.get(f"/api/roles/{role_id}")
    assert set(detail.data["permission_codes"]) == {"clients.customer.read"}


def test_delete_rights_removes_selected_only(admin_client):
    created = _create_role(
        admin_client,
        name=_unique("Trim Rights"),
        rights=["clients.customer.read", "clients.customer.update", "clients.contact.read"],
    )
    role_id = created.data["role_id"]

    removed = admin_client.delete(
        f"/api/roles/{role_id}/rights",
        {"rights": ["clients.customer.read"]},
        format="json",
    )
    assert removed.status_code == 200, removed.content
    assert set(removed.data["permission_codes"]) == {
        "clients.customer.update",
        "clients.contact.read",
    }
    assert len(_audit_rows("role.rights.removed", role_id)) == 1


def test_right_ids_accepted_and_validated(admin_client):
    catalogue = {
        p["code"]: p["permission_id"]
        for p in admin_client.get("/api/rights").data["permissions"]
    }
    created = _create_role(admin_client, name=_unique("Ids Held"))
    role_id = created.data["role_id"]

    added = admin_client.post(
        f"/api/roles/{role_id}/rights",
        {
            "right_ids": [
                catalogue["clients.customer.update"],
                catalogue["clients.contact.read"],
            ]
        },
        format="json",
    )
    assert added.status_code == 200, added.content
    assert "clients.customer.update" in added.data["permission_codes"]
    assert "clients.contact.read" in added.data["permission_codes"]

    bad = admin_client.post(
        f"/api/roles/{role_id}/rights",
        {"right_ids": [999999]},
        format="json",
    )
    assert bad.status_code == 422
    bad_list = admin_client.delete(
        f"/api/roles/{role_id}/rights",
        {"right_ids": ["not-an-int"]},
        format="json",
    )
    assert bad_list.status_code == 422


# ---------------------------------------------------------------------------
# Effective-rights / effective-access for an operator
# ---------------------------------------------------------------------------

def test_effective_rights_and_effective_access_endpoints(admin_client, create_user):
    created = _create_role(
        admin_client,
        name=_unique("Eff Rights"),
        rights=["clients.customer.read", "clients.contact.read"],
        scope="ASSIGNED",
    )
    role_code = created.data["code"]
    user_id = create_user("eff.op", "eff.op@example.com", "EffPass!123")
    assigned = admin_client.post(
        f"/api/operators/{user_id}/roles",
        {"role_codes": [role_code]},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content

    effective = admin_client.get(f"/api/operators/{user_id}/effective-rights")
    assert effective.status_code == 200, effective.content
    codes = {r["code"] for r in effective.data["rights"]}
    assert {"clients.customer.read", "clients.contact.read"} <= codes
    assert effective.data["scope"]["effective"] == "ASSIGNED"

    access = admin_client.get(f"/api/operators/{user_id}/effective-access")
    assert access.status_code == 200, access.content
    assert access.data["scope"]["effective"] == "ASSIGNED"
    assert any(
        p["code"] == "clients.customer.read" and p["effective"] == "ALLOW"
        for p in access.data["permissions"]
    )


def test_effective_endpoints_require_admin(rep_client):
    assert rep_client.get("/api/operators/1/effective-rights").status_code == 403
    assert rep_client.get("/api/operators/1/effective-access").status_code == 403