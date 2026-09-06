import logging
from abc import ABC, abstractmethod

import requests

from common.exceptions import APIError

logger = logging.getLogger(__name__)

PROVIDER_STATUS_TO_APP = {
    "queued": "QUEUED",
    "sent": "SENT",
    "submitted": "SENT",
    "accepted": "SENT",
    "delivered": "DELIVERED",
    "received": "DELIVERED",
    "failed": "FAILED",
    "undelivered": "FAILED",
    "rejected": "REJECTED",
    "error": "FAILED",
}


def normalize_status(provider_status):
    if not provider_status:
        return "UNKNOWN"
    return PROVIDER_STATUS_TO_APP.get(str(provider_status).lower(), "UNKNOWN")


class SmsGateway(ABC):
    @abstractmethod
    def send(self, *, to_number, body, from_number=None, reference=None) -> dict:
        pass


class LoggingSmsGateway(SmsGateway):
    def send(self, *, to_number, body, from_number=None, reference=None):
        logger.info(
            "SMS (dev gateway) to=%s from=%s reference=%s body=%s",
            to_number,
            from_number,
            reference,
            body,
        )
        return {"provider_message_id": None, "status": "SENT"}


class HttpSmsGateway(SmsGateway):
    def __init__(self, base_url, api_token, timeout=10):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def send(self, *, to_number, body, from_number=None, reference=None):
        try:
            response = requests.post(
                f"{self.base_url}/sms/send",
                json={
                    "to": to_number,
                    "from": from_number,
                    "message": body,
                    "reference": reference,
                },
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "provider_message_id": data.get("message_id") or data.get("id"),
                "provider_reference": data.get("reference"),
                "status": normalize_status(data.get("status", "sent")),
            }
        except requests.RequestException as exc:
            logger.warning("SMS provider request failed: %s", exc)
            raise APIError("SMS provider request failed.", status_code=502, error_code="provider_error")


def build_sms_gateway(settings):
    base_url = getattr(settings, "SMS_PROVIDER_URL", "")
    api_token = getattr(settings, "SMS_PROVIDER_TOKEN", "")
    if base_url:
        return HttpSmsGateway(base_url, api_token)
    return LoggingSmsGateway()
