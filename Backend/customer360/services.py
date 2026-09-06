import logging

import sqlalchemy as sa

from activities.models import ActivityNote
from clients.models import Customer, CustomerAddress, CustomerContact
from communications.models import CallLog, EmailMessage, SmsMessage

logger = logging.getLogger(__name__)


class Customer360Service:
    @staticmethod
    def build_summary(db, customer: Customer):
        customer_id = customer.customer_id

        contacts = db.execute(
            sa.select(CustomerContact)
            .where(CustomerContact.customer_id == customer_id, CustomerContact.is_active == sa.true())
            .order_by(CustomerContact.is_primary.desc(), CustomerContact.contact_id)
            .limit(10)
        ).scalars().all()
        contacts_total = db.execute(
            sa.select(sa.func.count()).select_from(CustomerContact).where(
                CustomerContact.customer_id == customer_id,
                CustomerContact.is_active == sa.true(),
            )
        ).scalar()

        addresses = db.execute(
            sa.select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .order_by(CustomerAddress.is_primary.desc())
        ).scalars().all()

        sms_total = db.execute(
            sa.select(sa.func.count()).select_from(SmsMessage).where(SmsMessage.customer_id == customer_id)
        ).scalar()
        email_total = db.execute(
            sa.select(sa.func.count()).select_from(EmailMessage).where(EmailMessage.customer_id == customer_id)
        ).scalar()
        call_total = db.execute(
            sa.select(sa.func.count()).select_from(CallLog).where(CallLog.customer_id == customer_id)
        ).scalar()

        notes = db.execute(
            sa.select(ActivityNote)
            .where(ActivityNote.customer_id == customer_id)
            .order_by(sa.desc(ActivityNote.created_at))
            .limit(5)
        ).scalars().all()

        portal_access = Customer360Service._build_portal_access(db, customer)

        notifications_summary = {
            "sms_total": sms_total,
            "email_total": email_total,
            "call_total": call_total,
        }

        return {
            "customer_id": customer.customer_id,
            "account_number": customer.customer_number,
            "display_name": customer.get_display_name(),
            "customer_type": customer.customer_type,
            "status": customer.status,
            "summary": {
                "contacts": contacts_total,
                "communications": notifications_summary,
            },
            "addresses": [
                {
                    "address_id": a.address_id,
                    "address_type": a.address_type,
                    "address": a.address,
                    "city": a.city,
                    "country": a.country,
                    "is_primary": bool(a.is_primary),
                }
                for a in addresses
            ],
            "contacts": [
                {
                    "contact_id": c.contact_id,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "email": c.email,
                    "phone": c.phone,
                    "mobile": c.mobile,
                    "role_id": c.role_id,
                    "is_primary": bool(c.is_primary),
                }
                for c in contacts
            ],
            "portal_access": portal_access,
            "notifications_summary": notifications_summary,
            "recent_notes": [
                {
                    "note_id": n.note_id,
                    "body": n.body,
                    "visibility": n.visibility,
                    "author_user_id": n.author_user_id,
                    "created_at": n.created_at,
                }
                for n in notes
            ],
            "urls": {
                "360": f"/api/clients/{customer_id}/360",
                "contacts": f"/api/clients/{customer_id}/contacts",
                "portal_access": f"/api/clients/{customer_id}/portal-access",
                "notifications": f"/api/clients/{customer_id}/notifications",
                "accounting_summary": f"/api/clients/{customer_id}/accounting-summary",
            },
        }

    @staticmethod
    def _build_portal_access(db, customer):
        from portal.models import CustomerAccount, PortalUser, PortalUserCustomer

        customer_account = db.execute(
            sa.select(CustomerAccount).where(
                CustomerAccount.customer_id == customer.customer_id,
            )
        ).scalar_one_or_none()

        if customer_account is None:
            return {
                "provisioned": False,
                "portal_users": [],
            }

        links = db.execute(
            sa.select(PortalUserCustomer).where(
                PortalUserCustomer.customer_account_id == customer_account.customer_account_id,
                PortalUserCustomer.is_active == sa.true(),
            )
        ).scalars().all()

        portal_users = []
        for link in links:
            user = db.get(PortalUser, link.portal_user_id)
            if user is None:
                continue
            portal_users.append({
                "portal_user_id": user.portal_user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "status": user.status,
                "role": link.role,
                "is_primary": bool(link.is_primary),
                "last_login_at": user.last_login_at,
            })

        return {
            "provisioned": True,
            "customer_account_id": customer_account.customer_account_id,
            "account_number": customer_account.account_number,
            "account_status": customer_account.status,
            "portal_users": portal_users,
        }
