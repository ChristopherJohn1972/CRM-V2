"""Creative concept, creative versioning, and asset management."""

import logging

import sqlalchemy as sa

from common import audit
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from campaigns.enums import (
    CreativeStatus,
    CreativeSource,
)
from campaigns.models import (
    Campaign,
    Creative,
    CreativeAsset,
    CreativeConcept,
)

logger = logging.getLogger(__name__)


class CreativeConceptService:
    @staticmethod
    def create_concept(
        db, campaign_id, strategy, user_id, *,
        description=None, recommendation_reason=None, request=None,
    ):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        concept = CreativeConcept(
            campaign_id=campaign_id,
            strategy=strategy,
            description=description,
            recommendation_reason=recommendation_reason,
        )
        db.add(concept)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_CONCEPT_CREATED",
            resource_type="creative_concept",
            resource_id=concept.id,
            description=f"Creative concept '{strategy}' created for campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return concept

    @staticmethod
    def list_concepts(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        return db.execute(
            sa.select(CreativeConcept)
            .where(CreativeConcept.campaign_id == campaign_id)
            .order_by(CreativeConcept.created_at.desc())
        ).scalars().all()

    @staticmethod
    def get_concept(db, concept_id):
        concept = db.get(CreativeConcept, concept_id)
        if concept is None:
            raise NotFoundError("Creative concept not found.")
        return concept

    @staticmethod
    def select_concept(db, campaign_id, concept_id, user_id, *, request=None):
        concept = db.execute(
            sa.select(CreativeConcept).where(
                CreativeConcept.id == concept_id,
                CreativeConcept.campaign_id == campaign_id,
            )
        ).scalar_one_or_none()
        if concept is None:
            raise NotFoundError("Concept not found in this campaign.")

        db.execute(
            sa.update(CreativeConcept)
            .where(
                CreativeConcept.campaign_id == campaign_id,
                CreativeConcept.is_selected == sa.true(),
            )
            .values(is_selected=False)
        )

        concept.is_selected = True
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_CONCEPT_SELECTED",
            resource_type="creative_concept",
            resource_id=concept_id,
            description=f"Creative concept {concept_id} selected for campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return concept

    @staticmethod
    def get_selected_concept(db, campaign_id):
        return db.execute(
            sa.select(CreativeConcept).where(
                CreativeConcept.campaign_id == campaign_id,
                CreativeConcept.is_selected == sa.true(),
            )
        ).scalar_one_or_none()


class CreativeService:
    @staticmethod
    def _next_version(db, campaign_id):
        max_ver = db.scalar(
            sa.select(sa.func.max(Creative.version)).where(
                Creative.campaign_id == campaign_id
            )
        )
        return (max_ver or 0) + 1

    @staticmethod
    def create_creative(
        db, campaign_id, user_id, *,
        concept_id=None, headline=None, subheadline=None,
        cta=None, visual_direction=None, source=CreativeSource.AI,
        ai_model=None, request=None,
    ):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        version = CreativeService._next_version(db, campaign_id)

        creative = Creative(
            campaign_id=campaign_id,
            concept_id=concept_id,
            version=version,
            status=CreativeStatus.DRAFT.value,
            headline=headline,
            subheadline=subheadline,
            cta=cta,
            visual_direction=visual_direction,
            source=source.value if hasattr(source, "value") else source,
            ai_model=ai_model,
        )
        db.add(creative)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_CREATED",
            resource_type="creative",
            resource_id=creative.id,
            description=f"Creative v{version} created for campaign {campaign_id}",
            metadata={"version": version, "source": creative.source},
            request=request,
        )
        db.commit()
        return creative

    @staticmethod
    def get_creative(db, creative_id):
        creative = db.get(Creative, creative_id)
        if creative is None:
            raise NotFoundError("Creative not found.")
        return creative

    @staticmethod
    def get_selected_creative(db, campaign_id):
        return db.execute(
            sa.select(Creative).where(
                Creative.campaign_id == campaign_id,
                Creative.is_selected == sa.true(),
            )
        ).scalar_one_or_none()

    @staticmethod
    def list_creatives(db, campaign_id):
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        return db.execute(
            sa.select(Creative)
            .where(Creative.campaign_id == campaign_id)
            .order_by(Creative.version.desc())
        ).scalars().all()

    @staticmethod
    def update_creative(db, creative_id, user_id, payload, *, request=None):
        creative = db.get(Creative, creative_id)
        if creative is None:
            raise NotFoundError("Creative not found.")
        if creative.status in (CreativeStatus.APPROVED.value,):
            raise ConflictError("Cannot edit an approved creative.")

        updatable = ["headline", "subheadline", "cta", "visual_direction", "status"]
        for field in updatable:
            if field in payload and payload[field] is not None:
                setattr(creative, field, payload[field])

        text_fields = ["headline", "subheadline", "cta"]
        if any(f in payload for f in text_fields):
            if creative.source == CreativeSource.AI.value:
                creative.source = CreativeSource.HYBRID.value
            else:
                creative.source = CreativeSource.USER.value

        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_UPDATED",
            resource_type="creative",
            resource_id=creative_id,
            description=f"Creative {creative_id} updated",
            metadata={"fields_changed": [k for k in payload if k in updatable]},
            request=request,
        )
        db.commit()
        return creative

    @staticmethod
    def select_creative(db, campaign_id, creative_id, user_id, *, request=None):
        creative = db.execute(
            sa.select(Creative).where(
                Creative.id == creative_id,
                Creative.campaign_id == campaign_id,
            )
        ).scalar_one_or_none()
        if creative is None:
            raise NotFoundError("Creative not found in this campaign.")

        db.execute(
            sa.update(Creative)
            .where(
                Creative.campaign_id == campaign_id,
                Creative.is_selected == sa.true(),
            )
            .values(is_selected=False)
        )

        creative.is_selected = True
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_SELECTED",
            resource_type="creative",
            resource_id=creative_id,
            description=f"Creative {creative_id} selected for campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return creative

    @staticmethod
    def mark_stale(db, campaign_id, user_id=None):
        updated = db.execute(
            sa.update(Creative)
            .where(
                Creative.campaign_id == campaign_id,
                Creative.status.in_([
                    CreativeStatus.READY.value,
                    CreativeStatus.APPROVED.value,
                ]),
            )
            .values(status=CreativeStatus.STALE.value)
        ).rowcount
        if updated:
            db.flush()
            logger.info("Marked %d creatives as STALE for campaign %d", updated, campaign_id)
            audit.record_audit(
                db,
                actor_user_id=user_id,
                action="CREATIVES_MARKED_STALE",
                resource_type="creative",
                resource_id=campaign_id,
                description=f"{updated} creatives marked as STALE for campaign {campaign_id}",
            )
        return updated

    @staticmethod
    def regenerate_creative(db, creative_id, user_id, *, request=None):
        old = db.get(Creative, creative_id)
        if old is None:
            raise NotFoundError("Creative not found.")

        version = CreativeService._next_version(db, old.campaign_id)

        new_creative = Creative(
            campaign_id=old.campaign_id,
            concept_id=old.concept_id,
            version=version,
            status=CreativeStatus.DRAFT.value,
            headline=old.headline,
            subheadline=old.subheadline,
            cta=old.cta,
            visual_direction=old.visual_direction,
            source=old.source,
            ai_model=old.ai_model,
        )
        db.add(new_creative)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_REGENERATED",
            resource_type="creative",
            resource_id=new_creative.id,
            description=f"Creative regenerated: v{old.version} -> v{version} for campaign {old.campaign_id}",
            metadata={"original_id": creative_id, "new_version": version},
            request=request,
        )
        db.commit()
        return new_creative


class CreativeAssetService:
    @staticmethod
    def create_asset(
        db, creative_id, user_id, *,
        asset_type, storage_key, mime_type=None,
        width=None, height=None, aspect_ratio=None,
        channel=None, thumbnail_key=None,
        generation_job_id=None, request=None,
    ):
        creative = db.get(Creative, creative_id)
        if creative is None:
            raise NotFoundError("Creative not found.")

        asset = CreativeAsset(
            creative_id=creative_id,
            asset_type=asset_type,
            storage_key=storage_key,
            thumbnail_key=thumbnail_key,
            mime_type=mime_type,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            channel=channel,
            generation_job_id=generation_job_id,
        )
        db.add(asset)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_ASSET_CREATED",
            resource_type="creative_asset",
            resource_id=asset.id,
            description=f"Asset '{asset_type}' created for creative {creative_id}",
            request=request,
        )
        db.commit()
        return asset

    @staticmethod
    def list_assets(db, creative_id, asset_type=None):
        query = sa.select(CreativeAsset).where(
            CreativeAsset.creative_id == creative_id
        )
        if asset_type:
            query = query.where(CreativeAsset.asset_type == asset_type)
        query = query.order_by(CreativeAsset.created_at.desc())

        return db.execute(query).scalars().all()

    @staticmethod
    def get_asset(db, asset_id):
        asset = db.get(CreativeAsset, asset_id)
        if asset is None:
            raise NotFoundError("Creative asset not found.")
        return asset

    @staticmethod
    def delete_asset(db, asset_id, user_id, *, request=None):
        asset = db.get(CreativeAsset, asset_id)
        if asset is None:
            raise NotFoundError("Creative asset not found.")

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="CREATIVE_ASSET_DELETED",
            resource_type="creative_asset",
            resource_id=asset_id,
            description=f"Asset {asset_id} deleted from creative {asset.creative_id}",
            request=request,
        )
        db.delete(asset)
        db.commit()
