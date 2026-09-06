import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load Backend/.env values into os.environ so tests use the configured
# credentials. Must run BEFORE django.setup(): settings.py also calls
# load_dotenv with override=False, which would otherwise leave the empty
# defaults set below in charge.
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# Force the test schema in the test process; never point tests at the live DB.
os.environ["CRM_DB_NAME"] = "crm_v2_test"
os.environ["CRM_STORAGE_BACKEND"] = "dev"
os.environ.setdefault("CRM_STORAGE_ROOT", str(Path(os.environ.get("TEMP", ".")) / "crm_v2_test_storage"))
for _key in ("CRM_DB_HOST", "CRM_DB_PORT", "CRM_DB_USER", "CRM_DB_PASSWORD"):
    os.environ.setdefault(_key, os.getenv(_key, ""))


def _db_params():
    return {
        "host": os.getenv("CRM_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("CRM_DB_PORT", "3306")),
        "user": os.getenv("CRM_DB_USER", "root"),
        "password": os.getenv("CRM_DB_PASSWORD", ""),
        "charset": "utf8mb4",
    }


@pytest.fixture(scope="session", autouse=True)
def test_database():
    import django

    django.setup()

    import pymysql
    from pymysql.constants import CLIENT

    params = _db_params()
    server = pymysql.connect(**params, client_flag=CLIENT.MULTI_STATEMENTS)
    try:
        with server.cursor() as cur:
            cur.execute("DROP DATABASE IF EXISTS `crm_v2_test`")
            cur.execute(
                "CREATE DATABASE `crm_v2_test` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        server.commit()
    finally:
        server.close()

    db = pymysql.connect(
        database="crm_v2_test", client_flag=CLIENT.MULTI_STATEMENTS, **params
    )
    try:
        with db.cursor() as cur:
            scripts = [
                BASE_DIR.parent / "crmv2_database.sql",
                BASE_DIR / "deploy" / "sql" / "002_clients_phase_schema.sql",
                BASE_DIR / "deploy" / "sql" / "003_seed_clients_phase.sql",
                BASE_DIR / "deploy" / "sql" / "004_portal_phase_schema.sql",
                BASE_DIR / "deploy" / "sql" / "005_seed_portal_test_roles.sql",
                BASE_DIR / "deploy" / "sql" / "006_client_contract_cleanup.sql",
                BASE_DIR / "deploy" / "sql" / "007_remove_legacy_test_customers.sql",
                BASE_DIR / "deploy" / "sql" / "008_reset_customer_account_sequence.sql",
                BASE_DIR / "deploy" / "sql" / "009_renumber_customer.sql",
                BASE_DIR / "deploy" / "sql" / "010_revert_account_number.sql",
                BASE_DIR / "deploy" / "sql" / "011_add_customer_soft_delete.sql",
                BASE_DIR / "deploy" / "sql" / "012_portal_client_features.sql",
                BASE_DIR / "deploy" / "sql" / "013_quote_studio_schema.sql",
                BASE_DIR / "deploy" / "sql" / "014_quote_studio_seed.sql",
            ]
            for path in scripts:
                sql = path.read_text(encoding="utf-8")
                sql = sql.replace("crm_v2", "crm_v2_test")
                cur.execute(sql)
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def db():
    from common.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


# Transactional tables wiped between tests so the whole suite shares the
# seeded reference data (roles/permissions/policies/config tables stay intact)
# while every test starts from empty transactional rows and a reset account
# number counter. TRUNCATE also resets AUTO_INCREMENT -> customer_id==1.
_TRUNCATE_PREFIX = [
    "users",
    "authentication_credentials",
    "user_roles",
    "user_access_policies",
    "user_permissions",
    "user_sessions",
    "customers",
    "customer_contacts",
    "customer_addresses",
    "customer_relationships",
    "activities",
    "activity_notes",
    "timeline_events",
    "sms_messages",
    "email_messages",
    "call_logs",
    "communication_provider_events",
    "documents",
    "document_versions",
    "audit_logs",
    "portal_users",
    "portal_authentication_credentials",
    "portal_user_permissions",
    "portal_user_customers",
    "portal_sessions",
    "portal_password_reset_tokens",
    "payments",
    "invoices",
    "payment_receipts",
    "complaints",
    "complaint_messages",
    "complaint_attachments",
    "complaint_status_history",
    "notifications",
    "rewards",
    "reward_redemptions",
    "quote_items",
    "quote_versions",
    "quote_documents",
    "quote_approvals",
    "quote_events",
    "quote_portal_access",
    "quote_client_responses",
    "quotes",
    "quote_number_sequences",
]

_TRUNCATE_SQL = (
    "SET FOREIGN_KEY_CHECKS=0; "
    + "; ".join(f"TRUNCATE TABLE `{t}`" for t in _TRUNCATE_PREFIX)
    + "; SET FOREIGN_KEY_CHECKS=1; "
    + "UPDATE `account_number_sequences` SET `last_value`=0 WHERE `bucket`='CUSTOMER';"
    + "UPDATE `quote_number_sequences` SET `last_value`=0 WHERE `bucket`='QUOTE';"
    + "UPDATE `portal_sequences` SET `last_value`=0;"
)


@pytest.fixture(autouse=True)
def clean_between_tests():
    import pymysql
    from pymysql.constants import CLIENT

    conn = pymysql.connect(
        database="crm_v2_test",
        client_flag=CLIENT.MULTI_STATEMENTS,
        autocommit=True,
        **_db_params(),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(_TRUNCATE_SQL)
            while cur.nextset():
                pass
    finally:
        conn.close()
    yield


@pytest.fixture()
def client():
    from rest_framework.test import APIClient

    return APIClient()


def _create_user(username, email, password, role_code=None, first_name="Test", last_name="User"):
    import sqlalchemy as sa

    from common.db import SessionLocal
    from iam.models import (
        AccessPolicy,
        AuthenticationCredential,
        Role,
        RoleAccessPolicy,
        RolePermission,
        User,
        UserAccessPolicy,
        UserRole,
    )
    from iam.services import hash_password

    session = SessionLocal()
    try:
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            status="ACTIVE",
        )
        session.add(user)
        session.flush()
        session.add(
            AuthenticationCredential(
                user_id=user.user_id, password_hash=hash_password(password)
            )
        )
        if role_code:
            role = session.execute(
                sa.select(Role).where(Role.code == role_code)
            ).scalar_one_or_none()
            if role:
                session.add(UserRole(user_id=user.user_id, role_id=role.role_id))
                policies = session.execute(
                    sa.select(RoleAccessPolicy).where(
                        RoleAccessPolicy.role_id == role.role_id
                    )
                ).scalars().all()
                for rp in policies:
                    session.add(
                        UserAccessPolicy(
                            user_id=user.user_id, access_policy_id=rp.access_policy_id
                        )
                    )
        session.commit()
        return user.user_id
    finally:
        session.close()


@pytest.fixture()
def admin_user():
    return _create_user("admin", "admin@example.com", "AdminPass!123", role_code="SUPER_ADMIN")


@pytest.fixture()
def sales_rep_user():
    return _create_user(
        "rep1", "rep1@example.com", "RepPass!123", role_code="SALES_REP"
    )


@pytest.fixture()
def sales_manager_user():
    return _create_user(
        "mgr1", "mgr1@example.com", "MgrPass!123", role_code="SALES_MANAGER"
    )


@pytest.fixture()
def login(client):
    def _login(username, password):
        response = client.post(
            "/api/auth/login", {"username": username, "password": password}, format="json"
        )
        assert response.status_code == 200, response.content
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
        return response.data

    return _login


def _authenticated_client(username, password):
    """Return an APIClient logged in as the given user.

    Each caller gets its own client so separate personas never share tokens
    (a shared client's credentials would be overwritten by the last login).
    """
    from rest_framework.test import APIClient

    client = APIClient()
    response = client.post(
        "/api/auth/login", {"username": username, "password": password}, format="json"
    )
    assert response.status_code == 200, response.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
    return client


@pytest.fixture()
def create_user():
    return _create_user


@pytest.fixture()
def admin_client(admin_user):
    return _authenticated_client("admin", "AdminPass!123")


@pytest.fixture()
def rep_client(sales_rep_user):
    return _authenticated_client("rep1", "RepPass!123")


@pytest.fixture()
def manager_client(sales_manager_user):
    return _authenticated_client("mgr1", "MgrPass!123")
