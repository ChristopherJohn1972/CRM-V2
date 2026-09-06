"""Read-only trace of the CRM client records shown on the Clients screen.

Prints an origin/ownership/visibility matrix for the given account numbers
(defaults to the exposed 0001/0002/0003) against the configured database
(live `crm_v2` unless CRM_DB_NAME overrides it). Makes NO writes.

Usage:
    .venv\\Scripts\\python.exe deploy\\trace_clients.py
    .venv\\Scripts\\python.exe deploy\\trace_clients.py 0001 0002 0003
"""

import os
import sys

import pymysql
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def db_config():
    return {
        "host": os.getenv("CRM_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("CRM_DB_PORT", "3306")),
        "user": os.getenv("CRM_DB_USER", "root"),
        "password": os.getenv("CRM_DB_PASSWORD", ""),
        "database": os.getenv("CRM_DB_NAME", "crm_v2"),
        "charset": "utf8mb4",
    }


def main():
    account_numbers = sys.argv[1:] or ["0001", "0002", "0003"]
    conn = pymysql.connect(**db_config())
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE()")
            print(f"[connected] database '{cur.fetchone()[0]}'")
            placeholders = ", ".join(["%s"] * len(account_numbers))
            cur.execute(
                f"""
                SELECT
                    c.customer_id,
                    c.customer_number,
                    c.status,
                    c.created_at,
                    c.updated_at,
                    c.created_by,
                    cu.username            AS created_by_username,
                    c.assigned_user_id,
                    au.username            AS assigned_username,
                    c.assigned_team_id,
                    t.name                 AS assigned_team_name,
                    c.branch_id,
                    b.name                 AS branch_name,
                    b.department_id,
                    d.name                 AS department_name
                FROM customers c
                LEFT JOIN users cu  ON cu.user_id  = c.created_by
                LEFT JOIN users au  ON au.user_id  = c.assigned_user_id
                LEFT JOIN teams t   ON t.team_id   = c.assigned_team_id
                LEFT JOIN branches b ON b.branch_id = c.branch_id
                LEFT JOIN departments d ON d.department_id = b.department_id
                WHERE c.customer_number IN ({placeholders})
                ORDER BY c.customer_number
                """,
                tuple(account_numbers),
            )
            rows = cur.fetchall()
        if not rows:
            print(f"No customers found for account numbers: {account_numbers}")
            print("Tip: unassigned/orphaned records are still visible to ALL scope.")
            return 1
        if "--deps" in sys.argv:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT customer_id FROM customers "
                    f"WHERE customer_number IN ({placeholders})",
                    tuple(account_numbers),
                )
                ids = [r[0] for r in cur.fetchall()]
                id_ph = ", ".join(["%s"] * len(ids))
                deps = [
                    ("customer_contacts", "customer_id", False),
                    ("customer_addresses", "customer_id", False),
                    ("customer_relationships", "customer_id", False),
                    ("customer_relationships", "related_customer_id", False),
                    ("activities", "customer_id", False),
                    ("timeline_events", "customer_id", False),
                    ("sms_messages", "customer_id", False),
                    ("email_messages", "customer_id", False),
                    ("call_logs", "customer_id", False),
                    ("documents", "customer_id", False),
                    ("portal_user_customers", "customer_id", False),
                ]
                print("\n--- dependency check (rows referencing these customers) ---")
                for table, col, _ in deps:
                    try:
                        cur.execute(
                            f"SELECT COUNT(*) FROM `{table}` WHERE `{col}` IN ({id_ph})",
                            tuple(ids),
                        )
                        print(f"  {table}.{col} = {cur.fetchone()[0]}")
                    except pymysql.err.OperationalError as exc:
                        print(f"  {table}.{col}  (skip: {exc.args[1]})")
            return 0
        cols = [
            "customer_id", "customer_number", "status", "created_at", "updated_at",
            "created_by", "created_by_username", "assigned_user_id", "assigned_username",
            "assigned_team_id", "assigned_team_name", "branch_id", "branch_name",
            "department_id", "department_name",
        ]
        widths = [len(c) for c in cols]
        for r in rows:
            for i, v in enumerate(r):
                widths[i] = max(widths[i], len(str(v)))
        header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
        print(header)
        print("-" * len(header))
        for r in rows:
            print(" | ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)))

        # Origin evidence: audit + address counts for the same record set.
        with conn.cursor() as cur:
            placeholders = ", ".join(["%s"] * len(account_numbers))
            cur.execute(
                f"""
                SELECT c.customer_number, a.action, a.created_at, a.metadata
                FROM audit_logs a
                JOIN customers c ON c.customer_id = a.resource_id
                WHERE a.resource_type = 'customers' AND c.customer_number IN ({placeholders})
                ORDER BY c.customer_number, a.audit_log_id
                """,
                tuple(account_numbers),
            )
            print("\n--- audit trail (origin evidence) ---")
            for r in cur.fetchall():
                print(f"  {r[0]}  {r[1]}  {r[2]}  {r[3]}")
            cur.execute(
                f"""
                SELECT c.customer_number, COUNT(a.address_id)
                FROM customers c
                LEFT JOIN customer_addresses a ON a.customer_id = c.customer_id
                WHERE c.customer_number IN ({placeholders})
                GROUP BY c.customer_number
                """,
                tuple(account_numbers),
            )
            print("\n--- addresses per record ---")
            for r in cur.fetchall():
                print(f"  {r[0]}  addresses={r[1]}")
            try:
                cur.execute(
                    "SELECT `bucket`, `last_value`, `min_length` "
                    "FROM `account_number_sequences`"
                )
                print("\n--- account number sequence ---")
                for r in cur.fetchall():
                    print(f"  {r[0]}: last_value={r[1]} (min_length={r[2]})")
            except pymysql.err.MySQLError as exc:
                print(f"\n--- account number sequence ---  (skip: {exc.args[1]})")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())