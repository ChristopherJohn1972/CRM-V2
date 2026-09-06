import logging
from datetime import datetime, timezone

import sqlalchemy as sa

from common import audit
from common.events import DomainEvent, EventBus
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from leads.enums import (
    ALLOWED_LEAD_TRANSITIONS,
    LeadStatus,
    TERMINAL_LEAD_STATUSES,
)
from leads.models import Lead, LeadConsent, LeadFollowUp, LeadQualification

logger = logging.getLogger(__name__)


class LeadService:
    @staticmethod
    def create_lead(db, payload: dict, user_id: int, *, request=None) -> Lead:
        email = (payload.get("email") or "").strip()
        phone = (payload.get("phone") or "").strip()
        if not email and not phone:
            raise ValidationError_("At least email or phone is required.")

        lead = Lead(
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            email=email or None,
            phone=phone or None,
            company=payload.get("company"),
            source_campaign_id=payload.get("source_campaign_id"),
            source_channel=payload.get("source_channel"),
            status=LeadStatus.NEW.value,
            assigned_user_id=payload.get("assigned_user_id"),
            assigned_team_id=payload.get("assigned_team_id"),
            tags=payload.get("tags"),
            notes=payload.get("notes"),
            consent_given=payload.get("consent_given", False),
            consent_date=datetime.now(timezone.utc) if payload.get("consent_given") else None,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(lead)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_CREATED",
            resource_type="lead",
            resource_id=lead.lead_id,
            description=f"Lead created for {email or phone}",
            request=request,
        )
        db.commit()
        return lead

    @staticmethod
    def update_lead(db, lead_id: int, payload: dict, user_id: int, *, request=None) -> Lead:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        if lead.status in TERMINAL_LEAD_STATUSES:
            raise ConflictError("Cannot edit a terminal lead.")

        if "first_name" in payload:
            lead.first_name = payload["first_name"]
        if "last_name" in payload:
            lead.last_name = payload["last_name"]
        if "email" in payload:
            lead.email = payload["email"] or None
        if "phone" in payload:
            lead.phone = payload["phone"] or None
        if "company" in payload:
            lead.company = payload["company"]
        if "source_campaign_id" in payload:
            lead.source_campaign_id = payload["source_campaign_id"]
        if "source_channel" in payload:
            lead.source_channel = payload["source_channel"]
        if "assigned_user_id" in payload:
            lead.assigned_user_id = payload["assigned_user_id"]
        if "assigned_team_id" in payload:
            lead.assigned_team_id = payload["assigned_team_id"]
        if "status" in payload and payload["status"]:
            old_status = lead.status
            new_status = payload["status"]
            allowed = ALLOWED_LEAD_TRANSITIONS.get(old_status, set())
            if new_status not in allowed:
                raise ConflictError(
                    f"Cannot transition from '{old_status}' to '{new_status}'. "
                    f"Allowed: {', '.join(sorted(allowed)) if allowed else 'none'}"
                )
            lead.status = new_status
        if "tags" in payload:
            lead.tags = payload["tags"]
        if "notes" in payload:
            lead.notes = payload["notes"]
        lead.updated_by = user_id

        db.flush()
        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_UPDATED",
            resource_type="lead",
            resource_id=lead.lead_id,
            description=f"Lead updated",
            request=request,
        )
        db.commit()
        return lead

    @staticmethod
    def transition_lead(db, lead_id: int, new_status: str, user_id: int, *, request=None) -> Lead:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        if lead.status in TERMINAL_LEAD_STATUSES:
            raise ConflictError("Cannot transition a terminal lead.")

        allowed = ALLOWED_LEAD_TRANSITIONS.get(lead.status, set())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot transition from '{lead.status}' to '{new_status}'. "
                f"Allowed: {', '.join(sorted(allowed)) if allowed else 'none'}"
            )

        old_status = lead.status
        lead.status = new_status
        lead.updated_by = user_id

        db.flush()
        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_STATUS_CHANGED",
            resource_type="lead",
            resource_id=lead.lead_id,
            description=f"Lead status changed from '{old_status}' to '{new_status}'",
            metadata={"old_status": old_status, "new_status": new_status},
            request=request,
        )
        db.commit()
        return lead

    @staticmethod
    def delete_lead(db, lead_id: int, user_id: int, *, request=None):
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_DELETED",
            resource_type="lead",
            resource_id=lead.lead_id,
            description=f"Lead deleted",
            request=request,
        )
        db.delete(lead)
        db.commit()


class LeadQualificationService:
    @staticmethod
    def qualify_lead(db, lead_id: int, payload: dict, user_id: int, *, request=None) -> LeadQualification:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")

        qual = LeadQualification(
            lead_id=lead_id,
            score=payload["score"],
            criteria=payload.get("criteria"),
            qualified_by=user_id,
            notes=payload.get("notes"),
        )
        db.add(qual)

        lead.qualification_score = payload["score"]
        lead.updated_by = user_id

        db.flush()
        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_QUALIFIED",
            resource_type="lead",
            resource_id=lead.lead_id,
            description=f"Lead qualified with score {payload['score']}",
            request=request,
        )
        db.commit()
        return qual


class LeadFollowUpService:
    @staticmethod
    def create_follow_up(db, lead_id: int, payload: dict, user_id: int, *, request=None) -> LeadFollowUp:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")

        fu = LeadFollowUp(
            lead_id=lead_id,
            follow_up_type=payload["follow_up_type"],
            scheduled_at=payload["scheduled_at"],
            notes=payload.get("notes"),
            assigned_to=payload.get("assigned_to"),
        )
        db.add(fu)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_FOLLOW_UP_CREATED",
            resource_type="lead_follow_up",
            resource_id=fu.id,
            description=f"Follow-up scheduled for lead {lead_id}",
            request=request,
        )
        db.commit()
        return fu

    @staticmethod
    def complete_follow_up(db, lead_id: int, follow_up_id: int, payload: dict, user_id: int, *, request=None) -> LeadFollowUp:
        fu = db.get(LeadFollowUp, follow_up_id)
        if fu is None or fu.lead_id != lead_id:
            raise NotFoundError("Follow-up not found.")

        fu.completed_at = datetime.now(timezone.utc)
        fu.outcome = payload.get("outcome")
        if "notes" in payload:
            fu.notes = payload["notes"]

        db.flush()
        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_FOLLOW_UP_COMPLETED",
            resource_type="lead_follow_up",
            resource_id=fu.id,
            description=f"Follow-up completed for lead {lead_id}",
            request=request,
        )
        db.commit()
        return fu


class LeadConsentService:
    @staticmethod
    def record_consent(db, lead_id: int, payload: dict, user_id: int, *, request=None) -> LeadConsent:
        lead = db.get(Lead, lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")

        consent = LeadConsent(
            lead_id=lead_id,
            consent_type=payload["consent_type"],
            granted=payload["granted"],
            granted_at=datetime.now(timezone.utc) if payload["granted"] else None,
            revoked_at=None if payload["granted"] else datetime.now(timezone.utc),
            ip_address=payload.get("ip_address"),
            source=payload.get("source"),
        )
        db.add(consent)

        if payload["granted"]:
            lead.consent_given = True
            lead.consent_date = datetime.now(timezone.utc)

        db.flush()
        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="LEAD_CONSENT_RECORDED",
            resource_type="lead",
            resource_id=lead.lead_id,
            description=f"Consent {'granted' if payload['granted'] else 'revoked'} for lead {lead_id}",
            request=request,
        )
        db.commit()
        return consent
