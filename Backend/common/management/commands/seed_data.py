import os

import sqlalchemy as sa
from django.core.management.base import BaseCommand

from common.db import SessionLocal
from iam.models import (
    AccessPolicy,
    AuthenticationCredential,
    Permission,
    Role,
    RoleAccessPolicy,
    RolePermission,
    User,
    UserAccessPolicy,
    UserRole,
)
from iam.services import hash_password


ACCESS_POLICIES = [
    ("Global All", "GLOBAL_ALL", "ALL", "Unrestricted access to all permitted records"),
    ("Department Scope", "SCOPE_DEPARTMENT", "DEPARTMENT", "Access limited to own department records"),
    ("Team Scope", "SCOPE_TEAM", "TEAM", "Access limited to team records"),
    ("Assigned Scope", "SCOPE_ASSIGNED", "ASSIGNED", "Access limited to assigned/own team records"),
    ("Own Scope", "SCOPE_OWN", "OWN", "Access limited to personally assigned records"),
]

PERMISSIONS = [
    ("Clients: create customer", "clients.customer.create", "clients", "customer:create"),
    ("Clients: read customer", "clients.customer.read", "clients", "customer:read"),
    ("Clients: update customer", "clients.customer.update", "clients", "customer:update"),
    ("Clients: delete customer", "clients.customer.delete", "clients", "customer:delete"),
    ("Clients: read sensitive fields", "clients.customer.sensitive.read", "clients", "customer:sensitive_read"),
    ("Clients: change status", "clients.customer.status.change", "clients", "customer:status_change"),
    ("Clients: transfer ownership", "clients.customer.ownership.transfer", "clients", "customer:ownership_transfer"),
    ("Clients: create contact", "clients.contact.create", "clients", "contact:create"),
    ("Clients: read contact", "clients.contact.read", "clients", "contact:read"),
    ("Clients: update contact", "clients.contact.update", "clients", "contact:update"),
    ("Clients: delete contact", "clients.contact.delete", "clients", "contact:delete"),
    ("Clients: create relationship", "clients.relationship.create", "clients", "relationship:create"),
    ("Clients: read relationship", "clients.relationship.read", "clients", "relationship:read"),
    ("Clients: delete relationship", "clients.relationship.delete", "clients", "relationship:delete"),
    ("Clients: write address", "clients.address.write", "clients", "address:write"),
    ("Activities: read", "activities.activity.read", "activities", "activity:read"),
    ("Activities: create", "activities.activity.create", "activities", "activity:create"),
    ("Activities: update", "activities.activity.update", "activities", "activity:update"),
    ("Activities: complete", "activities.activity.complete", "activities", "activity:complete"),
    ("Activities: read notes", "activities.note.read", "activities", "note:read"),
    ("Activities: create note", "activities.note.create", "activities", "note:create"),
    ("Activities: update note", "activities.note.update", "activities", "note:update"),
    ("Activities: delete note", "activities.note.delete", "activities", "note:delete"),
    ("Comms: read sms", "communications.sms.read", "communications", "sms:read"),
    ("Comms: send sms", "communications.sms.send", "communications", "sms:send"),
    ("Comms: read email", "communications.email.read", "communications", "email:read"),
    ("Comms: send email", "communications.email.send", "communications", "email:send"),
    ("Comms: read calls", "communications.call.read", "communications", "call:read"),
    ("Comms: log call", "communications.call.log", "communications", "call:log"),
    ("Comms: process webhooks", "communications.webhook.process", "communications", "webhook:process"),
    ("Documents: read", "documents.document.read", "documents", "document:read"),
    ("Documents: read public", "documents.document.read.public", "documents", "document:read_public"),
    ("Documents: read internal", "documents.document.read.internal", "documents", "document:read_internal"),
    ("Documents: read restricted", "documents.document.read.restricted", "documents", "document:read_restricted"),
    ("Documents: read confidential", "documents.document.read.confidential", "documents", "document:read_confidential"),
    ("Documents: create", "documents.document.create", "documents", "document:create"),
    ("Documents: update", "documents.document.update", "documents", "document:update"),
    ("Documents: download", "documents.document.download", "documents", "document:download"),
    ("Accounting: read summary", "accounting.summary.read", "accounting", "summary:read"),
    ("Accounting: read transactions", "accounting.transactions.read", "accounting", "transactions:read"),
    ("Customer360: view", "customer360.view", "customer360", "360:view"),
    ("Customer360: manage portal users", "portal.user.manage", "customer360", "portal:user_manage"),
    ("IAM: manage users", "iam.user.manage", "iam", "user:manage"),
    ("IAM: manage roles", "iam.role.manage", "iam", "role:manage"),
    ("IAM: audit permissions", "iam.permission.audit", "iam", "permission:audit"),
    ("Portal: view customers", "portal.customer.view", "portal", "customer:view"),
    ("Portal: read credentials", "portal.credential.read", "portal", "credential:read"),
    ("Portal: reset credentials", "portal.credential.reset", "portal", "credential:reset"),
    ("Quotes: create", "quotes.quote.create", "quotes", "quote:create"),
    ("Quotes: read", "quotes.quote.read", "quotes", "quote:read"),
    ("Quotes: update", "quotes.quote.update", "quotes", "quote:update"),
    ("Quotes: delete", "quotes.quote.delete", "quotes", "quote:delete"),
    ("Quotes: send", "quotes.quote.send", "quotes", "quote:send"),
    ("Quotes: duplicate", "quotes.quote.duplicate", "quotes", "quote:duplicate"),
    ("Quotes: calculate", "quotes.quote.calculate", "quotes", "quote:calculate"),
    ("Quotes: submit approval", "quotes.quote.submit_approval", "quotes", "quote:submit_approval"),
    ("Quotes: approve", "quotes.quote.approve", "quotes", "quote:approve"),
    ("Quotes: reject", "quotes.quote.reject", "quotes", "quote:reject"),
    ("Quotes: preview", "quotes.quote.preview", "quotes", "quote:preview"),
    ("Quotes: download pdf", "quotes.quote.download_pdf", "quotes", "quote:download_pdf"),
    ("Quotes: view audit", "quotes.quote.view_audit", "quotes", "quote:view_audit"),
    ("Quotes: convert to order", "quotes.quote.convert_to_order", "quotes", "quote:convert_to_order"),
    ("Quotes: manage templates", "quotes.quote.manage_templates", "quotes", "quote:manage_templates"),
    ("Quotes: manage tax rules", "quotes.quote.manage_tax_rules", "quotes", "quote:manage_tax_rules"),
    ("Quotes: manage payment terms", "quotes.quote.manage_payment_terms", "quotes", "quote:manage_payment_terms"),
    ("Sales Orders: create", "sales_order.sales_order.create", "sales_orders", "sales_order:create"),
    ("Sales Orders: read", "sales_order.sales_order.read", "sales_orders", "sales_order:read"),
    ("Sales Orders: update", "sales_order.sales_order.update", "sales_orders", "sales_order:update"),
    ("Sales Orders: delete", "sales_order.sales_order.delete", "sales_orders", "sales_order:delete"),
    ("Sales Orders: calculate", "sales_order.sales_order.calculate", "sales_orders", "sales_order:calculate"),
    ("Sales Orders: workflow", "sales_order.sales_order.workflow", "sales_orders", "sales_order:workflow"),
    ("Sales Orders: read payments", "sales_order.payment.read", "sales_orders", "payment:read"),
    ("Sales Orders: record payment", "sales_order.payment.record", "sales_orders", "payment:record"),
    ("Sales Orders: confirm payment", "sales_order.payment.confirm", "sales_orders", "payment:confirm"),
    ("Sales Orders: reverse payment", "sales_order.payment.reverse", "sales_orders", "payment:reverse"),
    ("Sales Orders: read receipts", "sales_order.receipt.read", "sales_orders", "receipt:read"),
    ("Sales Orders: void receipt", "sales_order.receipt.void", "sales_orders", "receipt:void"),
    ("Campaigns: view", "campaign.view", "campaigns", "campaign:view"),
    ("Campaigns: create", "campaign.create", "campaigns", "campaign:create"),
    ("Campaigns: edit", "campaign.edit", "campaigns", "campaign:edit"),
    ("Campaigns: delete", "campaign.delete", "campaigns", "campaign:delete"),
    ("Campaigns: generate creative", "campaign.generate_creative", "campaigns", "campaign:generate_creative"),
    ("Campaigns: launch", "campaign.launch", "campaigns", "campaign:launch"),
    ("Campaigns: activate", "campaign.activate", "campaigns", "campaign:activate"),
    ("Leads: view", "lead.view", "leads", "lead:view"),
    ("Leads: create", "lead.create", "leads", "lead:create"),
    ("Leads: edit", "lead.edit", "leads", "lead:edit"),
    ("Leads: delete", "lead.delete", "leads", "lead:delete"),
    ("Leads: assign", "lead.assign", "leads", "lead:assign"),
    ("Referrals: view", "referral.view", "referrals", "referral:view"),
    ("Referrals: manage", "referral.manage", "referrals", "referral:manage"),
    ("Momentum: view", "momentum.view", "momentum", "momentum:view"),
    ("Momentum: manage", "momentum.manage", "momentum", "momentum:manage"),
    ("Event Engine: manage outbox", "event.outbox.manage", "event_engine", "outbox:manage"),
    ("Attribution: view", "attribution.view", "attribution", "attribution:view"),
    ("USSD: view sessions", "ussd.session.view", "ussd", "session:view"),
]

ROLES = [
    ("Super Admin", "SUPER_ADMIN", "Full system access", True),
    ("Sales Manager", "SALES_MANAGER", "Manages sales team and their customers", True),
    ("Sales Representative", "SALES_REP", "Owns and manages assigned customers", True),
    ("Read Only", "READ_ONLY", "View-only access to permitted records", True),
]

SALES_MANAGER_PERMISSIONS = [
    "clients.customer.create", "clients.customer.read", "clients.customer.update",
    "clients.customer.status.change", "clients.customer.ownership.transfer",
    "clients.contact.create", "clients.contact.read", "clients.contact.update", "clients.contact.delete",
    "clients.relationship.create", "clients.relationship.read", "clients.relationship.delete",
    "clients.address.write",
    "activities.activity.read", "activities.activity.create", "activities.activity.update", "activities.activity.complete",
    "activities.note.read", "activities.note.create", "activities.note.update", "activities.note.delete",
    "communications.sms.read", "communications.sms.send", "communications.email.read", "communications.email.send",
    "communications.call.read", "communications.call.log",
    "documents.document.read", "documents.document.create", "documents.document.update", "documents.document.download",
    "accounting.summary.read", "accounting.transactions.read",
    "customer360.view",
    "quotes.quote.create", "quotes.quote.read", "quotes.quote.update", "quotes.quote.send",
    "quotes.quote.duplicate", "quotes.quote.calculate", "quotes.quote.preview", "quotes.quote.download_pdf",
    "sales_order.sales_order.create", "sales_order.sales_order.read", "sales_order.sales_order.update",
    "sales_order.sales_order.calculate", "sales_order.sales_order.workflow",
    "sales_order.payment.read", "sales_order.payment.record", "sales_order.receipt.read",
    "campaign.view", "campaign.create", "campaign.edit", "campaign.delete", "campaign.activate",
    "lead.view", "lead.create", "lead.edit", "lead.delete", "lead.assign",
    "referral.view", "referral.manage",
    "momentum.view", "momentum.manage",
]

SALES_REP_PERMISSIONS = [
    "clients.customer.create", "clients.customer.read", "clients.customer.update",
    "clients.contact.create", "clients.contact.read", "clients.contact.update",
    "clients.relationship.create", "clients.relationship.read",
    "clients.address.write",
    "activities.activity.read", "activities.activity.create", "activities.activity.complete",
    "activities.note.read", "activities.note.create",
    "communications.sms.read", "communications.sms.send", "communications.email.read", "communications.email.send",
    "communications.call.read", "communications.call.log",
    "documents.document.read", "documents.document.create", "documents.document.download",
    "customer360.view",
    "quotes.quote.create", "quotes.quote.read", "quotes.quote.update", "quotes.quote.calculate",
    "sales_order.sales_order.create", "sales_order.sales_order.read", "sales_order.sales_order.update",
    "campaign.view", "campaign.create", "campaign.edit",
    "lead.view", "lead.create", "lead.edit", "lead.assign",
    "referral.view", "referral.manage",
    "momentum.view",
]

READ_ONLY_PERMISSIONS = [
    "clients.customer.read", "clients.contact.read", "clients.relationship.read",
    "activities.activity.read", "activities.note.read",
    "communications.sms.read", "communications.email.read", "communications.call.read",
    "documents.document.read",
    "customer360.view",
    "quotes.quote.read",
    "sales_order.sales_order.read",
    "campaign.view",
    "lead.view",
    "referral.view",
    "momentum.view",
]

CONTACT_ROLES = [
    ("finance_manager", "Finance Manager"),
    ("accountant", "Accountant"),
    ("director", "Director"),
    ("owner", "Owner"),
    ("manager", "Manager"),
    ("procurement", "Procurement Officer"),
]

RELATIONSHIP_TYPES = [
    ("parent_company", "Parent Company", True),
    ("subsidiary", "Subsidiary", True),
    ("spouse", "Spouse", True),
    ("guarantor", "Guarantor", False),
    ("director", "Director", False),
    ("employee", "Employee", False),
    ("supplier_contact", "Supplier Contact", False),
    ("related_account", "Related Account", True),
]

ACTIVITY_TYPES = [
    ("call", "Call"),
    ("meeting", "Meeting"),
    ("task", "Task"),
    ("visit", "Visit"),
    ("follow_up", "Follow-up"),
    ("note", "Note"),
]

DOCUMENT_TYPES = [
    ("contract", "Contract"),
    ("invoice", "Invoice"),
    ("statement", "Statement"),
    ("application", "Application"),
    ("identification", "Identification"),
    ("certificate", "Certificate"),
    ("other", "Other"),
]


def _get_or_create(db, model, unique_field, value, extra=None):
    col = getattr(model, unique_field)
    existing = db.execute(sa.select(model).where(col == value)).scalar_one_or_none()
    if existing:
        return existing
    obj = model(**{unique_field: value, **(extra or {})})
    db.add(obj)
    db.flush()
    return obj


class Command(BaseCommand):
    help = "Seed initial data (access policies, permissions, roles, admin user). Idempotent."

    def handle(self, *args, **options):
        db = SessionLocal()
        try:
            count = 0

            for name, code, scope, desc in ACCESS_POLICIES:
                _get_or_create(db, AccessPolicy, "code", code, {
                    "name": name, "scope": scope, "description": desc, "is_active": True,
                })
                count += 1

            for name, code, resource, action in PERMISSIONS:
                _get_or_create(db, Permission, "code", code, {
                    "name": name, "resource": resource, "action": action,
                    "description": name, "is_active": True,
                })
                count += 1

            for name, code, desc, is_system in ROLES:
                _get_or_create(db, Role, "code", code, {
                    "name": name, "description": desc,
                    "is_system_role": is_system, "is_active": True,
                })
                count += 1

            perm_map = {}
            for p in db.execute(sa.select(Permission)).scalars().all():
                perm_map[p.code] = p.permission_id

            role_map = {}
            for r in db.execute(sa.select(Role)).scalars().all():
                role_map[r.code] = r.role_id

            policy_map = {}
            for ap in db.execute(sa.select(AccessPolicy)).scalars().all():
                policy_map[ap.code] = ap.access_policy_id

            existing_rp = set()
            for rp in db.execute(sa.select(RolePermission)).scalars().all():
                existing_rp.add((rp.role_id, rp.permission_id))

            existing_rap = set()
            for rap in db.execute(sa.select(RoleAccessPolicy)).scalars().all():
                existing_rap.add((rap.role_id, rap.access_policy_id))

            system_role_codes = ["SUPER_ADMIN", "SALES_MANAGER", "SALES_REP", "READ_ONLY"]
            for rc in system_role_codes:
                if rc in role_map:
                    db.execute(
                        sa.delete(RolePermission).where(RolePermission.role_id == role_map[rc])
                    )
                    db.execute(
                        sa.delete(RoleAccessPolicy).where(RoleAccessPolicy.role_id == role_map[rc])
                    )
            db.flush()

            if "SUPER_ADMIN" in role_map:
                rid = role_map["SUPER_ADMIN"]
                for pid in perm_map.values():
                    if (rid, pid) not in existing_rp:
                        db.add(RolePermission(role_id=rid, permission_id=pid))
                if "GLOBAL_ALL" in policy_map:
                    apid = policy_map["GLOBAL_ALL"]
                    if (rid, apid) not in existing_rap:
                        db.add(RoleAccessPolicy(role_id=rid, access_policy_id=apid))

            perm_config = {
                "SALES_MANAGER": (SALES_MANAGER_PERMISSIONS, "SCOPE_DEPARTMENT"),
                "SALES_REP": (SALES_REP_PERMISSIONS, "SCOPE_ASSIGNED"),
                "READ_ONLY": (READ_ONLY_PERMISSIONS, "SCOPE_OWN"),
            }
            for role_code, (codes, policy_code) in perm_config.items():
                if role_code not in role_map:
                    continue
                rid = role_map[role_code]
                for code in codes:
                    if code in perm_map and (rid, perm_map[code]) not in existing_rp:
                        db.add(RolePermission(role_id=rid, permission_id=perm_map[code]))
                if policy_code in policy_map and (rid, policy_map[policy_code]) not in existing_rap:
                    db.add(RoleAccessPolicy(role_id=rid, access_policy_id=policy_map[policy_code]))

            from clients.models import ContactRole, RelationshipType, Branch
            from activities.models import ActivityType
            from documents.models import DocumentType
            for code, name in CONTACT_ROLES:
                _get_or_create(db, ContactRole, "code", code, {"name": name, "is_active": True})
            for code, name, bidir in RELATIONSHIP_TYPES:
                _get_or_create(db, RelationshipType, "code", code, {
                    "name": name, "bidirectional": bidir, "is_active": True,
                })
            for code, name in ACTIVITY_TYPES:
                _get_or_create(db, ActivityType, "code", code, {"name": name, "is_active": True})
            for code, name in DOCUMENT_TYPES:
                _get_or_create(db, DocumentType, "code", code, {"name": name, "is_active": True})
            _get_or_create(db, Branch, "code", "HO", {"name": "Head Office", "is_active": True})

            admin_username = os.getenv("CRM_ADMIN_USERNAME", "admin")
            admin_email = os.getenv("CRM_ADMIN_EMAIL", "admin@crm.local")
            admin_password = os.getenv("CRM_ADMIN_PASSWORD", "admin123")

            existing_admin = db.execute(
                sa.select(User).where(User.username == admin_username)
            ).scalar_one_or_none()
            if existing_admin:
                existing_admin.email = admin_email
                cred = db.execute(
                    sa.select(AuthenticationCredential).where(
                        AuthenticationCredential.user_id == existing_admin.user_id
                    )
                ).scalar_one_or_none()
                if cred:
                    cred.password_hash = hash_password(admin_password)
                self.stdout.write(f"Updated admin user '{admin_username}' password.")
            else:
                user = User(
                    username=admin_username,
                    email=admin_email,
                    first_name="Admin",
                    last_name="User",
                    status="ACTIVE",
                )
                db.add(user)
                db.flush()
                db.add(AuthenticationCredential(
                    user_id=user.user_id,
                    password_hash=hash_password(admin_password),
                ))
                if "SUPER_ADMIN" in role_map:
                    db.add(UserRole(user_id=user.user_id, role_id=role_map["SUPER_ADMIN"]))
                if "GLOBAL_ALL" in policy_map:
                    db.add(UserAccessPolicy(user_id=user.user_id, access_policy_id=policy_map["GLOBAL_ALL"]))
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Created admin user '{admin_username}'"))

            SCOUT_ROLE_CODE = "APPLICATION_SCOUT"
            SCOUT_USERNAME = "scout"
            SCOUT_PASSWORD = os.getenv("CRM_SCOUT_PASSWORD", "Scout#$123")
            SCOUT_PERMISSIONS = [
                "clients.customer.read", "clients.customer.create", "clients.customer.update",
                "clients.contact.create", "clients.contact.update",
                "clients.relationship.create", "clients.relationship.read", "clients.address.write",
                "activities.activity.read", "activities.activity.create", "activities.activity.update",
                "activities.note.read", "activities.note.create", "activities.note.update",
                "communications.sms.read", "communications.email.read", "communications.call.read",
                "documents.document.read", "documents.document.create", "documents.document.download",
                "accounting.summary.read", "accounting.transactions.read",
                "customer360.view",
                "quotes.quote.read", "quotes.quote.create", "quotes.quote.update",
                "quotes.quote.calculate", "quotes.quote.preview", "quotes.quote.download_pdf",
                "sales_order.sales_order.read", "sales_order.sales_order.create", "sales_order.sales_order.update",
                "sales_order.sales_order.calculate", "sales_order.payment.read", "sales_order.receipt.read",
                "campaign.view", "campaign.create", "campaign.edit",
                "lead.view", "lead.create", "lead.edit", "lead.assign",
                "referral.view", "referral.manage",
                "momentum.view",
            ]

            scout_role = _get_or_create(db, Role, "code", SCOUT_ROLE_CODE, {
                "name": "Application Scout",
                "description": "Evaluation-only role with least-privilege business access.",
                "is_system_role": False, "is_active": True,
            })

            db.execute(
                sa.delete(RolePermission).where(RolePermission.role_id == scout_role.role_id)
            )
            db.execute(
                sa.delete(RoleAccessPolicy).where(RoleAccessPolicy.role_id == scout_role.role_id)
            )
            db.flush()

            for code in SCOUT_PERMISSIONS:
                if code in perm_map:
                    db.add(RolePermission(role_id=scout_role.role_id, permission_id=perm_map[code]))

            if "GLOBAL_ALL" in policy_map:
                db.add(RoleAccessPolicy(role_id=scout_role.role_id, access_policy_id=policy_map["GLOBAL_ALL"]))

            scout_user = db.execute(
                sa.select(User).where(User.username == SCOUT_USERNAME)
            ).scalar_one_or_none()
            if not scout_user:
                scout_user = User(
                    username=SCOUT_USERNAME,
                    email="scout@crm-v2.test",
                    first_name="CRM",
                    last_name="Scout",
                    status="ACTIVE",
                )
                db.add(scout_user)
                db.flush()
                db.add(AuthenticationCredential(
                    user_id=scout_user.user_id,
                    password_hash=hash_password(SCOUT_PASSWORD),
                ))
                db.add(UserRole(user_id=scout_user.user_id, role_id=scout_role.role_id))
                if "GLOBAL_ALL" in policy_map:
                    db.add(UserAccessPolicy(user_id=scout_user.user_id, access_policy_id=policy_map["GLOBAL_ALL"]))
                self.stdout.write(self.style.SUCCESS(f"Created scout user '{SCOUT_USERNAME}'"))
            else:
                cred = db.execute(
                    sa.select(AuthenticationCredential).where(
                        AuthenticationCredential.user_id == scout_user.user_id
                    )
                ).scalar_one_or_none()
                if cred:
                    cred.password_hash = hash_password(SCOUT_PASSWORD)

            db.commit()
            self.stdout.write(self.style.SUCCESS(f"Seed complete. {count} items processed."))
        finally:
            db.close()
