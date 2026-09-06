"""Campaign launch service with idempotent launch and readiness validation."""

import logging
import uuid
from datetime import datetime

import sqlalchemy as sa

from common import audit
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from campaigns.enums import (
    CampaignStatus,
    CreativeStatus,
)
from campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignBudget,
    CampaignChannel,
    CampaignLaunch,
    CampaignOffer,
    Creative,
)

logger = logging.getLogger(__name__)


class CampaignReadinessService:
    """Validates campaign readiness for launch."""

    @staticmethod
    def check_readiness(db, campaign_id):
        """Perform a full readiness check.

        Returns: {ready: bool, checks: [{key, status, message}]}
        """
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        product_count = len(campaign.target_products or [])
        has_audience = db.execute(
            sa.select(CampaignAudience).where(
                CampaignAudience.campaign_id == campaign_id
            )
        ).scalar_one_or_none() is not None
        has_offer = db.execute(
            sa.select(CampaignOffer).where(
                CampaignOffer.campaign_id == campaign_id
            )
        ).scalar_one_or_none() is not None
        channel_count = db.scalar(
            sa.select(sa.func.count()).where(
                CampaignChannel.campaign_id == campaign_id
            )
        )
        has_creative = db.execute(
            sa.select(Creative).where(
                Creative.campaign_id == campaign_id,
                Creative.is_selected == sa.true(),
                Creative.status.in_([
                    CreativeStatus.READY.value,
                    CreativeStatus.APPROVED.value,
                ]),
            )
        ).scalar_one_or_none() is not None
        budget = db.execute(
            sa.select(CampaignBudget).where(
                CampaignBudget.campaign_id == campaign_id
            )
        ).scalar_one_or_none()
        has_budget = budget is not None and budget.amount > 0

        checks = [
            {
                "key": "product",
                "status": "passed" if product_count > 0 else "failed",
                "message": None if product_count > 0 else "At least one product must be selected.",
            },
            {
                "key": "audience",
                "status": "passed" if has_audience else "failed",
                "message": None if has_audience else "Audience must be defined.",
            },
            {
                "key": "offer",
                "status": "passed" if has_offer else "warning",
                "message": None if has_offer else "No offer configured. This is optional but recommended.",
            },
            {
                "key": "channels",
                "status": "passed" if channel_count > 0 else "failed",
                "message": None if channel_count > 0 else "At least one channel must be selected.",
            },
            {
                "key": "creative",
                "status": "passed" if has_creative else "failed",
                "message": None if has_creative else "A ready or approved creative must be selected.",
            },
            {
                "key": "budget",
                "status": "passed" if has_budget else "failed",
                "message": None if has_budget else "Budget must be greater than 0.",
            },
        ]

        return {
            "ready": all(c["status"] == "passed" for c in checks),
            "checks": checks,
        }


class CampaignLaunchService:
    """Handle campaign launch with idempotency."""

    @staticmethod
    def launch(db, campaign_id, user_id, *, idempotency_key=None, request=None):
        """Launch a campaign. Idempotent - duplicate requests return existing result."""
        if not idempotency_key:
            idempotency_key = f"launch-{campaign_id}-{uuid.uuid4().hex[:12]}"

        existing = db.execute(
            sa.select(CampaignLaunch).where(
                CampaignLaunch.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()
        if existing:
            logger.info("Launch idempotent hit for key %s", idempotency_key)
            return existing

        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        if campaign.status not in (
            CampaignStatus.APPROVED.value,
            CampaignStatus.READY_FOR_REVIEW.value,
        ):
            raise ConflictError(
                f"Campaign cannot be launched from status '{campaign.status}'. "
                "Campaign must be APPROVED or READY_FOR_REVIEW."
            )

        readiness = CampaignReadinessService.check_readiness(db, campaign_id)
        if not readiness["ready"]:
            failed_checks = [c for c in readiness["checks"] if c["status"] == "failed"]
            raise ValidationError_(
                f"Campaign is not ready to launch. Failed: "
                + ", ".join(c["key"] for c in failed_checks)
            )

        launch = CampaignLaunch(
            campaign_id=campaign_id,
            idempotency_key=idempotency_key,
            status="VALIDATING",
            validation_result=readiness,
            launched_by=user_id,
        )
        db.add(launch)
        db.flush()

        try:
            launch.status = "LAUNCHING"
            db.flush()

            campaign.status = CampaignStatus.ACTIVE.value
            campaign.published_at = datetime.utcnow()

            launch.status = "COMPLETED"
            launch.launched_at = datetime.utcnow()

            audit.record_audit(
                db,
                actor_user_id=user_id,
                action="CAMPAIGN_LAUNCHED",
                resource_type="campaign",
                resource_id=campaign_id,
                description=f"Campaign '{campaign.name}' launched",
                metadata={"idempotency_key": idempotency_key},
                request=request,
            )
            db.commit()

            logger.info("Campaign %d launched successfully", campaign_id)
            return launch

        except Exception as exc:
            launch.status = "FAILED"
            launch.error_message = str(exc)
            db.flush()
            db.commit()
            logger.error("Launch failed for campaign %d: %s", campaign_id, exc)
            raise
