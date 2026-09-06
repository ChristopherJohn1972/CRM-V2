import sqlalchemy as sa

from iam.models import (
    AccessPolicy,
    Role,
    RoleAccessPolicy,
    RolePermission,
    User,
    UserAccessPolicy,
    UserRole,
)


def _role(user_id):
    from common.db import SessionLocal

    session = SessionLocal()
    try:
        role_id = session.execute(
            sa.select(UserRole.role_id).where(UserRole.user_id == user_id)
        ).scalar_one_or_none()
        if role_id is None:
            return None, []
        role = session.get(Role, role_id)
        perm_rows = session.execute(
            sa.select(RolePermission).where(RolePermission.role_id == role_id)
        ).scalars().all()
        policy_ids = [
            rp.access_policy_id
            for rp in session.execute(
                sa.select(RoleAccessPolicy).where(RoleAccessPolicy.role_id == role_id)
            ).scalars().all()
        ]
        scope_names = set()
        if policy_ids:
            scope_names = set(
                session.execute(
                    sa.select(AccessPolicy.scope).where(AccessPolicy.access_policy_id.in_(policy_ids))
                ).scalars().all()
            )
        return role, scope_names
    finally:
        session.close()


def _scopes_for_user(user_id):
    from common.db import SessionLocal

    session = SessionLocal()
    try:
        ids = session.execute(
            sa.select(UserAccessPolicy.access_policy_id).where(UserAccessPolicy.user_id == user_id)
        ).scalars().all()
        scope_names = set(
            session.execute(
                sa.select(AccessPolicy.scope).where(AccessPolicy.access_policy_id.in_(ids))
            ).scalars().all()
        )
        return scope_names
    finally:
        session.close()


def _create_customer(client, name):
    response = client.post(
        "/api/clients",
        {
            "customer_type": "BUSINESS",
            "legal_name": name,
            "display_name": name,
            "email": f"{name.lower().replace(' ', '')}@example.com",
            "phone": "+254790000003",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.data


def test_rights_matrix_roles_are_seeded(create_user):
    for role_code in ("SYSTEM_ADMINISTRATOR", "CRM_MANAGER", "ACCOUNT_MANAGER", "CUSTOMER_SERVICE"):
        user_id = create_user(
            f"matrix.{role_code.lower()}", f"matrix.{role_code.lower()}@example.com",
            "MatrixPass!123", role_code=role_code,
        )
        role, _scopes = _role(user_id)
        assert role is not None, role_code
        assert role.code == role_code


def test_system_administrator_has_all_access(admin_client, client, create_user, db):
    _create_customer(admin_client, "Global Co")
    user_id = create_user("sysadmin1", "sysadmin1@example.com", "MatrixPass!123", role_code="SYSTEM_ADMINISTRATOR")
    scopes = _scopes_for_user(user_id)
    assert "ALL" in scopes

    login = client.post(
        "/api/auth/login", {"username": "sysadmin1", "password": "MatrixPass!123"}, format="json"
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    # Full visibility regardless of ownership.
    list_response = client.get("/api/clients")
    assert list_response.status_code == 200
    assert list_response.data["count"] == 1


def test_account_manager_scoped_to_assigned(admin_client, client, create_user, sales_rep_user):
    mine = _create_customer(admin_client, "Mine Co")
    _create_customer(admin_client, "Theirs Co")
    user_id = create_user(
        "acctmgr1", "acctmgr1@example.com", "MatrixPass!123", role_code="ACCOUNT_MANAGER"
    )

    from common.db import SessionLocal

    session = SessionLocal()
    try:
        from clients.models import Customer

        c = session.get(Customer, mine["customer_id"])
        c.assigned_user_id = user_id
        session.commit()
    finally:
        session.close()

    login = client.post(
        "/api/auth/login", {"username": "acctmgr1", "password": "MatrixPass!123"}, format="json"
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    list_response = client.get("/api/clients")
    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert list_response.data["results"][0]["customer_id"] == mine["customer_id"]

    denied = client.get(f"/api/clients/{mine['customer_id'] + 1}")
    assert denied.status_code == 403


def test_crm_manager_department_scope_and_iam(admin_client, client, create_user):
    user_id = create_user("crmmgr1", "crmmgr1@example.com", "MatrixPass!123", role_code="CRM_MANAGER")
    scopes = _scopes_for_user(user_id)
    assert "DEPARTMENT" in scopes

    login = client.post(
        "/api/auth/login", {"username": "crmmgr1", "password": "MatrixPass!123"}, format="json"
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    # CRM_MANAGER carries iam.user.manage (internal account administration).
    response = client.post(
        "/api/portal/users",
        {
            "username": "crm.portal",
            "email": "crm.portal@example.com",
            "first_name": "CRM",
            "last_name": "Portal",
        },
        format="json",
    )
    assert response.status_code == 201, response.content


def test_customer_service_assigned_and_team_scope(admin_client, client, create_user):
    user_id = create_user(
        "custsvc1", "custsvc1@example.com", "MatrixPass!123", role_code="CUSTOMER_SERVICE"
    )
    scopes = _scopes_for_user(user_id)
    assert "ASSIGNED" in scopes and "TEAM" in scopes

    login = client.post(
        "/api/auth/login", {"username": "custsvc1", "password": "MatrixPass!123"}, format="json"
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['token']}")

    # Support role cannot create customers or manage portal users.
    assert client.get("/api/clients").status_code == 200
    create = client.post(
        "/api/clients",
        {"customer_type": "BUSINESS", "legal_name": "No Create", "display_name": "No Create"},
        format="json",
    )
    assert create.status_code == 403
    portal = client.post(
        "/api/portal/users",
        {"username": "x", "email": "x@example.com", "first_name": "X", "last_name": "Y"},
        format="json",
    )
    assert portal.status_code == 403