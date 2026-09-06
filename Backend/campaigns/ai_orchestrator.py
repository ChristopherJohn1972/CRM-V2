"""AI orchestration layer for campaign creative generation.

This module handles:
- Prompt construction from campaign context
- Structured output validation
- Generation job management
- Guardrails (product accuracy, brand compliance, content safety)
"""

import json
import logging
import uuid
from datetime import datetime

import sqlalchemy as sa

from common import audit
from common.exceptions import NotFoundError, ValidationError_
from campaigns.enums import (
    CampaignStatus,
    CreativeSource,
    CreativeStatus,
    GenerationJobStatus,
    GenerationJobType,
)
from campaigns.models import (
    AIGenerationJob,
    Campaign,
    CampaignAudience,
    CampaignBudget,
    CampaignChannel,
    CampaignOffer,
    Creative,
    CreativeConcept,
)

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Orchestrates AI generation of campaign creatives.

    This is the central coordinator for AI operations. It:
    1. Assembles context from campaign configuration
    2. Constructs structured prompts
    3. Manages generation jobs
    4. Validates AI output against guardrails
    5. Stores results as creative concepts and creatives
    """

    @staticmethod
    def build_generation_context(db, campaign_id):
        """Assemble all campaign data into an AI generation context dict."""
        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        target_products = campaign.target_products or []

        audience = db.execute(
            sa.select(CampaignAudience).where(
                CampaignAudience.campaign_id == campaign_id
            )
        ).scalar_one_or_none()

        offer = db.execute(
            sa.select(CampaignOffer).where(
                CampaignOffer.campaign_id == campaign_id
            )
        ).scalar_one_or_none()

        channels = db.execute(
            sa.select(CampaignChannel).where(
                CampaignChannel.campaign_id == campaign_id
            )
        ).scalars().all()

        budget = db.execute(
            sa.select(CampaignBudget).where(
                CampaignBudget.campaign_id == campaign_id
            )
        ).scalar_one_or_none()

        return {
            "campaign": {
                "name": campaign.name,
                "description": campaign.description,
                "objective": campaign.objective.value if campaign.objective else None,
                "campaign_type": campaign.campaign_type.value if campaign.campaign_type else None,
            },
            "products": [
                {
                    "reference": p,
                    "discount_type": None,
                    "discount_value": None,
                }
                for p in target_products
            ],
            "audience": {
                "type": audience.audience_type.value if audience else None,
                "configuration": audience.configuration if audience else None,
                "description": audience.description if audience else None,
            } if audience else None,
            "offer": {
                "type": offer.offer_type.value if offer else None,
                "value": float(offer.value) if offer and offer.value else None,
                "description": offer.description if offer else None,
            } if offer else None,
            "channels": [
                {"channel": ch.channel.value, "configuration": ch.configuration}
                for ch in channels
            ],
            "budget": {
                "amount": float(budget.amount) if budget else None,
                "currency": budget.currency if budget else "KES",
                "period": budget.period.value if budget else None,
            } if budget else None,
        }

    @staticmethod
    def build_prompt(context):
        """Construct a structured prompt from campaign context."""
        parts = []
        parts.append("Generate advertising campaign creative concepts.")
        parts.append("")

        campaign = context.get("campaign", {})
        if campaign.get("name"):
            parts.append(f"Campaign: {campaign['name']}")
        if campaign.get("description"):
            parts.append(f"Description: {campaign['description']}")
        if campaign.get("objective"):
            parts.append(f"Objective: {campaign['objective']}")

        products = context.get("products", [])
        if products:
            parts.append("")
            parts.append("Products:")
            for p in products:
                ref = p.get("reference", {})
                name = ref.get("name", "Unknown Product")
                parts.append(f"  - {name}")
                if p.get("discount_type") and p.get("discount_value"):
                    parts.append(f"    Discount: {p['discount_value']}% {p['discount_type']}")

        audience = context.get("audience")
        if audience and audience.get("type"):
            parts.append(f"\nTarget audience: {audience['type']}")
            if audience.get("description"):
                parts.append(f"Audience details: {audience['description']}")

        offer = context.get("offer")
        if offer and offer.get("type") and offer["type"] != "NONE":
            parts.append(f"\nOffer: {offer['type']}")
            if offer.get("value"):
                parts.append(f"Offer value: {offer['value']}")
            if offer.get("description"):
                parts.append(f"Offer details: {offer['description']}")

        channels = context.get("channels", [])
        if channels:
            channel_names = [ch["channel"] for ch in channels]
            parts.append(f"\nChannels: {', '.join(channel_names)}")

        parts.append("")
        parts.append("Generate 3 creative concepts with different strategies:")
        parts.append("1. Product focused - highlight the product features and benefits")
        parts.append("2. Offer focused - emphasize the promotion/deal")
        parts.append("3. Lifestyle focused - connect to the customer's aspirational lifestyle")
        parts.append("")
        parts.append("For each concept, provide:")
        parts.append("- strategy (PRODUCT_FOCUSED, OFFER_FOCUSED, or LIFESTYLE)")
        parts.append("- headline (short, punchy, memorable)")
        parts.append("- subheadline (supporting detail)")
        parts.append("- cta (call to action)")
        parts.append("- visual_direction (brief description of visual approach)")
        parts.append("- reasoning (why this concept works for this campaign)")

        return "\n".join(parts)

    @staticmethod
    def validate_output(output):
        """Validate AI-generated output against guardrails.

        Returns: (is_valid, errors_list)
        """
        errors = []

        if not isinstance(output, dict):
            return False, ["Output must be a dictionary"]

        concepts = output.get("concepts")
        if not concepts or not isinstance(concepts, list):
            return False, ["Output must contain a 'concepts' list"]

        if len(concepts) == 0:
            return False, ["At least one concept is required"]

        required_fields = ["strategy", "headline", "cta"]
        valid_strategies = {
            "PRODUCT_FOCUSED", "OFFER_FOCUSED", "LIFESTYLE",
            "SOCIAL_PROOF", "URGENCY", "EDUCATIONAL", "CUSTOM",
        }
        harmful_terms = {"hate", "violence", "discrimination"}

        for i, concept in enumerate(concepts):
            for field in required_fields:
                value = concept.get(field)
                if not value or not isinstance(value, str) or not value.strip():
                    errors.append(f"Concept {i + 1}: '{field}' is required and must be non-empty")

            strategy = concept.get("strategy", "")
            if strategy not in valid_strategies:
                errors.append(f"Concept {i + 1}: invalid strategy '{strategy}'")

            headline = concept.get("headline", "").lower()
            for term in harmful_terms:
                if term in headline:
                    errors.append(f"Concept {i + 1}: headline contains potentially inappropriate content")
                    break

        return len(errors) == 0, errors

    @staticmethod
    def create_generation_job(
        db, campaign_id, user_id, *,
        job_type, creative_id=None, model=None,
        request_payload=None, idempotency_key=None, request=None,
    ):
        if not idempotency_key:
            idempotency_key = f"job-{uuid.uuid4().hex[:16]}"

        job_type_val = job_type.value if hasattr(job_type, "value") else job_type

        job = AIGenerationJob(
            campaign_id=campaign_id,
            creative_id=creative_id,
            job_type=job_type_val,
            model=model,
            status=GenerationJobStatus.PENDING.value,
            request_payload=request_payload,
            idempotency_key=idempotency_key,
        )
        db.add(job)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="AI_JOB_CREATED",
            resource_type="ai_generation_job",
            resource_id=job.id,
            description=f"AI generation job '{job_type_val}' created for campaign {campaign_id}",
            request=request,
        )
        db.commit()
        return job

    @staticmethod
    def update_job_status(db, job_id, status, *,
                          response_payload=None, error_message=None,
                          token_count=None, cost=None):
        job = db.get(AIGenerationJob, job_id)
        if job is None:
            raise NotFoundError("Generation job not found.")

        status_val = status.value if hasattr(status, "value") else status
        job.status = status_val
        if response_payload is not None:
            job.response_payload = response_payload
        if error_message is not None:
            job.error_message = error_message
        if token_count is not None:
            job.token_count = token_count
        if cost is not None:
            job.cost = cost
        if status_val in (GenerationJobStatus.COMPLETED.value, GenerationJobStatus.FAILED.value):
            job.completed_at = datetime.utcnow()

        db.flush()
        db.commit()
        return job

    @staticmethod
    def get_job(db, job_id):
        job = db.get(AIGenerationJob, job_id)
        if job is None:
            raise NotFoundError("Generation job not found.")
        return job

    @staticmethod
    def get_job_by_idempotency(db, idempotency_key):
        return db.execute(
            sa.select(AIGenerationJob).where(
                AIGenerationJob.idempotency_key == idempotency_key
            )
        ).scalar_one_or_none()

    @staticmethod
    def process_generation_result(db, job_id, user_id, concepts_output, *, request=None):
        """Process validated AI output into creative concepts and creatives.

        1. Validate output
        2. Create CreativeConcept for each concept
        3. Create Creative (v1) for each concept
        4. Mark first concept as selected
        5. Update job status and campaign status
        """
        job = db.get(AIGenerationJob, job_id)
        if job is None:
            raise NotFoundError("Generation job not found.")

        is_valid, errors = AIOrchestrator.validate_output(concepts_output)
        if not is_valid:
            AIOrchestrator.update_job_status(
                db, job_id, GenerationJobStatus.FAILED,
                error_message="; ".join(errors),
            )
            db.commit()
            raise ValidationError_(f"AI output validation failed: {'; '.join(errors)}")

        concepts_data = concepts_output.get("concepts", [])
        created_concepts = []
        created_creatives = []

        for i, concept_data in enumerate(concepts_data):
            concept = CreativeConcept(
                campaign_id=job.campaign_id,
                strategy=concept_data.get("strategy", "CUSTOM"),
                description=concept_data.get("reasoning", ""),
                recommendation_reason=concept_data.get("reasoning"),
                is_selected=(i == 0),
            )
            db.add(concept)
            db.flush()

            creative = Creative(
                campaign_id=job.campaign_id,
                concept_id=concept.id,
                version=1,
                status=CreativeStatus.DRAFT.value,
                headline={"value": concept_data.get("headline", ""), "source": "ai"},
                subheadline={"value": concept_data.get("subheadline", ""), "source": "ai"},
                cta={"value": concept_data.get("cta", ""), "source": "ai"},
                visual_direction=concept_data.get("visual_direction", ""),
                source=CreativeSource.AI.value,
                is_selected=(i == 0),
                ai_model=job.model,
                generation_version=1,
            )
            db.add(creative)
            db.flush()

            created_concepts.append(concept)
            created_creatives.append(creative)

        job.status = GenerationJobStatus.COMPLETED.value
        job.response_payload = concepts_output
        job.completed_at = datetime.utcnow()

        campaign = db.get(Campaign, job.campaign_id)
        if campaign and campaign.status in (
            CampaignStatus.CREATIVE_GENERATING.value,
            CampaignStatus.CONFIGURING.value,
            CampaignStatus.PRODUCT_SELECTED.value,
        ):
            campaign.status = CampaignStatus.CREATIVE_READY.value

        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="AI_JOB_COMPLETED",
            resource_type="ai_generation_job",
            resource_id=job_id,
            description=f"AI generation completed: {len(created_concepts)} concepts, {len(created_creatives)} creatives",
            metadata={
                "concepts_created": len(created_concepts),
                "creatives_created": len(created_creatives),
            },
            request=request,
        )
        db.commit()

        return {
            "concepts": created_concepts,
            "creatives": created_creatives,
            "job": job,
        }

    @staticmethod
    def generate_billboard(db, campaign_id, user_id, *, creative_id=None, template="hero", product_image_url=None, request=None):
        """Generate billboard image for a campaign.

        Tries AI image generation (DALL-E 3) first. Falls back to Pillow
        composition when AI is not configured or fails.
        Creates a CreativeAsset with the generated image.
        """
        from campaigns.models import CreativeAsset

        campaign = db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found.")

        product_img_url = product_image_url
        target_products = campaign.target_products or []
        if not product_img_url and target_products:
            ref = target_products[0] if isinstance(target_products[0], dict) else {}
            product_img_url = ref.get("image_url") or ref.get("image")

        headline = None
        subheadline = None
        offer_text = None
        cta_text = None

        if creative_id:
            creative = db.get(Creative, creative_id)
            if creative:
                headline = creative.headline.get("value") if isinstance(creative.headline, dict) else creative.headline
                subheadline = creative.subheadline.get("value") if isinstance(creative.subheadline, dict) else creative.subheadline
                cta_text = creative.cta.get("value") if isinstance(creative.cta, dict) else creative.cta

        from campaigns.models import CampaignOffer
        offer = db.execute(
            sa.select(CampaignOffer).where(CampaignOffer.campaign_id == campaign_id)
        ).scalar_one_or_none()
        if offer and offer.offer_type and offer.offer_type.value != "NONE":
            if offer.value:
                offer_text = f"{offer.value}% OFF" if offer.offer_type.value == "PERCENTAGE" else f"Save {offer.value}"
            elif offer.description:
                offer_text = offer.description

        product_name = "Our Product"
        product_description = ""
        if target_products:
            ref = target_products[0] if isinstance(target_products[0], dict) else {}
            product_name = ref.get("name", product_name)
            product_description = ref.get("description", "")

        if not headline:
            headline = product_name if product_name != "Our Product" else (campaign.name or "New Campaign")
        if not cta_text:
            cta_text = "Shop Now"

        billboards = None
        ai_model_used = "pillow-composer"

        from campaigns.ai_image_generator import is_available as ai_available
        if ai_available():
            try:
                from campaigns.ai_image_generator import generate_image as ai_generate
                ai_result = ai_generate(
                    product_name=product_name,
                    product_description=product_description,
                    offer_text=offer_text,
                    template=template,
                    campaign_id=campaign_id,
                    extra_context=campaign.description or "",
                )
                billboards = {template: ai_result}
                ai_model_used = "dall-e-3"
                logger.info("AI image generated for campaign %s", campaign_id)
            except Exception as exc:
                logger.warning("AI generation failed, falling back to Pillow: %s", exc)
                billboards = None

        if billboards is None:
            from campaigns.image_service import generate_multi_template
            billboards = generate_multi_template(
                product_image_url=product_img_url,
                headline=headline,
                subheadline=subheadline,
                offer_text=offer_text,
                cta_text=cta_text,
                campaign_id=campaign_id,
            )

        if creative_id is None:
            creative = Creative(
                campaign_id=campaign_id,
                version=1,
                status=CreativeStatus.READY.value,
                headline={"value": headline, "source": "ai"},
                subheadline={"value": subheadline or "", "source": "ai"},
                cta={"value": cta_text, "source": "ai"},
                source=CreativeSource.AI.value,
                is_selected=True,
                ai_model=ai_model_used,
                generation_version=1,
            )
            db.add(creative)
            db.flush()
        else:
            creative = db.get(Creative, creative_id)

        assets_created = []
        for template_name, result in billboards.items():
            asset = CreativeAsset(
                creative_id=creative.id,
                asset_type="BANNER",
                storage_key=result["storage_key"],
                mime_type=result["mime_type"],
                width=result["width"],
                height=result["height"],
                aspect_ratio=f"{result['width']}:{result['height']}",
                channel=template_name,
            )
            db.add(asset)
            assets_created.append(asset)

        primary = billboards.get(template) or billboards.get("hero") or next(iter(billboards.values()))
        creative.image_url = primary["storage_key"]
        creative.visual_direction = f"Template: {template} | Generated billboards: {', '.join(billboards.keys())}"

        campaign_obj = db.get(Campaign, campaign_id)
        if campaign_obj and campaign_obj.status in (
            CampaignStatus.CREATIVE_GENERATING.value,
            CampaignStatus.CONFIGURING.value,
            CampaignStatus.PRODUCT_SELECTED.value,
            CampaignStatus.CREATIVE_READY.value,
        ):
            campaign_obj.status = CampaignStatus.CREATIVE_READY.value

        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="BILLBOARD_GENERATED",
            resource_type="creative",
            resource_id=creative.id,
            description=f"Billboard generated: {len(billboards)} templates for campaign {campaign_id}",
            metadata={"templates": list(billboards.keys()), "primary_template": template},
            request=request,
        )
        db.commit()

        return {
            "creative_id": creative.id,
            "primary_template": template,
            "provider": ai_model_used,
            "billboards": {
                name: {
                    "storage_key": r["storage_key"],
                    "width": r["width"],
                    "height": r["height"],
                }
                for name, r in billboards.items()
            },
            "assets_created": len(assets_created),
        }
