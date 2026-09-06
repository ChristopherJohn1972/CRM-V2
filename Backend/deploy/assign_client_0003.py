"""One-time data fix: assign client 0003 to the ACCOUNT_MANAGER operator.

ASSIGNED-scope roles require the operator to own the record (assigned_user_id).
This script finds the first user with the ACCOUNT_MANAGER role and transfers
client 0003 to them. Idempotent: only runs if 0003 is still unassigned and
at least one ACCOUNT_MANAGER user exists.

Usage:
    .venv\\Scripts\\python.exe deploy\\assign_client_0003.py
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
    conn = pymysql.connect(**db_config())
    try:
        with conn.cursor() as cur:
            # Find the ACCOUNT_MANAGER role
            cur.execute(
                "SELECT role_id FROM roles WHERE code = 'ACCOUNT_MANAGER' LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                print("No ACCOUNT_MANAGER role found. Assign the role to an operator first.")
                return 1
            role_id = row[0]

            # Find a user with that role
            cur.execute(
                "SELECT u.user_id, u.username FROM user_roles ur "
                "JOIN users u ON u.user_id = ur.user_id "
                "WHERE ur.role_id = %s LIMIT 1",
                (role_id,),
            )
            user = cur.fetchone()
            if user is None:
                print("No operator has the ACCOUNT_MANAGER role yet.")
                print("Assign it first: POST /api/operators/{id}/roles {\"role_codes\": [\"ACCOUNT_MANAGER\"]}")
                return 1
            user_id, username = user
            print(f"ACCOUNT_MANAGER operator: user_id={user_id} ({username})")

            # Transfer client 0003 if unassigned
            cur.execute(
                "SELECT customer_id, assigned_user_id FROM customers "
                "WHERE customer_number = '0003'"
            )
            c = cur.fetchone()
            if c is None:
                print("Client 0003 not found.")
                return 1
            cid, current_owner = c
            if current_owner is not None:
                print(f"Client 0003 already assigned to user_id={current_owner}. Skipping.")
                return 0

            cur.execute(
                "UPDATE customers SET assigned_user_id = %s, updated_by = %s, "
                "version = version + 1, updated_at = CURRENT_TIMESTAMP "
                "WHERE customer_id = %s",
                (user_id, user_id, cid),
            )
            conn.commit()
            print(f"Client 0003 transferred to user_id={user_id} ({username}).")
            print("The operator can now see client 0003 under ASSIGNED scope.")
            return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())