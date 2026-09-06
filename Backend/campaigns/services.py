import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa

from common import audit
from common.events import DomainEvent, EventBus
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from campaigns.enums import (
    ALLOWED_CAMPAIGN_TRANSITIONS,
    CampaignStatus,
    TERMINAL_CAMPAIGN_STATUSES,
)
from campaigns.models import (
    Campaign,
    CampaignCode,
    CampaignSchedule,
    CampaignShortUrl,
    CampaignSource,
    CampaignStateHistory,
)

logger = logging.getLogger(__name__)


class CampaignService:
    @staticmethod
    def create_campaign(db, payload: dict, user_id: int, *, request=None) -> Campaign:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValidationError_("Campaign name is required.")

        campaign = Campaign(
            name=name,
            description=payload.get("description"),
            status=payload.get("status", CampaignStatus.DRAFT.value),
            campaign_type=payload.get("campaign_type", "CUSTOM"),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            budget=payload.get("budget"),
            owner_user_id=payload.get("owner_user_id"),
            target_products=payload.get("target_products"),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(campaign)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_CREATED",
            resource_type="campaign",
            resource_id=campaign.campaign_id,
            description=f"Campaign '{name}' created",
            request=request,
        )
        db.commit()
        return campaign

    @staticmethod
    def update_campaign(db, campaign_id: int, payload: dict, user_id: int, *, request=None) -> Campaign:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        if campaign.status in TERMINAL_CAMPAIGN_STATUSES:
            raise ConflictError("Cannot edit a terminal campaign.")

        if "name" in payload and payload["name"]:
            campaign.name = payload["name"].strip()
        if "description" in payload:
            campaign.description = payload["description"]
        if "campaign_type" in payload:
            campaign.campaign_type = payload["campaign_type"]
        if "start_date" in payload:
            campaign.start_date = payload["start_date"]
        if "end_date" in payload:
            campaign.end_date = payload["end_date"]
        if "budget" in payload:
            campaign.budget = payload["budget"]
        if "owner_user_id" in payload:
            campaign.owner_user_id = payload["owner_user_id"]
        if "target_products" in payload:
            campaign.target_products = payload["target_products"]
        campaign.updated_by = user_id

        db.flush()
        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_UPDATED",
            resource_type="campaign",
            resource_id=campaign.campaign_id,
            description=f"Campaign '{campaign.name}' updated",
            request=request,
        )
        db.commit()
        return campaign

    @staticmethod
    def transition_campaign(db, campaign_id: int, new_status: str, user_id: int, *, reason: str = None, request=None) -> Campaign:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        if campaign.status in TERMINAL_CAMPAIGN_STATUSES:
            raise ConflictError("Cannot transition a terminal campaign.")

        allowed = ALLOWED_CAMPAIGN_TRANSITIONS.get(campaign.status, set())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot transition from '{campaign.status}' to '{new_status}'. "
                f"Allowed: {', '.join(sorted(allowed)) if allowed else 'none'}"
            )

        old_status = campaign.status
        campaign.status = new_status
        campaign.updated_by = user_id

        history = CampaignStateHistory(
            campaign_id=campaign.campaign_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=user_id,
            reason=reason,
        )
        db.add(history)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_STATUS_CHANGED",
            resource_type="campaign",
            resource_id=campaign.campaign_id,
            description=f"Campaign status changed from '{old_status}' to '{new_status}'",
            metadata={"old_status": old_status, "new_status": new_status, "reason": reason},
            request=request,
        )
        db.commit()
        return campaign

    @staticmethod
    def delete_campaign(db, campaign_id: int, user_id: int, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        if campaign.deleted_at is not None:
            raise NotFoundError("Campaign not found.")

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_DELETED",
            resource_type="campaign",
            resource_id=campaign.campaign_id,
            description=f"Campaign '{campaign.name}' deleted",
            request=request,
        )
        campaign.deleted_at = datetime.utcnow()
        campaign.deleted_by = user_id
        db.commit()


class CampaignCodeService:
    @staticmethod
    def generate_code(campaign_id: int) -> str:
        return f"CMP-{campaign_id}-{secrets.token_hex(4).upper()}"

    @staticmethod
    def create_code(db, campaign_id: int, payload: dict, user_id: int, *, request=None) -> CampaignCode:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        code = (payload.get("code") or "").strip()
        if not code:
            code = CampaignCodeService.generate_code(campaign_id)

        existing = db.execute(
            sa.select(CampaignCode).where(CampaignCode.code == code)
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Code '{code}' already exists.")

        cc = CampaignCode(
            campaign_id=campaign_id,
            code=code,
            type=payload.get("type", "CUSTOM"),
            max_uses=payload.get("max_uses"),
            expires_at=payload.get("expires_at"),
        )
        db.add(cc)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_CODE_CREATED",
            resource_type="campaign_code",
            resource_id=cc.id,
            description=f"Campaign code '{code}' created for campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return cc

    @staticmethod
    def increment_use_count(db, code: str):
        cc = db.execute(
            sa.select(CampaignCode).where(CampaignCode.code == code).with_for_update()
        ).scalar_one_or_none()
        if cc is None:
            return None
        cc.use_count += 1
        db.flush()
        return cc


class CampaignSourceService:
    @staticmethod
    def create_source(db, campaign_id: int, payload: dict, user_id: int, *, request=None) -> CampaignSource:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        cs = CampaignSource(
            campaign_id=campaign_id,
            source_type=payload.get("source_type", "CUSTOM"),
            source_identifier=payload.get("source_identifier"),
            tracking_url=payload.get("tracking_url"),
        )
        db.add(cs)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_SOURCE_CREATED",
            resource_type="campaign_source",
            resource_id=cs.id,
            description=f"Campaign source '{cs.source_type}' created for campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return cs

    @staticmethod
    def increment_click_count(db, source_id: int):
        cs = db.get(CampaignSource, source_id)
        if cs:
            cs.click_count += 1
            db.flush()


class CampaignScheduleService:
    @staticmethod
    def create_schedule(db, campaign_id: int, payload: dict, user_id: int, *, request=None) -> CampaignSchedule:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        sched = CampaignSchedule(
            campaign_id=campaign_id,
            action=payload["action"],
            scheduled_at=payload["scheduled_at"],
        )
        db.add(sched)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_SCHEDULE_CREATED",
            resource_type="campaign_schedule",
            resource_id=sched.id,
            description=f"Schedule '{sched.action}' created for campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return sched
