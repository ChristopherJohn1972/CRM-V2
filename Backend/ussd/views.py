import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.db import SessionLocal
from ussd.enums import USSD_MAIN_MENU, UssdSessionStatus
from ussd.services import UssdSessionService, UssdGatewayService

logger = logging.getLogger(__name__)


class UssdGatewayView(APIView):
    """
    USSD Gateway endpoint for *900#
    Handles incoming USSD requests from gateway provider.
    Expected params: sessionId, phoneNumber, text
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        session_id = request.data.get("sessionId") or request.data.get("session_id")
        phone_number = request.data.get("phoneNumber") or request.data.get("phone_number")
        text = request.data.get("text", "")

        if not session_id or not phone_number:
            return Response(
                {"error": "sessionId and phoneNumber are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = SessionLocal()
        try:
            ussd_session = UssdSessionService.get_or_create_session(
                session, phone_number, session_id, text
            )

            if ussd_session is None:
                return Response({
                    "sessionId": session_id,
                    "text": "Session expired. Please dial *900# again.",
                    "action": "end",
                })

            user_input = text.split("*")[-1] if text else ""
            response_text = UssdSessionService.advance_session(
                session, ussd_session, user_input
            )

            ussd_session.expires_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc) + __import__("datetime").timedelta(minutes=5)
            session.commit()

            UssdSessionService.log_transaction(
                session,
                session_id=session_id,
                phone_number=phone_number,
                customer_id=ussd_session.customer_id,
                flow_type=ussd_session.current_menu,
                input_text=user_input,
                response_text=response_text,
            )

            is_end = ussd_session.status == UssdSessionStatus.COMPLETED.value
            return Response({
                "sessionId": session_id,
                "text": response_text,
                "action": "end" if is_end else "continue",
            })
        except Exception as exc:
            logger.exception("USSD error")
            session.rollback()
            return Response({
                "sessionId": session_id,
                "text": "An error occurred. Please try again.",
                "action": "end",
            })
        finally:
            session.close()

    def get(self, request):
        """Health check for USSD gateway"""
        return Response({
            "status": "ok",
            "short_code": "*900#",
            "service": "CRM USSD Gateway",
        })


class UssdSessionListView(APIView):
    def get(self, request):
        from iam.permissions import UserPrincipal
        principal = getattr(request, "user", None)
        if principal is None or not principal.has_permission("ussd.session.view"):
            from common.exceptions import PermissionDeniedError
            raise PermissionDeniedError()

        session = SessionLocal()
        try:
            from ussd.models import UssdSession
            import sqlalchemy as sa
            from django.conf import settings
            from rest_framework.pagination import PageNumberPagination

            stmt = sa.select(UssdSession).order_by(sa.desc(UssdSession.created_at))

            status_filter = request.query_params.get("status")
            if status_filter:
                stmt = stmt.where(UssdSession.status == status_filter)

            phone = request.query_params.get("phone")
            if phone:
                stmt = stmt.where(UssdSession.phone_number == phone)

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
            offset = (page_number - 1) * page_size

            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            rows = session.execute(stmt.limit(page_size).offset(offset)).scalars().all()
            data = [
                {
                    "id": s.id,
                    "session_id": s.session_id,
                    "phone_number": s.phone_number,
                    "customer_id": s.customer_id,
                    "current_menu": s.current_menu,
                    "status": s.status,
                    "created_at": str(s.created_at),
                }
                for s in rows
            ]

            return Response({
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": data,
            })
        finally:
            session.close()
