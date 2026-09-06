import logging

import sqlalchemy as sa

from common import audit
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from campaigns.enums import (
    CampaignStatus,
    RecommendationAction,
    TERMINAL_CAMPAIGN_STATUSES,
)
from campaigns.models import (
    Campaign,
    CampaignAudience,
    CampaignBudget,
    CampaignChannel,
    CampaignOffer,
    CampaignProduct,
    CampaignAnalyticsEvent,
)
from iam.permissions import UserPrincipal

logger = logging.getLogger(__name__)


def _validate_campaign_editable(campaign):
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    if campaign.status in TERMINAL_CAMPAIGN_STATUSES:
        raise ConflictError("Cannot edit a terminal campaign.")


class CampaignProductService:
    @staticmethod
    def add_products(db, campaign_id, product_ids, user_id, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        _validate_campaign_editable(campaign)

        if not product_ids:
            raise ValidationError_("At least one product ID is required.")

        existing = {
            row[0]
            for row in db.execute(
                sa.select(CampaignProduct.product_reference).where(
                    CampaignProduct.campaign_id == campaign_id
                )
            ).all()
        }

        added = 0
        for pid in product_ids:
            ref = pid if isinstance(pid, dict) else {"product_id": pid}
            ref_key = ref.get("product_id") if isinstance(ref, dict) else ref
            if ref_key in existing:
                continue
            cp = CampaignProduct(
                campaign_id=campaign_id,
                product_reference=ref,
            )
            db.add(cp)
            existing.add(ref_key)
            added += 1

        if added == 0:
            raise ConflictError("All provided products are already in this campaign.")

        if campaign.status == CampaignStatus.DRAFT.value:
            campaign.status = CampaignStatus.PRODUCT_SELECTED.value

        campaign.updated_by = user_id
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_PRODUCTS_ADDED",
            resource_type="campaign_product",
            resource_id=campaign_id,
            description=f"{added} product(s) added to campaign {campaign_id}",
            metadata={"product_ids": product_ids},
            request=request,
        )
        db.commit()

    @staticmethod
    def list_products(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        return db.execute(
            sa.select(CampaignProduct).where(CampaignProduct.campaign_id == campaign_id)
        ).scalars().all()

    @staticmethod
    def remove_product(db, campaign_id, product_id, user_id, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        _validate_campaign_editable(campaign)

        cp = db.execute(
            sa.select(CampaignProduct).where(
                CampaignProduct.campaign_id == campaign_id,
                CampaignProduct.id == product_id,
            )
        ).scalar_one_or_none()
        if cp is None:
            raise NotFoundError("Product not found in this campaign.")

        db.delete(cp)
        campaign.updated_by = user_id
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_PRODUCT_REMOVED",
            resource_type="campaign_product",
            resource_id=product_id,
            description=f"Product {product_id} removed from campaign {campaign_id}",
            request=request,
        )
        db.commit()


class CampaignAudienceService:
    @staticmethod
    def upsert_audience(db, campaign_id, payload, user_id, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        _validate_campaign_editable(campaign)

        audience_type = payload.get("audience_type")
        if not audience_type:
            raise ValidationError_("audience_type is required.")

        existing = db.execute(
            sa.select(CampaignAudience).where(
                CampaignAudience.campaign_id == campaign_id
            )
        ).scalar_one_or_none()

        if existing:
            existing.audience_type = audience_type
            existing.configuration = payload.get("configuration")
            existing.description = payload.get("description")
            existing.updated_at = sa.func.now()
            action_label = "CAMPAIGN_AUDIENCE_UPDATED"
            description = f"Audience updated for campaign {campaign_id}"
            resource_id = existing.id
        else:
            existing = CampaignAudience(
                campaign_id=campaign_id,
                audience_type=audience_type,
                configuration=payload.get("configuration"),
                description=payload.get("description"),
            )
            db.add(existing)
            action_label = "CAMPAIGN_AUDIENCE_CREATED"
            description = f"Audience created for campaign {campaign_id}"
            resource_id = None

        campaign.updated_by = user_id
        db.flush()

        if resource_id is None:
            resource_id = existing.id

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action=action_label,
            resource_type="campaign_audience",
            resource_id=resource_id,
            description=description,
            request=request,
        )
        db.commit()
        return existing

    @staticmethod
    def get_audience(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        return db.execute(
            sa.select(CampaignAudience).where(
                CampaignAudience.campaign_id == campaign_id
            )
        ).scalar_one_or_none()

    @staticmethod
    def set_user_action(db, audience_id, action, user_id, *, request=None):
        if action not in {a.value for a in RecommendationAction}:
            raise ValidationError_(f"Invalid action: {action}")

        audience = db.get(CampaignAudience, audience_id)
        if audience is None:
            raise NotFoundError("Audience not found.")

        audience.user_action = action
        audience.updated_at = sa.func.now()
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_AUDIENCE_ACTION",
            resource_type="campaign_audience",
            resource_id=audience_id,
            description=f"User action '{action}' recorded on audience {audience_id}",
            request=request,
        )
        db.commit()
        return audience


class CampaignOfferService:
    @staticmethod
    def upsert_offer(db, campaign_id, payload, user_id, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        _validate_campaign_editable(campaign)

        offer_type = payload.get("offer_type")
        if not offer_type:
            raise ValidationError_("offer_type is required.")

        existing = db.execute(
            sa.select(CampaignOffer).where(CampaignOffer.campaign_id == campaign_id)
        ).scalar_one_or_none()

        if existing:
            existing.offer_type = offer_type
            existing.value = payload.get("value")
            existing.description = payload.get("description")
            existing.start_at = payload.get("start_at")
            existing.end_at = payload.get("end_at")
            existing.updated_at = sa.func.now()
            action_label = "CAMPAIGN_OFFER_UPDATED"
            description = f"Offer updated for campaign {campaign_id}"
            resource_id = existing.id
        else:
            existing = CampaignOffer(
                campaign_id=campaign_id,
                offer_type=offer_type,
                value=payload.get("value"),
                description=payload.get("description"),
                start_at=payload.get("start_at"),
                end_at=payload.get("end_at"),
            )
            db.add(existing)
            action_label = "CAMPAIGN_OFFER_CREATED"
            description = f"Offer created for campaign {campaign_id}"
            resource_id = None

        campaign.updated_by = user_id
        db.flush()

        if resource_id is None:
            resource_id = existing.id

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action=action_label,
            resource_type="campaign_offer",
            resource_id=resource_id,
            description=description,
            request=request,
        )
        db.commit()
        return existing

    @staticmethod
    def get_offer(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        return db.execute(
            sa.select(CampaignOffer).where(CampaignOffer.campaign_id == campaign_id)
        ).scalar_one_or_none()

    @staticmethod
    def set_user_action(db, offer_id, action, user_id, *, request=None):
        if action not in {a.value for a in RecommendationAction}:
            raise ValidationError_(f"Invalid action: {action}")

        offer = db.get(CampaignOffer, offer_id)
        if offer is None:
            raise NotFoundError("Offer not found.")

        offer.user_action = action
        offer.updated_at = sa.func.now()
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_OFFER_ACTION",
            resource_type="campaign_offer",
            resource_id=offer_id,
            description=f"User action '{action}' recorded on offer {offer_id}",
            request=request,
        )
        db.commit()
        return offer


class CampaignChannelService:
    @staticmethod
    def add_channel(db, campaign_id, channel, configuration, user_id, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        _validate_campaign_editable(campaign)

        if not channel:
            raise ValidationError_("channel is required.")

        existing = db.execute(
            sa.select(CampaignChannel).where(
                CampaignChannel.campaign_id == campaign_id,
                CampaignChannel.channel == channel,
            )
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Channel '{channel}' already exists on this campaign.")

        cc = CampaignChannel(
            campaign_id=campaign_id,
            channel=channel,
            configuration=configuration,
        )
        db.add(cc)
        campaign.updated_by = user_id
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_CHANNEL_ADDED",
            resource_type="campaign_channel",
            resource_id=cc.id,
            description=f"Channel '{channel}' added to campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return cc

    @staticmethod
    def list_channels(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        return db.execute(
            sa.select(CampaignChannel).where(CampaignChannel.campaign_id == campaign_id)
        ).scalars().all()

    @staticmethod
    def remove_channel(db, campaign_id, channel_id, user_id, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        _validate_campaign_editable(campaign)

        cc = db.execute(
            sa.select(CampaignChannel).where(
                CampaignChannel.campaign_id == campaign_id,
                CampaignChannel.id == channel_id,
            )
        ).scalar_one_or_none()
        if cc is None:
            raise NotFoundError("Channel not found in this campaign.")

        db.delete(cc)
        campaign.updated_by = user_id
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CAMPAIGN_CHANNEL_REMOVED",
            resource_type="campaign_channel",
            resource_id=channel_id,
            description=f"Channel {channel_id} removed from campaign {campaign_id}",
            request=request,
        )
        db.commit()


class CampaignBudgetService:
    @staticmethod
    def upsert_budget(db, campaign_id, payload, user_id, *, request=None):
        campaign = db.get(Campaign, campaign_id)
        _validate_campaign_editable(campaign)

        amount = payload.get("amount")
        if amount is None:
            raise ValidationError_("amount is required.")

        existing = db.execute(
            sa.select(CampaignBudget).where(CampaignBudget.campaign_id == campaign_id)
        ).scalar_one_or_none()

        if existing:
            existing.amount = amount
            existing.currency = payload.get("currency", existing.currency)
            existing.period = payload.get("period", existing.period)
            existing.updated_at = sa.func.now()
            action_label = "CAMPAIGN_BUDGET_UPDATED"
            description = f"Budget updated for campaign {campaign_id}"
            resource_id = existing.id
        else:
            existing = CampaignBudget(
                campaign_id=campaign_id,
                amount=amount,
                currency=payload.get("currency", "KES"),
                period=payload.get("period", "CAMPAIGN"),
            )
            db.add(existing)
            action_label = "CAMPAIGN_BUDGET_CREATED"
            description = f"Budget created for campaign {campaign_id}"
            resource_id = None

        campaign.updated_by = user_id
        db.flush()

        if resource_id is None:
            resource_id = existing.id

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action=action_label,
            resource_type="campaign_budget",
            resource_id=resource_id,
            description=description,
            request=request,
        )
        db.commit()
        return existing

    @staticmethod
    def get_budget(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        return db.execute(
            sa.select(CampaignBudget).where(CampaignBudget.campaign_id == campaign_id)
        ).scalar_one_or_none()


class CampaignProgressService:
    @staticmethod
    def get_progress(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        product_count = db.scalar(
            sa.select(sa.func.count()).where(
                CampaignProduct.campaign_id == campaign_id
            )
        )
        audience = db.execute(
            sa.select(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)
        ).scalar_one_or_none()
        offer = db.execute(
            sa.select(CampaignOffer).where(CampaignOffer.campaign_id == campaign_id)
        ).scalar_one_or_none()
        channel_count = db.scalar(
            sa.select(sa.func.count()).where(
                CampaignChannel.campaign_id == campaign_id
            )
        )
        budget = db.execute(
            sa.select(CampaignBudget).where(CampaignBudget.campaign_id == campaign_id)
        ).scalar_one_or_none()

        progress = {
            "product": "complete" if product_count else "incomplete",
            "objective": "complete" if campaign.objective else "incomplete",
            "audience": "complete" if audience else "incomplete",
            "offer": "complete" if offer else "incomplete",
            "channels": "complete" if channel_count else "incomplete",
            "creative": "incomplete",
            "budget": "complete" if budget else "incomplete",
        }

        checks = CampaignProgressService.get_readiness(db, campaign_id)["checks"]

        return {
            "campaign_id": campaign_id,
            "status": campaign.status,
            "progress": progress,
            "readiness": {
                "ready": all(c["status"] == "complete" for c in checks),
                "checks": checks,
            },
        }

    @staticmethod
    def get_readiness(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        product_count = db.scalar(
            sa.select(sa.func.count()).where(
                CampaignProduct.campaign_id == campaign_id
            )
        )
        audience = db.execute(
            sa.select(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)
        ).scalar_one_or_none()
        offer = db.execute(
            sa.select(CampaignOffer).where(CampaignOffer.campaign_id == campaign_id)
        ).scalar_one_or_none()
        channel_count = db.scalar(
            sa.select(sa.func.count()).where(
                CampaignChannel.campaign_id == campaign_id
            )
        )
        budget = db.execute(
            sa.select(CampaignBudget).where(CampaignBudget.campaign_id == campaign_id)
        ).scalar_one_or_none()

        checks = [
            {
                "key": "product",
                "status": "complete" if product_count else "incomplete",
                "message": "Products selected." if product_count else "No products added yet.",
            },
            {
                "key": "objective",
                "status": "complete" if campaign.objective else "incomplete",
                "message": "Objective set." if campaign.objective else "No objective defined.",
            },
            {
                "key": "audience",
                "status": "complete" if audience else "incomplete",
                "message": "Audience configured." if audience else "No audience defined.",
            },
            {
                "key": "offer",
                "status": "complete" if offer else "incomplete",
                "message": "Offer defined." if offer else "No offer defined.",
            },
            {
                "key": "channels",
                "status": "complete" if channel_count else "incomplete",
                "message": "Channels selected." if channel_count else "No channels selected.",
            },
            {
                "key": "creative",
                "status": "incomplete",
                "message": "Creative generation pending.",
            },
            {
                "key": "budget",
                "status": "complete" if budget else "incomplete",
                "message": "Budget set." if budget else "No budget defined.",
            },
        ]

        return {
            "ready": all(c["status"] == "complete" for c in checks),
            "checks": checks,
        }


class CampaignAnalyticsService:
    @staticmethod
    def track_event(db, campaign_id, event_type, event_data=None, user_id=None):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        if not event_type:
            raise ValidationError_("event_type is required.")

        event = CampaignAnalyticsEvent(
            campaign_id=campaign_id,
            event_type=event_type,
            event_data=event_data,
            user_id=user_id,
        )
        db.add(event)
        db.flush()
        db.commit()
        return event

    @staticmethod
    def record_event(db, campaign_id, event_type, *, metadata=None, user_id=None, request=None):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        if not event_type:
            raise ValidationError_("event_type is required.")

        event = CampaignAnalyticsEvent(
            campaign_id=campaign_id,
            event_type=event_type,
            event_data=metadata,
            user_id=user_id,
        )
        db.add(event)
        db.flush()
        db.commit()
        return event

    @staticmethod
    def get_events(db, campaign_id, event_type=None, limit=50):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        query = sa.select(CampaignAnalyticsEvent).where(
            CampaignAnalyticsEvent.campaign_id == campaign_id
        )
        if event_type:
            query = query.where(CampaignAnalyticsEvent.event_type == event_type)
        query = query.order_by(CampaignAnalyticsEvent.created_at.desc()).limit(limit)

        return db.execute(query).scalars().all()

    @staticmethod
    def list_events(db, campaign_id, event_type=None, limit=50):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        query = sa.select(CampaignAnalyticsEvent).where(
            CampaignAnalyticsEvent.campaign_id == campaign_id
        )
        if event_type:
            query = query.where(CampaignAnalyticsEvent.event_type == event_type)
        query = query.order_by(CampaignAnalyticsEvent.created_at.desc()).limit(limit)

        return db.execute(query).scalars().all()
