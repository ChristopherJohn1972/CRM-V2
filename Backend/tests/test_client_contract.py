import uuid

import sqlalchemy as sa

from clients.models import Customer, CustomerAddress


def _create(client, **overrides):
    payload = {
        "customer_type": "BUSINESS",
        "legal_name": "Contract Co",
        "email": "contract@example.com",
        "phone": "+254700000001",
    }
    payload.update(overrides)
    return client.post("/api/clients", payload, format="json")


def _unique_name(prefix):
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def _login(client, username, password):
    response = client.post(
        "/api/auth/login", {"username": username, "password": password}, format="json"
    )
    assert response.status_code == 200, response.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
    return response.data


def test_removed_fields_cannot_alter_stored_model(admin_client, db):
    response = _create(
        admin_client,
        display_name="Should Not Persist",
        assigned_user_id=999,
        assigned_team_id=999,
        branch_id=1,
        account_number="9999",
        addresses=[
            {
                "address_type": "OFFICE",
                "address": "Nairobi Road",
                "city": "Nairobi",
                "country": "Kenya",
                "is_primary": True,
                "state_province": "Sneaky-State",
                "address_line_2": "Sneaky-Line2",
            }
        ],
    )
    assert response.status_code == 201, response.content
    customer_id = response.data["customer_id"]
    assert response.data["account_number"] == "0001"
    assert response.data["account_number"] != "9999"
    assert "display_name" not in response.data

    customer = db.get(Customer, customer_id)
    assert customer.display_name is None
    assert customer.assigned_user_id is None
    assert customer.assigned_team_id is None
    assert customer.branch_id is None
    assert customer.created_by is not None

    address = (
        db.execute(
            sa.select(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id
            )
        )
        .scalars()
        .one()
    )
    assert address.address == "Nairobi Road"
    assert address.address_line_1 is None
    assert address.state_province is None
    assert address.address_line_2 is None


def test_read_contract_returns_canonical_legal_name(admin_client):
    response = _create(admin_client)
    assert response.status_code == 201
    assert response.data["legal_name"] == "Contract Co"
    assert "display_name" not in response.data


def test_single_address_round_trip(admin_client):
    created = _create(
        admin_client,
        addresses=[
            {"address_type": "OFFICE", "address": "Moi Avenue 45", "is_primary": True}
        ],
    )
    assert created.status_code == 201, created.content
    customer_id = created.data["customer_id"]

    listed = admin_client.get(f"/api/clients/{customer_id}/addresses")
    assert listed.status_code == 200
    assert listed.data[0]["address"] == "Moi Avenue 45"
    assert "address_line_1" not in listed.data[0]
    assert "state_province" not in listed.data[0]

    added = admin_client.post(
        f"/api/clients/{customer_id}/addresses",
        {"address_type": "HOME", "address": "Ngong Lane", "city": "Nairobi"},
        format="json",
    )
    assert added.status_code == 201, added.content
    assert added.data["address"] == "Ngong Lane"


def test_legacy_address_fields_rejected(admin_client):
    response = _create(
        admin_client,
        addresses=[{"address_type": "OFFICE", "address_line_1": "Old Street"}],
    )
    assert response.status_code == 400


def test_assignment_only_possible_via_transfer(admin_client, sales_rep_user):
    created = _create(admin_client)
    assert created.data["assigned_user_id"] is None

    transfer = admin_client.post(
        f"/api/clients/{created.data['customer_id']}/transfer",
        {"assigned_user_id": sales_rep_user},
        format="json",
    )
    assert transfer.status_code == 200, transfer.content
    assert transfer.data["assigned_user_id"] == sales_rep_user


def test_list_detail_search_consistent_scope(admin_client, rep_client, create_user):
    other_rep = create_user(
        "rep9", "rep9@example.com", "RepPass!123", role_code="SALES_REP"
    )

    owned = _create(admin_client, legal_name="Strict Co")
    transfer = admin_client.post(
        f"/api/clients/{owned.data['customer_id']}/transfer",
        {"assigned_user_id": other_rep},
        format="json",
    )
    assert transfer.status_code == 200, transfer.content
    account_number = owned.data["account_number"]

    assert rep_client.get("/api/clients").data["count"] == 0
    assert rep_client.get(f"/api/clients/{owned.data['customer_id']}").status_code == 403
    assert rep_client.get("/api/clients?search=Strict").data["count"] == 0
    assert rep_client.get(f"/api/clients?search={account_number}").data["count"] == 0
    assert rep_client.get("/api/clients?status=PROSPECT").data["count"] == 0


def test_creator_gets_no_implicit_visibility(rep_client):
    # Creation must not silently make a record visible to its creator:
    # visibility comes from permission + explicit scope (spec §11/§17).
    created = rep_client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": "My Created Co",
            "email": "my@example.com",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    cid = created.data["customer_id"]

    # SALES_REP is ASSIGNED scope; the record was never assigned to the rep.
    assert rep_client.get("/api/clients").data["count"] == 0
    assert rep_client.get(f"/api/clients/{cid}").status_code == 403
    assert rep_client.get("/api/clients?search=My%20Created").data["count"] == 0


def test_creator_visibility_does_not_leak_others_records(admin_client, rep_client):
    other = admin_client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": "Not Yours Co",
            "email": "o@example.com",
        },
        format="json",
    )
    assert other.status_code == 201, other.content

    assert rep_client.get("/api/clients").data["count"] == 0
    assert rep_client.get(f"/api/clients/{other.data['customer_id']}").status_code == 403
    assert rep_client.get("/api/clients?search=Not%20Yours").data["count"] == 0


def _role_with_scope(admin_client, rights, scope, name=None):
    response = admin_client.post(
        "/api/roles",
        {
            "name": name or _unique_name("Scope Role"),
            "rights": rights,
            "scope": scope,
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def test_manager_with_all_scope_sees_admin_created_client(admin_client, client, create_user):
    role = _role_with_scope(admin_client, ["clients.customer.read"], "ALL")
    user_id = create_user("allscope1", "allscope1@example.com", "AllPass!123", role_code=role["code"])

    created = admin_client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": "Handed Over Co",
            "email": "handover@example.com",
        },
        format="json",
    )
    assert created.status_code == 201, created.content

    _login(client, "allscope1", "AllPass!123")
    listed = client.get("/api/clients")
    assert listed.status_code == 200
    assert listed.data["count"] == 1
    assert listed.data["results"][0]["customer_id"] == created.data["customer_id"]
    assert client.get(f"/api/clients/{created.data['customer_id']}").status_code == 200


def test_manager_assigned_scope_sees_only_after_assignment(admin_client, client, create_user, sales_rep_user):
    role = _role_with_scope(admin_client, ["clients.customer.read"], "ASSIGNED")
    user_id = create_user("assignmgr1", "assignmgr1@example.com", "AssignPass!123", role_code=role["code"])

    created = admin_client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": "Streets Co",
            "email": "streets@example.com",
        },
        format="json",
    )
    assert created.status_code == 201, created.content

    _login(client, "assignmgr1", "AssignPass!123")
    assert client.get("/api/clients").data["count"] == 0

    claim = admin_client.post(
        f"/api/clients/{created.data['customer_id']}/transfer",
        {"assigned_user_id": user_id},
        format="json",
    )
    assert claim.status_code == 200, claim.content

    listed = client.get("/api/clients")
    assert listed.data["count"] == 1
    assert client.get(f"/api/clients/{created.data['customer_id']}").status_code == 200


def test_manager_without_client_read_is_denied(admin_client, client, create_user):
    role = _role_with_scope(admin_client, ["communications.sms.read"], "ALL")
    user_id = create_user("noread1", "noread1@example.com", "NoReadPass!123", role_code=role["code"])
    assert user_id

    _login(client, "noread1", "NoReadPass!123")
    assert client.get("/api/clients").status_code == 403


# -------------------------------------------------------------------
# Soft-delete tests
# -------------------------------------------------------------------

def test_soft_delete_sets_deleted_at(admin_client, db):
    created = _create(admin_client, legal_name="Delete Me")
    assert created.status_code == 201, created.content
    cid = created.data["customer_id"]

    response = admin_client.delete(f"/api/clients/{cid}")
    assert response.status_code == 204

    customer = db.get(Customer, cid)
    assert customer.deleted_at is not None
    assert customer.deleted_by is not None


def test_soft_deleted_client_hidden_from_list(admin_client):
    created = _create(admin_client, legal_name="Gone From List")
    assert created.status_code == 201, created.content
    cid = created.data["customer_id"]

    admin_client.delete(f"/api/clients/{cid}")
    listed = admin_client.get("/api/clients")
    ids = [r["customer_id"] for r in listed.data["results"]]
    assert cid not in ids


def test_soft_deleted_client_hidden_from_detail(admin_client):
    created = _create(admin_client, legal_name="Gone From Detail")
    assert created.status_code == 201, created.content
    cid = created.data["customer_id"]

    admin_client.delete(f"/api/clients/{cid}")
    detail = admin_client.get(f"/api/clients/{cid}")
    assert detail.status_code == 404


def test_soft_deleted_client_hidden_from_search(admin_client):
    created = _create(admin_client, legal_name="Searchable Vanished")
    assert created.status_code == 201, created.content

    admin_client.delete(f"/api/clients/{created.data['customer_id']}")
    search = admin_client.get("/api/clients?search=Searchable%20Vanished")
    assert search.data["count"] == 0


def test_account_number_continues_after_soft_delete(admin_client):
    c1 = _create(admin_client, legal_name="First Co")
    assert c1.status_code == 201, c1.content
    assert c1.data["account_number"] == "0001"

    admin_client.delete(f"/api/clients/{c1.data['customer_id']}")

    c2 = _create(admin_client, legal_name="Second Co")
    assert c2.status_code == 201, c2.content
    assert c2.data["account_number"] == "0002"

    c3 = _create(admin_client, legal_name="Third Co")
    assert c3.status_code == 201, c3.content
    assert c3.data["account_number"] == "0003"


def test_soft_delete_requires_permission(rep_client, admin_client):
    created = _create(admin_client, legal_name="Protected Delete")
    assert created.status_code == 201, created.content
    cid = created.data["customer_id"]

    response = rep_client.delete(f"/api/clients/{cid}")
    assert response.status_code in (403, 404)


def test_soft_delete_is_idempotent(admin_client):
    created = _create(admin_client, legal_name="Double Delete")
    assert created.status_code == 201, created.content
    cid = created.data["customer_id"]

    r1 = admin_client.delete(f"/api/clients/{cid}")
    assert r1.status_code == 204

    r2 = admin_client.delete(f"/api/clients/{cid}")
    assert r2.status_code == 404


def test_soft_delete_audit_trail(admin_client, db):
    from common.db import SessionLocal
    from iam.models import AuditLog

    created = _create(admin_client, legal_name="Audit Delete")
    assert created.status_code == 201, created.content
    cid = created.data["customer_id"]

    admin_client.delete(f"/api/clients/{cid}")

    session = SessionLocal()
    try:
        rows = session.execute(
            sa.select(AuditLog).where(
                AuditLog.resource_type == "customers",
                AuditLog.resource_id == cid,
                AuditLog.action == "customer.deleted",
            )
        ).scalars().all()
        assert len(rows) == 1
    finally:
        session.close()