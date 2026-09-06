from datetime import datetime, timezone

import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.access import get_customer_for_request
from common import audit
from common.db import SessionLocal
from common.events import DomainEvent, EventBus
from common.exceptions import NotFoundError, PermissionDeniedError
from communications.models import (
    CallLog,
    CommunicationProviderEvent,
    EmailMessage,
    SmsMessage,
)
from communications.serializers import (
    CallSerializer,
    CommunicationItemSerializer,
    EmailSendSerializer,
    EmailSerializer,
    SmsSendSerializer,
    SmsSerializer,
)
from communications.services import build_sms_gateway, normalize_status

PERMISSION_SMS_READ = "communications.sms.read"
PERMISSION_SMS_SEND = "communications.sms.send"
PERMISSION_EMAIL_READ = "communications.email.read"
PERMISSION_EMAIL_SEND = "communications.email.send"
PERMISSION_CALL_READ = "communications.call.read"
PERMISSION_CALL_LOG = "communications.call.log"


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CommunicationHistoryView(APIView):
    def get(self, request, customer_id):
        principal = request.user
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id)

            channel = request.query_params.get("channel")
            items = []

            if not channel or channel == "sms":
                if principal.has_permission(PERMISSION_SMS_READ):
                    for msg in db.execute(
                        sa.select(SmsMessage).where(SmsMessage.customer_id == customer_id)
                    ).scalars().all():
                        items.append(
                            {
                                "channel": "sms",
                                "id": msg.sms_message_id,
                                "occurred_at": msg.sent_at or msg.created_at,
                                "summary": f"SMS {msg.direction.lower()} to {msg.to_number}: {msg.body[:80]}",
                                "status": msg.status,
                                "reference": msg.provider_message_id,
                            }
                        )

            if not channel or channel == "email":
                if principal.has_permission(PERMISSION_EMAIL_READ):
                    for msg in db.execute(
                        sa.select(EmailMessage).where(EmailMessage.customer_id == customer_id)
                    ).scalars().all():
                        items.append(
                            {
                                "channel": "email",
                                "id": msg.email_message_id,
                                "occurred_at": msg.sent_at or msg.created_at,
                                "summary": f"Email {msg.direction.lower()} to {msg.to_address}: {msg.subject or ''}",
                                "status": msg.status,
                                "reference": msg.provider_message_id,
                            }
                        )

            if not channel or channel == "call":
                if principal.has_permission(PERMISSION_CALL_READ):
                    for call in db.execute(
                        sa.select(CallLog).where(CallLog.customer_id == customer_id)
                    ).scalars().all():
                        items.append(
                            {
                                "channel": "call",
                                "id": call.call_log_id,
                                "occurred_at": call.started_at or call.created_at,
                                "summary": f"Call {call.direction.lower()} to {call.phone_number} ({call.outcome or 'no outcome'})",
                                "status": None,
                                "reference": None,
                            }
                        )

            items.sort(key=lambda i: i["occurred_at"] or _utcnow(), reverse=True)

            try:
                page = int(request.query_params.get("page", 1))
            except (TypeError, ValueError):
                page = 1
            page = max(1, page)
            try:
                page_size = int(request.query_params.get("page_size", 20))
            except (TypeError, ValueError):
                page_size = 20
            start = (page - 1) * page_size
            page_items = items[start : start + page_size]

            return Response(
                {
                    "count": len(items),
                    "page": page,
                    "page_size": page_size,
                    "results": CommunicationItemSerializer(page_items, many=True).data,
                }
            )
        finally:
            db.close()


class SmsView(APIView):
    def post(self, request, customer_id):
        principal = request.user
        if not principal.has_permission(PERMISSION_SMS_SEND):
            raise PermissionDeniedError()
        serializer = SmsSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id)
            sms = SmsMessage(
                customer_id=customer_id,
                direction="OUTBOUND",
                to_number=serializer.validated_data["to_number"],
                body=serializer.validated_data["body"],
                from_number=serializer.validated_data.get("from_number"),
                status="QUEUED",
                attempts=1,
                last_attempt_at=_utcnow(),
                created_by=principal.user_id,
            )
            db.add(sms)
            db.flush()

            gateway = build_sms_gateway(settings)
            try:
                result = gateway.send(
                    to_number=sms.to_number,
                    body=sms.body,
                    from_number=sms.from_number,
                    reference=str(sms.sms_message_id),
                )
                sms.provider_message_id = result.get("provider_message_id")
                sms.provider_reference = result.get("provider_reference")
                sms.status = result.get("status", "SENT")
                if sms.status in ("SENT", "DELIVERED"):
                    sms.sent_at = _utcnow()
            except Exception as exc:
                sms.status = "FAILED"
                sms.failure_reason = str(exc)[:500]

            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="sms.sent",
                resource_type="sms_messages",
                resource_id=sms.sms_message_id,
                description=f"SMS sent to {sms.to_number}",
                request=request,
            )
            db.commit()
            db.refresh(sms)
            EventBus.publish(
                DomainEvent(
                    event_type="SmsSent",
                    customer_id=customer_id,
                    source_module="communications",
                    actor_user_id=principal.user_id,
                    actor_type="INTERNAL_USER",
                    summary=f"SMS sent to {sms.to_number}",
                    reference_type="sms_messages",
                    reference_id=sms.sms_message_id,
                    payload={"status": sms.status},
                )
            )
            return Response(SmsSerializer(sms).data, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class EmailView(APIView):
    def post(self, request, customer_id):
        principal = request.user
        if not principal.has_permission(PERMISSION_EMAIL_SEND):
            raise PermissionDeniedError()
        serializer = EmailSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id)
            email = EmailMessage(
                customer_id=customer_id,
                direction="OUTBOUND",
                to_address=serializer.validated_data["to_address"],
                from_address=serializer.validated_data.get("from_address"),
                cc_address=serializer.validated_data.get("cc_address"),
                bcc_address=serializer.validated_data.get("bcc_address"),
                subject=serializer.validated_data.get("subject", ""),
                body=serializer.validated_data.get("body", ""),
                status="SENT",
                sent_at=_utcnow(),
                created_by=principal.user_id,
            )
            db.add(email)
            db.commit()
            db.refresh(email)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="email.sent",
                resource_type="email_messages",
                resource_id=email.email_message_id,
                description=f"Email sent to {email.to_address}",
                request=request,
            )
            db.commit()
            return Response(EmailSerializer(email).data, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class CallView(APIView):
    def post(self, request, customer_id):
        principal = request.user
        if not principal.has_permission(PERMISSION_CALL_LOG):
            raise PermissionDeniedError()
        serializer = CallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        db = SessionLocal()
        try:
            get_customer_for_request(db, request, customer_id)
            call = CallLog(customer_id=customer_id, **serializer.validated_data)
            if call.staff_user_id is None:
                call.staff_user_id = principal.user_id
            db.add(call)
            db.commit()
            db.refresh(call)
            audit.record_audit(
                db,
                actor_user_id=principal.user_id,
                action="call.logged",
                resource_type="call_logs",
                resource_id=call.call_log_id,
                description=f"Call logged to {call.phone_number}",
                request=request,
            )
            db.commit()
            return Response(CallSerializer(call).data, status=status.HTTP_201_CREATED)
        finally:
            db.close()


class SmsWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        token = request.META.get("HTTP_X_WEBHOOK_TOKEN")
        if token != getattr(settings, "WEBHOOK_SECRET", ""):
            raise PermissionDeniedError("Invalid webhook token.")

        payload = request.data or {}
        message_id = payload.get("provider_message_id") or payload.get("message_id")
        db = SessionLocal()
        try:
            sms = db.execute(
                sa.select(SmsMessage).where(
                    (SmsMessage.provider_message_id == message_id)
                    | (SmsMessage.provider_reference == message_id)
                )
            ).scalar_one_or_none()
            if sms is None:
                db.add(
                    CommunicationProviderEvent(
                        provider="sms",
                        event_type=payload.get("event") or "status_callback",
                        provider_message_id=message_id,
                        status=normalize_status(payload.get("status")),
                        raw_event=payload,
                        received_at=_utcnow(),
                        processed=False,
                    )
                )
                db.commit()
                return Response(status=status.HTTP_202_ACCEPTED)

            sms.status = normalize_status(payload.get("status"))
            sms.failure_reason = payload.get("failure_reason")
            sms.attempts += 1
            if sms.status == "DELIVERED":
                sms.delivered_at = _utcnow()
            elif sms.status == "SENT":
                sms.sent_at = sms.sent_at or _utcnow()
            sms.last_attempt_at = _utcnow()

            db.add(
                CommunicationProviderEvent(
                    provider="sms",
                    event_type=payload.get("event") or "status_callback",
                    provider_message_id=message_id,
                    status=sms.status,
                    raw_event=payload,
                    received_at=_utcnow(),
                    processed=True,
                )
            )
            db.commit()
            if sms.customer_id:
                EventBus.publish(
                    DomainEvent(
                        event_type="SmsStatusChanged",
                        customer_id=sms.customer_id,
                        source_module="communications",
                        actor_user_id=None,
                        actor_type="SYSTEM",
                        summary=f"SMS {sms.status.lower()}",
                        reference_type="sms_messages",
                        reference_id=sms.sms_message_id,
                        payload={"status": sms.status},
                    )
                )
            return Response(status=status.HTTP_200_OK)
        finally:
            db.close()