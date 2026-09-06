"""Apply phase SQL scripts to the CRM MySQL database.

Reads credentials from Backend/.env (or environment) at runtime so they are
never embedded in commands or logs. Statements are sent with
CLIENT.MULTI_STATEMENTS so multi-statement scripts (including `USE db;`)
execute correctly in order.

Usage:
    .venv\\Scripts\\python.exe deploy\\apply_sql.py deploy\\sql\\002_...sql
    .venv\\Scripts\\python.exe deploy\\apply_sql.py deploy\\sql\\003_...sql
    .venv\\Scripts\\python.exe deploy\\apply_sql.py --all
    .venv\\Scripts\\python.exe deploy\\apply_sql.py --check   # phase probes only
"""

import os
import sys

import pymysql
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SQL_DIR = os.path.join(BASE_DIR, "deploy", "sql")


def db_config():
    return {
        "host": os.getenv("CRM_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("CRM_DB_PORT", "3306")),
        "user": os.getenv("CRM_DB_USER", "root"),
        "password": os.getenv("CRM_DB_PASSWORD", ""),
        "database": os.getenv("CRM_DB_NAME", "crm_v2"),
        "charset": "utf8mb4",
        "autocommit": True,
        "client_flag": pymysql.constants.CLIENT.MULTI_STATEMENTS,
    }


def connect():
    return pymysql.connect(**db_config())


def has_column(conn, table, column):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (table, column),
        )
        return cur.fetchone()[0] > 0


def run_script(conn, path):
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()
    with conn.cursor() as cur:
        cur.execute(script)
        while cur.nextset():
            pass
        return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION(), DATABASE()")
            ver, db = cur.fetchone()
        print(f"[connected] MySQL {ver} database '{db}'")

        if "--check" in argv:
            print(f"  customers.account_number_status  -> {has_column(conn, 'customers', 'account_number_status')}")
            print(f"  customers.customer_number       -> {has_column(conn, 'customers', 'customer_number')}")
            print(f"  customer_addresses.address      -> {has_column(conn, 'customer_addresses', 'address')}")
            for table in (
                "branches", "contact_roles", "relationship_types", "activity_types",
                "document_types", "account_number_sequences", "activities",
                "activity_notes", "timeline_events", "sms_messages", "email_messages",
                "call_logs", "communication_provider_events", "documents",
                "document_versions", "role_access_policies", "user_access_policies",
                "portal_users", "portal_authentication_credentials", "portal_permissions",
                "portal_user_permissions", "portal_user_customers", "portal_sessions",
                "portal_password_reset_tokens",
            ):
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))
                    exists = cur.fetchone()[0] > 0
                print(f"  {table:32s} -> {'present' if exists else 'MISSING'}")
            return 0

        files = list(args)
        if "--all" in argv or not files:
            files = sorted(
                n for n in os.listdir(SQL_DIR)
                if n.endswith(".sql") and n[0].isdigit()
            )
        if not files:
            print("No scripts to run.")
            return 0

        for rel in files:
            candidate = rel if os.path.isabs(rel) or os.path.dirname(rel) else os.path.join(SQL_DIR, rel)
            path = candidate if os.path.exists(candidate) else os.path.join(SQL_DIR, rel)
            if not os.path.exists(path):
                print(f"! {rel}: file not found {path}")
                continue
            # Phase 002 is schema DDL; skip if already applied (non-idempotent ALTERs).
            if os.path.basename(rel).startswith("002") and has_column(conn, "customers", "account_number_status"):
                print(f"- 002 skipped: customers.account_number_status already exists")
                continue
            # Phase 006 adds customer_addresses.address; skip if already applied.
            if os.path.basename(rel).startswith("006") and has_column(conn, "customer_addresses", "address"):
                print(f"- 006 skipped: customer_addresses.address already exists")
                continue
            try:
                run_script(conn, path)
                print(f"  applied: {os.path.basename(rel)}")
            except pymysql.err.MySQLError as exc:
                print(f"X {os.path.basename(rel)}: {exc}")
                return 2
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))