import logging
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger(__name__)


class AccountingDataUnavailable(Exception):
    def __init__(self, reason="accounting_unavailable"):
        super().__init__(reason)
        self.reason = reason


class AccountingGateway(ABC):
    @abstractmethod
    def fetch_summary(self, customer_id, account_number) -> dict:
        pass

    def fetch_transactions(self, customer_id, account_number, page=1, page_size=20) -> dict:
        raise NotImplementedError


class NullAccountingGateway(AccountingGateway):
    def fetch_summary(self, customer_id, account_number):
        raise AccountingDataUnavailable()

    def fetch_transactions(self, customer_id, account_number, page=1, page_size=20):
        raise AccountingDataUnavailable()


class HttpAccountingGateway(AccountingGateway):
    def __init__(self, base_url, api_token, timeout=3):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    def _headers(self):
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _get(self, path, params):
        try:
            response = requests.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
            if response.status_code == 404:
                raise AccountingDataUnavailable("accounting_not_found")
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            logger.warning("accounting gateway timed out for %s", path)
            raise AccountingDataUnavailable("accounting_timeout")
        except requests.RequestException as exc:
            logger.warning("accounting gateway request failed for %s: %s", path, exc)
            raise AccountingDataUnavailable("accounting_unreachable")

    def fetch_summary(self, customer_id, account_number):
        return self._get(
            f"/customers/{customer_id}/financial-summary",
            {"account_number": account_number},
        )

    def fetch_transactions(self, customer_id, account_number, page=1, page_size=20):
        return self._get(
            f"/customers/{customer_id}/transactions",
            {"account_number": account_number, "page": page, "page_size": page_size},
        )


def build_gateway(settings_module) -> AccountingGateway:
    if not getattr(settings_module, "ACCOUNTING_BASE_URL", ""):
        return NullAccountingGateway()
    return HttpAccountingGateway(
        settings_module.ACCOUNTING_BASE_URL,
        settings_module.ACCOUNTING_API_TOKEN,
        settings_module.ACCOUNTING_TIMEOUT_SECONDS,
    )