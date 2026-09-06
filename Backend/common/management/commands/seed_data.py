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
    ("IAM: manage users", "iam.user.manage", "iam", "user:manage"),
    ("IAM: manage roles", "iam.role.manage", "iam", "role:manage"),
    ("IAM: audit permissions", "iam.permission.audit", "iam", "permission:audit"),
    ("Quotes: create", "quotes.quote.create", "quotes", "quote:create"),
    ("Quotes: read", "quotes.quote.read", "quotes", "quote:read"),
    ("Quotes: update", "quotes.quote.update", "quotes", "quote:update"),
    ("Quotes: delete", "quotes.quote.delete", "quotes", "quote:delete"),
    ("Quotes: send", "quotes.quote.send", "quotes", "quote:send"),
    ("Sales Orders: create", "sales_order.sales_order.create", "sales_orders", "sales_order:create"),
    ("Sales Orders: read", "sales_order.sales_order.read", "sales_orders", "sales_order:read"),
    ("Sales Orders: update", "sales_order.sales_order.update", "sales_orders", "sales_order:update"),
    ("Sales Orders: delete", "sales_order.sales_order.delete", "sales_orders", "sales_order:delete"),
    ("Sales Orders: calculate", "sales_order.sales_order.calculate", "sales_orders", "sales_order:calculate"),
    ("Sales Orders: workflow", "sales_order.sales_order.workflow", "sales_orders", "sales_order:workflow"),
    ("Campaigns: read", "campaigns.campaign.read", "campaigns", "campaign:read"),
    ("Campaigns: create", "campaigns.campaign.create", "campaigns", "campaign:create"),
    ("Campaigns: update", "campaigns.campaign.update", "campaigns", "campaign:update"),
    ("Campaigns: delete", "campaigns.campaign.delete", "campaigns", "campaign:delete"),
    ("Leads: read", "leads.lead.read", "leads", "lead:read"),
    ("Leads: create", "leads.lead.create", "leads", "lead:create"),
    ("Leads: update", "leads.lead.update", "leads", "lead:update"),
    ("Leads: delete", "leads.lead.delete", "leads", "lead:delete"),
    ("Referrals: read", "referrals.referral.read", "referrals", "referral:read"),
    ("Referrals: create", "referrals.referral.create", "referrals", "referral:create"),
    ("Momentum: read", "momentum.momentum.read", "momentum", "momentum:read"),
    ("Momentum: manage", "momentum.momentum.manage", "momentum", "momentum:manage"),
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
    "sales_order.sales_order.create", "sales_order.sales_order.read", "sales_order.sales_order.update",
    "sales_order.sales_order.calculate", "sales_order.sales_order.workflow",
    "campaigns.campaign.read", "campaigns.campaign.create", "campaigns.campaign.update", "campaigns.campaign.delete",
    "leads.lead.read", "leads.lead.create", "leads.lead.update", "leads.lead.delete",
    "referrals.referral.read", "referrals.referral.create",
    "momentum.momentum.read", "momentum.momentum.manage",
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
    "quotes.quote.create", "quotes.quote.read", "quotes.quote.update",
    "sales_order.sales_order.create", "sales_order.sales_order.read", "sales_order.sales_order.update",
    "campaigns.campaign.read", "campaigns.campaign.create", "campaigns.campaign.update",
    "leads.lead.read", "leads.lead.create", "leads.lead.update",
    "referrals.referral.read", "referrals.referral.create",
    "momentum.momentum.read",
]

READ_ONLY_PERMISSIONS = [
    "clients.customer.read", "clients.contact.read", "clients.relationship.read",
    "activities.activity.read", "activities.note.read",
    "communications.sms.read", "communications.email.read", "communications.call.read",
    "documents.document.read",
    "customer360.view",
    "quotes.quote.read",
    "sales_order.sales_order.read",
    "campaigns.campaign.read",
    "leads.lead.read",
    "referrals.referral.read",
    "momentum.momentum.read",
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
            if not existing_admin:
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
            else:
                self.stdout.write(f"Admin user '{admin_username}' already exists, skipping.")

            db.commit()
            self.stdout.write(self.style.SUCCESS(f"Seed complete. {count} items processed."))
        finally:
            db.close()
