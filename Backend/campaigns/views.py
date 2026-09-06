import logging
import uuid
import os
import sqlalchemy as sa
from django.conf import settings
from django.http import HttpResponse
from pathlib import Path
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from iam.permissions import UserPrincipal
from campaigns.access import can_access_campaign, scope_campaign_queryset
from campaigns.models import Campaign, CampaignAnalyticsEvent, CampaignBudget, CampaignCode, CampaignSchedule, CampaignSource
from campaigns.serializers import (
    CampaignCodeReadSerializer,
    CampaignCodeWriteSerializer,
    CampaignReadSerializer,
    CampaignScheduleWriteSerializer,
    CampaignSourceReadSerializer,
    CampaignSourceWriteSerializer,
    CampaignTransitionSerializer,
    CampaignUpdateSerializer,
    CampaignWriteSerializer,
)
from campaigns.services import (
    CampaignCodeService,
    CampaignScheduleService,
    CampaignService,
    CampaignSourceService,
)

logger = logging.getLogger(__name__)

PERMISSION_CAMPAIGN_VIEW = "campaign.view"
PERMISSION_CAMPAIGN_CREATE = "campaign.create"
PERMISSION_CAMPAIGN_EDIT = "campaign.edit"
PERMISSION_CAMPAIGN_DELETE = "campaign.delete"
PERMISSION_CAMPAIGN_ACTIVATE = "campaign.activate"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        from common.exceptions import PermissionDeniedError
        raise PermissionDeniedError(f"Missing required permission: {code}")


def _get_campaign(db, request, campaign_id):
    from common.exceptions import NotFoundError, PermissionDeniedError
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    if not can_access_campaign(db, _principal(request), campaign):
        raise PermissionDeniedError()
    return campaign


class CampaignListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            stmt = sa.select(Campaign).where(Campaign.deleted_at.is_(None))
            stmt = scope_campaign_queryset(session, principal, stmt)

            search = request.query_params.get("search")
            if search:
                stmt = stmt.where(Campaign.name.ilike(f"%{search}%"))

            status_filter = request.query_params.get("status")
            if status_filter:
                stmt = stmt.where(Campaign.status == status_filter)

            campaign_type = request.query_params.get("campaign_type")
            if campaign_type:
                stmt = stmt.where(Campaign.campaign_type == campaign_type)

            stmt = stmt.order_by(sa.desc(Campaign.campaign_id))

            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
            offset = (page_number - 1) * page_size

            rows = session.execute(stmt.limit(page_size).offset(offset)).scalars().all()
            data = [CampaignReadSerializer(row).data for row in rows]

            return Response({
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": data,
            })
        finally:
            session.close()

    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_CREATE)

        serializer = CampaignWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            campaign = CampaignService.create_campaign(
                session, payload, principal.user_id, request=request
            )
            return Response(
                CampaignReadSerializer(campaign).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class CampaignDetailView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            campaign = _get_campaign(session, request, campaign_id)
            return Response(CampaignReadSerializer(campaign).data)
        finally:
            session.close()

    def put(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            campaign = CampaignService.update_campaign(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(CampaignReadSerializer(campaign).data)
        finally:
            session.close()

    def delete(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_DELETE)

        session = SessionLocal()
        try:
            CampaignService.delete_campaign(
                session, campaign_id, principal.user_id, request=request
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


class CampaignTransitionView(APIView):
    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["new_status"]
        reason = serializer.validated_data.get("reason")

        session = SessionLocal()
        try:
            campaign = CampaignService.transition_campaign(
                session, campaign_id, new_status, principal.user_id, reason=reason, request=request
            )
            return Response(CampaignReadSerializer(campaign).data)
        finally:
            session.close()


class CampaignCodeListView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            _get_campaign(session, request, campaign_id)
            stmt = sa.select(CampaignCode).where(CampaignCode.campaign_id == campaign_id)
            stmt = stmt.order_by(sa.desc(CampaignCode.id))
            rows = session.execute(stmt).scalars().all()
            data = [CampaignCodeReadSerializer(row).data for row in rows]
            return Response({"results": data})
        finally:
            session.close()

    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignCodeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            cc = CampaignCodeService.create_code(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(
                CampaignCodeReadSerializer(cc).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class CampaignSourceListView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            _get_campaign(session, request, campaign_id)
            stmt = sa.select(CampaignSource).where(CampaignSource.campaign_id == campaign_id)
            stmt = stmt.order_by(sa.desc(CampaignSource.id))
            rows = session.execute(stmt).scalars().all()
            data = [CampaignSourceReadSerializer(row).data for row in rows]
            return Response({"results": data})
        finally:
            session.close()

    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignSourceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            cs = CampaignSourceService.create_source(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(
                CampaignSourceReadSerializer(cs).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class CampaignScheduleListView(APIView):
    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignScheduleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        session = SessionLocal()
        try:
            sched = CampaignScheduleService.create_schedule(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(
                {"id": sched.id, "action": sched.action, "scheduled_at": str(sched.scheduled_at)},
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


# ============================================================================
# AI Campaign Builder Views
# ============================================================================

from campaigns.ai_services import (
    CampaignProductService,
    CampaignAudienceService,
    CampaignOfferService,
    CampaignChannelService,
    CampaignBudgetService,
    CampaignProgressService,
    CampaignAnalyticsService,
)
from campaigns.creative_services import (
    CreativeConceptService,
    CreativeService,
    CreativeAssetService,
)
from campaigns.ai_orchestrator import AIOrchestrator
from campaigns.launch_services import (
    CampaignReadinessService,
    CampaignLaunchService,
)
from campaigns.serializers import (
    CampaignProductWriteSerializer,
    CampaignProductReadSerializer,
    CampaignAudienceWriteSerializer,
    CampaignAudienceReadSerializer,
    CampaignOfferWriteSerializer,
    CampaignOfferReadSerializer,
    CampaignChannelWriteSerializer,
    CampaignChannelReadSerializer,
    CampaignBudgetWriteSerializer,
    CampaignBudgetReadSerializer,
    CreativeConceptReadSerializer,
    CreativeReadSerializer,
    CreativeWriteSerializer,
    CreativeAssetReadSerializer,
    AIGenerationJobReadSerializer,
    CampaignReadinessSerializer,
    CampaignProgressSerializer,
    CampaignLaunchReadSerializer,
    AIGenerateRequestSerializer,
)
from campaigns.models import Campaign
from campaigns.enums import CampaignStatus


PERMISSION_CAMPAIGN_GENERATE = "campaign.generate_creative"
PERMISSION_CAMPAIGN_LAUNCH = "campaign.launch"


class CampaignProductView(APIView):
    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session = SessionLocal()
        try:
            result = CampaignProductService.add_products(
                session, campaign_id, payload["product_ids"], principal.user_id, request=request
            )
            return Response({"ok": True, "count": len(result)}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()

    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            products = CampaignProductService.list_products(session, campaign_id)
            data = [CampaignProductReadSerializer(p).data for p in products]
            return Response({"results": data})
        finally:
            session.close()

    def delete(self, request, campaign_id, product_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        session = SessionLocal()
        try:
            CampaignProductService.remove_product(session, campaign_id, product_id, principal.user_id, request=request)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignAudienceView(APIView):
    def put(self, request, campaign_id):
        return self._upsert(request, campaign_id)

    def post(self, request, campaign_id):
        return self._upsert(request, campaign_id)

    def _upsert(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignAudienceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session = SessionLocal()
        try:
            result = CampaignAudienceService.upsert_audience(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(CampaignAudienceReadSerializer(result).data)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()

    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            audience = CampaignAudienceService.get_audience(session, campaign_id)
            if not audience:
                return Response({"results": None})
            return Response(CampaignAudienceReadSerializer(audience).data)
        finally:
            session.close()


class CampaignOfferView(APIView):
    def put(self, request, campaign_id):
        return self._upsert(request, campaign_id)

    def post(self, request, campaign_id):
        return self._upsert(request, campaign_id)

    def _upsert(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignOfferWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session = SessionLocal()
        try:
            result = CampaignOfferService.upsert_offer(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(CampaignOfferReadSerializer(result).data)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()

    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            offer = CampaignOfferService.get_offer(session, campaign_id)
            if not offer:
                return Response({"results": None})
            return Response(CampaignOfferReadSerializer(offer).data)
        finally:
            session.close()


class CampaignChannelView(APIView):
    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignChannelWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session = SessionLocal()
        try:
            result = CampaignChannelService.add_channel(
                session, campaign_id, payload["channel"],
                payload.get("configuration"), principal.user_id, request=request
            )
            return Response(CampaignChannelReadSerializer(result).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()

    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            channels = CampaignChannelService.list_channels(session, campaign_id)
            data = [CampaignChannelReadSerializer(c).data for c in channels]
            return Response({"results": data})
        finally:
            session.close()

    def delete(self, request, campaign_id, channel_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        session = SessionLocal()
        try:
            CampaignChannelService.remove_channel(session, campaign_id, channel_id, principal.user_id, request=request)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignBudgetView(APIView):
    def put(self, request, campaign_id):
        return self._upsert(request, campaign_id)

    def post(self, request, campaign_id):
        return self._upsert(request, campaign_id)

    def _upsert(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CampaignBudgetWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session = SessionLocal()
        try:
            result = CampaignBudgetService.upsert_budget(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(CampaignBudgetReadSerializer(result).data)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()

    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            budget = CampaignBudgetService.get_budget(session, campaign_id)
            if not budget:
                return Response({"results": None})
            return Response(CampaignBudgetReadSerializer(budget).data)
        finally:
            session.close()


class CampaignAIGenerateView(APIView):
    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = AIGenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session = SessionLocal()
        try:
            context = AIOrchestrator.build_generation_context(session, campaign_id)
            prompt = AIOrchestrator.build_prompt(context)

            job = AIOrchestrator.create_generation_job(
                session, campaign_id, "FULL_CREATIVE",
                model=payload.get("model", "gpt-4"),
                request_payload={"prompt": prompt, "context": context},
                idempotency_key=payload.get("idempotency_key"),
                request=request,
            )

            campaign = session.get(Campaign, campaign_id)
            if campaign and campaign.status in (
                CampaignStatus.DRAFT.value,
                CampaignStatus.PRODUCT_SELECTED.value,
                CampaignStatus.CONFIGURING.value,
            ):
                campaign.status = CampaignStatus.CREATIVE_GENERATING.value
                session.flush()

            session.commit()

            return Response(
                {
                    "job_id": job.id,
                    "status": job.status,
                    "message": "Generation started. Poll /ai/jobs/{job_id} for results.",
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignAIJobView(APIView):
    def get(self, request, campaign_id, job_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            job = AIOrchestrator.get_job(session, job_id)
            return Response(AIGenerationJobReadSerializer(job).data)
        finally:
            session.close()


class CampaignConceptsView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            concepts = CreativeConceptService.list_concepts(session, campaign_id)
            data = [CreativeConceptReadSerializer(c).data for c in concepts]
            return Response({"results": data})
        finally:
            session.close()


class CampaignConceptSelectView(APIView):
    def post(self, request, campaign_id, concept_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        session = SessionLocal()
        try:
            concept = CreativeConceptService.select_concept(
                session, campaign_id, concept_id, principal.user_id, request=request
            )
            return Response(CreativeConceptReadSerializer(concept).data)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignCreativeView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            creative = CreativeService.get_selected_creative(session, campaign_id)
            if not creative:
                return Response({"results": None})
            return Response(CreativeReadSerializer(creative).data)
        finally:
            session.close()

    def put(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        session = SessionLocal()
        try:
            creative = CreativeService.get_selected_creative(session, campaign_id)
            if not creative:
                return Response({"detail": "No selected creative"}, status=status.HTTP_404_NOT_FOUND)

            serializer = CreativeWriteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            payload = serializer.validated_data

            result = CreativeService.update_creative(
                session, creative.id, payload, principal.user_id, request=request
            )
            return Response(CreativeReadSerializer(result).data)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()

    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        serializer = CreativeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        session = SessionLocal()
        try:
            result = CreativeService.create_creative(
                session, campaign_id, payload, principal.user_id, request=request
            )
            return Response(CreativeReadSerializer(result).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignCreativeAllView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            creatives = CreativeService.list_creatives(session, campaign_id)
            data = [CreativeReadSerializer(c).data for c in creatives]
            return Response({"results": data})
        finally:
            session.close()


class CampaignCreativeRegenerateView(APIView):
    def post(self, request, campaign_id, creative_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        session = SessionLocal()
        try:
            creative = CreativeService.regenerate_creative(
                session, creative_id, principal.user_id, request=request
            )
            return Response(CreativeReadSerializer(creative).data)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignReadinessView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            result = CampaignReadinessService.check_readiness(session, campaign_id)
            return Response(result)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignProgressView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            result = CampaignProgressService.get_progress(session, campaign_id)
            return Response(result)
        finally:
            session.close()


class CampaignLaunchView(APIView):
    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_LAUNCH)

        payload = request.data if request.data else {}
        idempotency_key = payload.get("idempotency_key")

        session = SessionLocal()
        try:
            result = CampaignLaunchService.launch(
                session, campaign_id, principal.user_id,
                idempotency_key=idempotency_key,
                request=request,
            )
            return Response(CampaignLaunchReadSerializer(result).data)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignAnalyticsView(APIView):
    def get(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        event_type = request.query_params.get("event_type")
        limit = int(request.query_params.get("limit", 50))

        session = SessionLocal()
        try:
            _get_campaign(session, request, campaign_id)
            events = CampaignAnalyticsService.list_events(
                session, campaign_id, event_type=event_type, limit=limit
            )
            data = [
                {
                    "id": e.id,
                    "campaign_id": e.campaign_id,
                    "event_type": e.event_type,
                    "event_data": e.event_data,
                    "user_id": e.user_id,
                    "created_at": str(e.created_at),
                }
                for e in events
            ]
            return Response({"results": data})
        finally:
            session.close()


class CampaignBillboardView(APIView):
    """POST /campaigns/{id}/billboard — generate billboard images from product + text"""

    def post(self, request, campaign_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        payload = request.data if request.data else {}
        template = payload.get("template", "hero")
        creative_id = payload.get("creative_id")
        product_image_url = payload.get("product_image_url")

        session = SessionLocal()
        try:
            result = AIOrchestrator.generate_billboard(
                session, campaign_id, principal.user_id,
                creative_id=creative_id,
                template=template,
                product_image_url=product_image_url,
                request=request,
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as exc:
            session.rollback()
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            session.close()


class CampaignProductImageView(APIView):
    """POST /campaigns/upload-image/ — upload a product image for campaign generation."""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_EDIT)

        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        allowed = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/jpg"}
        if file.content_type not in allowed:
            return Response(
                {"detail": f"Unsupported file type: {file.content_type}. Allowed: JPEG, PNG, WebP, GIF."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            return Response({"detail": "File too large. Maximum size is 10MB."}, status=status.HTTP_400_BAD_REQUEST)

        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else "png"
        filename = f"product_{uuid.uuid4().hex[:12]}.{ext}"
        storage_root = Path(getattr(settings, "STORAGE_ROOT", "storage/"))
        if not os.path.isabs(storage_root):
            storage_root = Path(settings.BASE_DIR) / storage_root
        subdir = storage_root / "campaign_products"
        subdir.mkdir(parents=True, exist_ok=True)
        filepath = subdir / filename

        with open(filepath, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        storage_key = f"campaign_products/{filename}"
        url = f"/api/storage/{storage_key}"

        return Response({
            "url": url,
            "storage_key": storage_key,
            "filename": filename,
            "content_type": file.content_type,
            "size": file.size,
        }, status=status.HTTP_201_CREATED)


class CampaignDashboardKPIView(APIView):
    """GET /campaigns/dashboard/kpis — aggregate KPI metrics across all campaigns."""

    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CAMPAIGN_VIEW)

        session = SessionLocal()
        try:
            from leads.models import Lead
            from leads.enums import LeadStatus
            from campaigns.enums import CampaignStatus

            base_q = sa.select(Campaign)
            base_q = scope_campaign_queryset(session, principal, base_q)
            base_sub = base_q.subquery()

            total_campaigns = session.execute(
                sa.select(sa.func.count()).select_from(base_sub)
            ).scalar() or 0

            active_campaigns = session.execute(
                sa.select(sa.func.count()).select_from(base_sub).where(
                    base_sub.c.status == CampaignStatus.ACTIVE.value
                )
            ).scalar() or 0

            campaign_ids_q = sa.select(base_sub.c.campaign_id)

            total_leads = session.execute(
                sa.select(sa.func.count()).where(
                    Lead.source_campaign_id.in_(campaign_ids_q)
                )
            ).scalar() or 0

            qualified_leads = session.execute(
                sa.select(sa.func.count()).where(
                    Lead.source_campaign_id.in_(campaign_ids_q),
                    Lead.status == LeadStatus.QUALIFIED.value,
                )
            ).scalar() or 0

            converted_leads = session.execute(
                sa.select(sa.func.count()).where(
                    Lead.source_campaign_id.in_(campaign_ids_q),
                    Lead.status == LeadStatus.CONVERTED.value,
                )
            ).scalar() or 0

            total_interactions = session.execute(
                sa.select(sa.func.count()).where(
                    CampaignAnalyticsEvent.campaign_id.in_(campaign_ids_q)
                )
            ).scalar() or 0

            budget_row = session.execute(
                sa.select(sa.func.coalesce(sa.func.sum(CampaignBudget.amount), 0)).where(
                    CampaignBudget.campaign_id.in_(campaign_ids_q)
                )
            ).scalar()

            total_spend = float(budget_row) if budget_row else 0.0
            cost_per_lead = round(total_spend / total_leads, 2) if total_leads > 0 else 0.0
            conversion_rate = round((qualified_leads / total_leads) * 100, 1) if total_leads > 0 else 0.0

            recent_events = session.execute(
                sa.select(CampaignAnalyticsEvent)
                .where(CampaignAnalyticsEvent.campaign_id.in_(campaign_ids_q))
                .order_by(sa.desc(CampaignAnalyticsEvent.created_at))
                .limit(10)
            ).scalars().all()

            activity_feed = [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "campaign_id": e.campaign_id,
                    "event_data": e.event_data,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in recent_events
            ]

            return Response({
                "kpis": {
                    "active_campaigns": active_campaigns,
                    "total_campaigns": total_campaigns,
                    "interactions": total_interactions,
                    "leads": total_leads,
                    "qualified_leads": qualified_leads,
                    "converted_leads": converted_leads,
                    "conversion_rate": conversion_rate,
                    "spend": total_spend,
                    "cost_per_lead": cost_per_lead,
                },
                "activity": activity_feed,
            })
        finally:
            session.close()
