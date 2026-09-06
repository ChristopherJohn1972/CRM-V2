import logging
from datetime import datetime, timezone

import sqlalchemy as sa

from clients.enums import ALLOWED_STATUS_TRANSITIONS, CustomerStatus
from clients.models import AccountNumberSequence, Customer
from common import audit
from common.events import DomainEvent, EventBus
from common.exceptions import ConflictError, ValidationError_
from portal.services import provision_portal_access

logger = logging.getLogger(__name__)

ACCOUNT_NUMBER_BUCKET = "CUSTOMER"


def generate_account_number(db, bucket=ACCOUNT_NUMBER_BUCKET):
    row = db.execute(
        sa.select(AccountNumberSequence)
        .where(AccountNumberSequence.bucket == bucket)
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        row = AccountNumberSequence(bucket=bucket, last_value=0, min_length=4)
        db.add(row)
        db.flush()
    # Reconcile the sequence against every active customer number already in use
    # so soft-deleted numbers can be recycled and a new account never regresses
    # below the highest existing active number.
    max_existing = db.execute(
        sa.select(sa.func.max(sa.cast(Customer.customer_number, sa.Integer)))
        .where(Customer.deleted_at.is_(None))
    ).scalar()
    if max_existing and max_existing > row.last_value:
        row.last_value = max_existing
    row.last_value += 1
    return str(row.last_value).zfill(row.min_length)


class CustomerService:
    @staticmethod
    def create_customer(db, payload, actor_user_id, request=None):
        account_number = generate_account_number(db)

        if payload.get("customer_type") == "INDIVIDUAL":
            if not payload.get("first_name") and not payload.get("legal_name"):
                raise ValidationError_(
                    "Individual customers require a first name or legal name."
                )
            if not payload.get("legal_name"):
                payload["legal_name"] = " ".join(
                    [
                        part
                        for part in (
                            payload.get("first_name"),
                            payload.get("middle_name"),
                            payload.get("last_name"),
                        )
                        if part
                    ]
                )
        else:
            if not payload.get("legal_name"):
                raise ValidationError_("Business customers require a legal name.")

        customer = Customer(customer_number=account_number, **payload)
        customer.created_by = actor_user_id
        customer.updated_by = actor_user_id
        customer.version = 1
        db.add(customer)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="customer.created",
            resource_type="customers",
            resource_id=customer.customer_id,
            description=f"Customer {account_number} created",
            metadata={
                "account_number": account_number,
                "customer_type": customer.customer_type,
            },
            request=request,
        )

        for field in Customer.SENSITIVE_FIELDS:
            value = payload.get(field)
            if value:
                audit.record_audit(
                    db,
                    actor_user_id=actor_user_id,
                    action="sensitive_field.set",
                    resource_type="customers",
                    resource_id=customer.customer_id,
                    description=f"Sensitive field {field} recorded",
                    metadata={"field": field},
                    request=request,
                )

        db.commit()
        db.refresh(customer)

        try:
            _portal_user, temp_password = provision_portal_access(
                db, customer, initial_password=customer.legal_name
            )
            db.commit()
            customer._temp_portal_password = temp_password
        except Exception:
            logger.warning("Portal provisioning failed for customer %s", account_number, exc_info=True)
            customer._temp_portal_password = None
            db.rollback()
            db.refresh(customer)

        EventBus.publish(
            DomainEvent(
                event_type="CustomerCreated",
                customer_id=customer.customer_id,
                source_module="clients",
                actor_user_id=actor_user_id,
                actor_type="INTERNAL_USER",
                summary=f"Customer {customer.get_display_name()} created (account {account_number})",
                reference_type="customers",
                reference_id=customer.customer_id,
                payload={"account_number": account_number},
            )
        )
        return customer

    @staticmethod
    def update_customer(db, customer, payload, actor_user_id, request=None):
        sensitive_changed = []
        for field in Customer.SENSITIVE_FIELDS:
            if field in payload:
                sensitive_changed.append(field)

        version = payload.pop("version", None)
        if version is not None and int(version) != customer.version:
            raise ConflictError(
                f"Version mismatch. Current version is {customer.version}.",
                error_code="optimistic_lock",
            )

        old_status = customer.status
        for key, value in payload.items():
            setattr(customer, key, value)
        customer.updated_by = actor_user_id
        customer.version += 1
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="customer.updated",
            resource_type="customers",
            resource_id=customer.customer_id,
            description=f"Customer {customer.customer_number} updated",
            metadata={"changed_fields": sorted(payload.keys())},
            request=request,
        )
        for field in sensitive_changed:
            audit.record_audit(
                db,
                actor_user_id=actor_user_id,
                action="sensitive_field.changed",
                resource_type="customers",
                resource_id=customer.customer_id,
                description=f"Sensitive field {field} updated",
                metadata={"field": field, "old_status": old_status},
                request=request,
            )

        db.commit()
        db.refresh(customer)
        EventBus.publish(
            DomainEvent(
                event_type="CustomerUpdated",
                customer_id=customer.customer_id,
                source_module="clients",
                actor_user_id=actor_user_id,
                actor_type="INTERNAL_USER",
                summary=f"Customer {customer.customer_number} profile updated",
                reference_type="customers",
                reference_id=customer.customer_id,
            )
        )
        return customer

    @staticmethod
    def change_status(db, customer, new_status, reason, actor_user_id, request=None):
        old_status = customer.status
        if new_status == old_status:
            return customer

        allowed = ALLOWED_STATUS_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise ValidationError_(
                f"Status transition from {old_status} to {new_status} is not allowed.",
                field_errors={"status": "Invalid transition."},
            )

        customer.status = new_status
        customer.status_reason = reason
        customer.updated_by = actor_user_id
        customer.version += 1
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="customer.status_changed",
            resource_type="customers",
            resource_id=customer.customer_id,
            description=f"Status changed {old_status} -> {new_status}",
            metadata={"from": old_status, "to": new_status, "reason": reason},
            request=request,
        )
        db.commit()
        db.refresh(customer)
        EventBus.publish(
            DomainEvent(
                event_type="CustomerStatusChanged",
                customer_id=customer.customer_id,
                source_module="clients",
                actor_user_id=actor_user_id,
                actor_type="INTERNAL_USER",
                summary=f"Customer status changed to {new_status}",
                reference_type="customers",
                reference_id=customer.customer_id,
                payload={"from": old_status, "to": new_status},
            )
        )
        return customer

    @staticmethod
    def transfer_ownership(db, customer, assigned_user_id, assigned_team_id, actor_user_id, request=None):
        customer.assigned_user_id = assigned_user_id
        customer.assigned_team_id = assigned_team_id
        customer.updated_by = actor_user_id
        customer.version += 1
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=actor_user_id,
            action="customer.ownership_changed",
            resource_type="customers",
            resource_id=customer.customer_id,
            description=f"Ownership reassigned to user {assigned_user_id} / team {assigned_team_id}",
            metadata={"assigned_user_id": assigned_user_id, "assigned_team_id": assigned_team_id},
            request=request,
        )
        db.commit()
        db.refresh(customer)
        EventBus.publish(
            DomainEvent(
                event_type="CustomerOwnershipChanged",
                customer_id=customer.customer_id,
                source_module="clients",
                actor_user_id=actor_user_id,
                actor_type="INTERNAL_USER",
                summary="Customer ownership reassigned",
                reference_type="customers",
                reference_id=customer.customer_id,
            )
        )
        return customer


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)
