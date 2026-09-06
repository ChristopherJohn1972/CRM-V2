from conftest import _create_user


def _make_customer_assigned(client, assigned_user_id=None):
    payload = {
        "customer_type": "BUSINESS",
        "legal_name": "Scoped Co",
        "email": "scoped@example.com",
        "phone": "+254711111111",
    }
    response = client.post("/api/clients", payload, format="json")
    assert response.status_code == 201, response.content
    data = response.data
    if assigned_user_id is not None:
        claim = client.post(
            f"/api/clients/{data['customer_id']}/transfer",
            {"assigned_user_id": assigned_user_id},
            format="json",
        )
        assert claim.status_code == 200, claim.content
    return data


def test_unauthenticated_request_rejected(client):
    response = client.get("/api/clients")
    assert response.status_code in (401, 403)


def test_rep_cannot_transfer_ownership(rep_client):
    data = _make_customer_assigned(rep_client)
    response = rep_client.post(
        f"/api/clients/{data['customer_id']}/transfer",
        {"assigned_user_id": 999},
        format="json",
    )
    assert response.status_code == 403


def test_rep_without_sensitive_read_gets_mask(admin_client, rep_client, sales_rep_user):
    created = admin_client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": "Masked Co",
            "tax_identifier": "P123456789X",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    assert created.data["tax_identifier"] == "P123456789X"

    claim = admin_client.post(
        f"/api/clients/{created.data['customer_id']}/transfer",
        {"assigned_user_id": sales_rep_user},
        format="json",
    )
    assert claim.status_code == 200, claim.content

    masked = rep_client.get(f"/api/clients/{created.data['customer_id']}")
    assert masked.status_code == 200
    assert masked.data["tax_identifier"] != "P123456789X"
    assert "***" in masked.data["tax_identifier"]


def test_scope_hides_unassigned_customers(client, admin_client, rep_client, create_user):
    other_rep = create_user(
        "rep2", "rep2@example.com", "RepPass!123", role_code="SALES_REP"
    )
    _make_customer_assigned(admin_client, assigned_user_id=other_rep)

    response = rep_client.get("/api/clients")
    assert response.status_code == 200
    assert response.data["count"] == 0


def test_scope_allows_own_assigned_customers(admin_client, rep_client, sales_rep_user):
    created = _make_customer_assigned(admin_client, assigned_user_id=None)
    claim = admin_client.post(
        f"/api/clients/{created['customer_id']}/transfer",
        {"assigned_user_id": sales_rep_user},
        format="json",
    )
    assert claim.status_code == 200, claim.content
    assert claim.data["assigned_user_id"] == sales_rep_user

    response = rep_client.get("/api/clients")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["customer_id"] == created["customer_id"]


def test_admin_sees_all_customers(admin_client):
    _make_customer_assigned(admin_client)
    response = admin_client.get("/api/clients")
    assert response.status_code == 200
    assert response.data["count"] >= 1
