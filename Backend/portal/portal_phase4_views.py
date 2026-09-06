import logging
import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from campaigns.models import Campaign
from referrals.models import ReferralCode, ReferralEvent
from referrals.services import ReferralCodeService, ReferralLifecycleService, ReferralAntiAbuseService
from momentum.services import MomentumLedgerService
from momentum.models import MomentumLedger

logger = logging.getLogger(__name__)


def _get_portal_customer(request):
    from portal.portal_auth import get_portal_customer_from_request
    return get_portal_customer_from_request(request)


class PortalCampaignListView(APIView):
    def get(self, request):
        customer = _get_portal_customer(request)
        if customer is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        session = SessionLocal()
        try:
            now = sa.func.now()
            stmt = (
                sa.select(Campaign)
                .where(
                    Campaign.status == "ACTIVE",
                    sa.or_(Campaign.start_date == None, Campaign.start_date <= now),
                    sa.or_(Campaign.end_date == None, Campaign.end_date >= now),
                )
                .order_by(sa.desc(Campaign.campaign_id))
            )
            rows = session.execute(stmt).scalars().all()
            data = [
                {
                    "campaign_id": c.campaign_id,
                    "name": c.name,
                    "description": c.description,
                    "campaign_type": c.campaign_type,
                    "start_date": str(c.start_date) if c.start_date else None,
                    "end_date": str(c.end_date) if c.end_date else None,
                }
                for c in rows
            ]
            return Response({"results": data})
        finally:
            session.close()


class PortalCampaignDetailView(APIView):
    def get(self, request, campaign_id):
        customer = _get_portal_customer(request)
        if customer is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        session = SessionLocal()
        try:
            campaign = session.get(Campaign, campaign_id)
            if campaign is None or campaign.status != "ACTIVE":
                from common.exceptions import NotFoundError
                raise NotFoundError("Campaign not found.")
            return Response({
                "campaign_id": campaign.campaign_id,
                "name": campaign.name,
                "description": campaign.description,
                "campaign_type": campaign.campaign_type,
                "start_date": str(campaign.start_date) if campaign.start_date else None,
                "end_date": str(campaign.end_date) if campaign.end_date else None,
                "budget": float(campaign.budget) if campaign.budget else None,
            })
        finally:
            session.close()


class PortalLeadSelfRegisterView(APIView):
    def post(self, request):
        customer = _get_portal_customer(request)

        from leads.serializers import LeadWriteSerializer
        serializer = LeadWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)

        if customer:
            payload["source_channel"] = "PORTAL"

        session = SessionLocal()
        try:
            from leads.services import LeadService
            user_id = customer.customer_id if customer else 0
            lead = LeadService.create_lead(session, payload, user_id, request=request)
            return Response(
                {"lead_id": lead.lead_id, "status": lead.status},
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class PortalReferralCodeListView(APIView):
    def get(self, request):
        customer = _get_portal_customer(request)
        if customer is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        session = SessionLocal()
        try:
            stmt = (
                sa.select(ReferralCode)
                .where(ReferralCode.referrer_customer_id == customer.customer_id)
                .order_by(sa.desc(ReferralCode.id))
            )
            rows = session.execute(stmt).scalars().all()
            data = [
                {
                    "id": rc.id,
                    "code": rc.code,
                    "status": rc.status,
                    "referral_count": rc.referral_count,
                    "max_referrals": rc.max_referrals,
                    "expires_at": str(rc.expires_at) if rc.expires_at else None,
                    "created_at": str(rc.created_at),
                }
                for rc in rows
            ]
            return Response({"results": data})
        finally:
            session.close()

    def post(self, request):
        customer = _get_portal_customer(request)
        if customer is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        session = SessionLocal()
        try:
            rc = ReferralCodeService.create_code(
                session, customer.customer_id, {}, customer.customer_id, request=request
            )
            return Response(
                {"id": rc.id, "code": rc.code, "status": rc.status},
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class PortalReferralTrackingView(APIView):
    def get(self, request, code):
        session = SessionLocal()
        try:
            rc = ReferralCodeService.validate_code(session, code)
            ReferralLifecycleService.record_event(
                session, rc.id, 0, "CODE_CLICKED", request=request
            )
            session.commit()
            return Response({
                "code": rc.code,
                "status": rc.status,
            })
        finally:
            session.close()


class PortalMomentumBalanceView(APIView):
    def get(self, request):
        customer = _get_portal_customer(request)
        if customer is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        session = SessionLocal()
        try:
            balance = MomentumLedgerService.get_balance(session, customer.customer_id)
            return Response({
                "customer_id": customer.customer_id,
                "balance": balance,
            })
        finally:
            session.close()


class PortalMomentumHistoryView(APIView):
    def get(self, request):
        customer = _get_portal_customer(request)
        if customer is None:
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        session = SessionLocal()
        try:
            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
            offset = (page_number - 1) * page_size

            entries = MomentumLedgerService.get_ledger_entries(
                session, customer.customer_id, limit=page_size, offset=offset
            )
            data = [
                {
                    "id": e.id,
                    "entry_type": e.entry_type,
                    "points": e.points,
                    "balance_after": e.balance_after,
                    "source_type": e.source_type,
                    "description": e.description,
                    "created_at": str(e.created_at),
                }
                for e in entries
            ]

            total = session.execute(
                sa.select(sa.func.count()).where(MomentumLedger.customer_id == customer.customer_id)
            ).scalar()

            return Response({
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": data,
            })
        finally:
            session.close()
