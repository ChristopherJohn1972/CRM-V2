from django.core.files.uploadedfile import SimpleUploadedFile


def _create_business(client, name="Acme Ltd"):
    response = client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": name,
            "email": f"{name.lower().replace(' ', '')}@example.com",
            "phone": "+254711111111",
            "industry": "Retail",
            "customer_category": "SME",
            "segment": "Retail",
            "addresses": [
                {
                    "address_type": "OFFICE",
                    "address": "Kimathi Street",
                    "city": "Nairobi",
                    "country": "Kenya",
                    "is_primary": True,
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def test_create_customer_returns_generated_account_number(admin_client):
    data = _create_business(admin_client)
    assert data["account_number"] == "0001"
    assert data["_360_url"] == "/api/clients/1/360"
    assert data["status"] == "PROSPECT"


def test_create_individual_customer(admin_client):
    response = admin_client.post(
        "/api/clients",
        {
            "customer_type": "INDIVIDUAL",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "phone": "+254722222222",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    assert response.data["legal_name"] == "Jane Doe"


def test_create_business_requires_legal_name(admin_client):
    response = admin_client.post(
        "/api/clients",
        {"customer_type": "BUSINESS", "email": "x@example.com"},
        format="json",
    )
    assert response.status_code == 400


def test_list_and_filter_customers(admin_client):
    _create_business(admin_client, "One")
    _create_business(admin_client, "Two")
    response = admin_client.get("/api/clients?status=PROSPECT&search=One")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["legal_name"] == "One"


def test_patch_customer_and_version_increment(admin_client):
    data = _create_business(admin_client, "Version Me")
    response = admin_client.patch(
        f"/api/clients/{data['customer_id']}",
        {"phone": "+254733333333", "version": data["version"]},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.data["version"] == data["version"] + 1


def test_status_transition_rules(admin_client):
    data = _create_business(admin_client, "Lifecycle")
    ok = admin_client.post(
        f"/api/clients/{data['customer_id']}/status",
        {"status": "ONBOARDING", "reason": "KYC in progress"},
        format="json",
    )
    assert ok.status_code == 200, ok.content
    assert ok.data["status"] == "ONBOARDING"

    bad = admin_client.post(
        f"/api/clients/{data['customer_id']}/status",
        {"status": "CLOSED", "reason": "jump"},
        format="json",
    )
    assert bad.status_code == 400


def test_close_customer(admin_client):
    data = _create_business(admin_client, "To Close")
    response = admin_client.post(
        f"/api/clients/{data['customer_id']}/close", {"reason": "Business closed"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["status"] == "CLOSED"
    assert response.data["account_number"] == data["account_number"]


def test_sensitive_fields_masked_for_rep(admin_client, rep_client, sales_rep_user):
    created = admin_client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": "Sensitive Co",
            "tax_identifier": "P012345678Z",
            "registration_number": "REG-123456",
        },
        format="json",
    ).data
    claim = admin_client.post(
        f"/api/clients/{created['customer_id']}/transfer",
        {"assigned_user_id": sales_rep_user},
        format="json",
    )
    assert claim.status_code == 200, claim.content
    assert created["tax_identifier"] == "P012345678Z"

    masked = rep_client.get(f"/api/clients/{created['customer_id']}")
    assert masked.status_code == 200, masked.content
    assert "***" in masked.data["tax_identifier"]
    assert masked.data["tax_identifier"] != "P012345678Z"

    full = admin_client.get(f"/api/clients/{created['customer_id']}")
    assert full.data["tax_identifier"] == "P012345678Z"


def test_contact_crud(admin_client):
    data = _create_business(admin_client, "Contacts Co")
    cid = data["customer_id"]

    created = admin_client.post(
        f"/api/clients/{cid}/contacts",
        {
            "first_name": "Alice",
            "last_name": "Muthoni",
            "email": "alice@contacts.co",
            "phone": "+254744444444",
            "is_primary": True,
        },
        format="json",
    )
    assert created.status_code == 201, created.content

    updated = admin_client.patch(
        f"/api/clients/{cid}/contacts/{created.data['contact_id']}",
        {"job_title": "Finance Manager"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.data["job_title"] == "Finance Manager"

    listed = admin_client.get(f"/api/clients/{cid}/contacts")
    assert listed.status_code == 200
    assert len(listed.data) == 1

    deleted = admin_client.delete(
        f"/api/clients/{cid}/contacts/{created.data['contact_id']}"
    )
    assert deleted.status_code == 204


def test_relationship_rules(admin_client):
    a = _create_business(admin_client, "Parent Co")
    b = _create_business(admin_client, "Child Co")

    self_link = admin_client.post(
        f"/api/clients/{a['customer_id']}/relationships",
        {
            "related_customer_id": a["customer_id"],
            "relationship_type": "parent_company",
        },
        format="json",
    )
    assert self_link.status_code == 403

    valid = admin_client.post(
        f"/api/clients/{a['customer_id']}/relationships",
        {
            "related_customer_id": b["customer_id"],
            "relationship_type": "parent_company",
        },
        format="json",
    )
    assert valid.status_code == 201, valid.content
    assert valid.data["related_account_number"] == b["account_number"]


def test_document_upload_and_download(admin_client):
    data = _create_business(admin_client, "Docs Co")
    cid = data["customer_id"]

    uploaded = admin_client.post(
        f"/api/clients/{cid}/documents",
        data={
            "document_type": "contract",
            "access_classification": "INTERNAL",
            "file": SimpleUploadedFile(
                "contract.pdf", b"%PDF-1.4 sample content", content_type="application/pdf"
            ),
        },
        format="multipart",
    )
    assert uploaded.status_code == 201, uploaded.content
    document_id = uploaded.data["document_id"]
    assert uploaded.data["current_version"] == 1

    download = admin_client.get(f"/api/clients/{cid}/documents/{document_id}/download")
    assert download.status_code == 200, download.content
    assert download.data["version"] == 1
    assert download.data["url"].startswith("/api/documents/serve")

    versions = admin_client.get(f"/api/clients/{cid}/documents/{document_id}/versions")
    assert versions.status_code == 200
    assert len(versions.data) == 1


def test_activity_create_and_complete(admin_client):
    data = _create_business(admin_client, "Activity Co")
    cid = data["customer_id"]

    created = admin_client.post(
        f"/api/clients/{cid}/activities",
        {
            "activity_type": "call",
            "subject": "Introductory call",
            "priority": "HIGH",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    activity_id = created.data["activity_id"]

    completed = admin_client.post(f"/api/clients/{cid}/activities/{activity_id}/complete")
    assert completed.status_code == 200, completed.content
    assert completed.data["status"] == "COMPLETED"
    assert completed.data["completed_at"] is not None


def test_sms_send_uses_dev_gateway(admin_client):
    data = _create_business(admin_client, "SMS Co")
    cid = data["customer_id"]

    response = admin_client.post(
        f"/api/clients/{cid}/sms",
        {"to_number": "+254755555555", "body": "Welcome!"},
        format="json",
    )
    assert response.status_code == 201, response.content
    assert response.data["status"] in ("SENT", "QUEUED")


def test_communications_history(admin_client):
    data = _create_business(admin_client, "Comms Co")
    cid = data["customer_id"]
    admin_client.post(
        f"/api/clients/{cid}/sms",
        {"to_number": "+254755555555", "body": "Hello"},
        format="json",
    )
    history = admin_client.get(f"/api/clients/{cid}/communications")
    assert history.status_code == 200
    assert len(history.data["results"]) >= 1
    assert history.data["results"][0]["channel"] == "sms"


def test_timeline_reflects_customer_created(admin_client):
    data = _create_business(admin_client, "Timeline Co")
    cid = data["customer_id"]
    timeline = admin_client.get(f"/api/clients/{cid}/timeline")
    assert timeline.status_code == 200
    event_types = [e["event_type"] for e in timeline.data["results"]]
    assert "CustomerCreated" in event_types


def test_customer_360_summary(admin_client):
    data = _create_business(admin_client, "Full Co")
    cid = data["customer_id"]
    admin_client.post(
        f"/api/clients/{cid}/contacts",
        {"first_name": "Bob", "last_name": "Wanjiku"},
        format="json",
    )
    admin_client.post(
        f"/api/clients/{cid}/activities",
        {"activity_type": "task", "subject": "Follow up"},
        format="json",
    )

    response = admin_client.get(f"/api/clients/{cid}/360")
    assert response.status_code == 200, response.content
    assert response.data["account_number"] == data["account_number"]
    assert response.data["summary"]["contacts"] == 1
    assert response.data["summary"]["activities"] == 1
    assert response.data["summary"]["documents"] == 0
    assert response.data["accounting"]["available"] is False
    assert response.data["urls"]["360"] == f"/api/clients/{cid}/360"


def test_delete_customer_soft_deletes(admin_client):
    data = _create_business(admin_client, "Soft Delete")
    response = admin_client.delete(f"/api/clients/{data['customer_id']}")
    assert response.status_code == 204
    detail = admin_client.get(f"/api/clients/{data['customer_id']}")
    assert detail.status_code == 404
