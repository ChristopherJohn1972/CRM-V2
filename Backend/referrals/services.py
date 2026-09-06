import logging
import secrets
from datetime import datetime, timezone

import sqlalchemy as sa

from common import audit
from common.exceptions import ConflictError, NotFoundError, ValidationError_
from referrals.enums import (
    ALLOWED_REFERRAL_CODE_TRANSITIONS,
    ReferralCodeStatus,
    ReferralEventType,
    TERMINAL_REFERRAL_STATUSES,
)
from referrals.models import ReferralCode, ReferralEvent, ReferralQualification

logger = logging.getLogger(__name__)


class ReferralCodeService:
    @staticmethod
    def generate_code(customer_id: int) -> str:
        return f"REF-{customer_id}-{secrets.token_hex(4).upper()}"

    @staticmethod
    def create_code(db, customer_id: int, payload: dict, user_id: int, *, request=None) -> ReferralCode:
        code = (payload.get("code") or "").strip()
        if not code:
            code = ReferralCodeService.generate_code(customer_id)

        existing = db.execute(
            sa.select(ReferralCode).where(ReferralCode.code == code)
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Referral code '{code}' already exists.")

        rc = ReferralCode(
            code=code,
            referrer_customer_id=customer_id,
            campaign_id=payload.get("campaign_id"),
            status=ReferralCodeStatus.ACTIVE.value,
            max_referrals=payload.get("max_referrals"),
            expires_at=payload.get("expires_at"),
        )
        db.add(rc)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="REFERRAL_CODE_CREATED",
            resource_type="referral_code",
            resource_id=rc.id,
            description=f"Referral code '{code}' created for customer {customer_id}",
            request=request,
        )
        db.commit()
        return rc

    @staticmethod
    def validate_code(db, code: str) -> ReferralCode:
        rc = db.execute(
            sa.select(ReferralCode).where(ReferralCode.code == code)
        ).scalar_one_or_none()
        if rc is None:
            raise NotFoundError("Referral code not found.")
        if rc.status != ReferralCodeStatus.ACTIVE.value:
            raise ConflictError(f"Referral code is {rc.status}.")
        if rc.expires_at and rc.expires_at < datetime.now(timezone.utc):
            raise ConflictError("Referral code has expired.")
        if rc.max_referrals and rc.referral_count >= rc.max_referrals:
            raise ConflictError("Referral code has reached maximum uses.")
        return rc


class ReferralLifecycleService:
    @staticmethod
    def record_event(db, referral_code_id: int, referred_customer_id: int, event_type: str, *, metadata=None, request=None) -> ReferralEvent:
        re = ReferralEvent(
            referral_code_id=referral_code_id,
            referred_customer_id=referred_customer_id,
            event_type=event_type,
            metadata_=metadata,
        )
        db.add(re)

        rc = db.get(ReferralCode, referral_code_id)
        if rc and event_type == ReferralEventType.FIRST_PURCHASE.value:
            rc.referral_count += 1
            if rc.max_referrals and rc.referral_count >= rc.max_referrals:
                rc.status = ReferralCodeStatus.EXHAUSTED.value

        db.flush()
        return re


class ReferralQualificationService:
    @staticmethod
    def qualify_purchase(db, referral_event_id: int, order_id: int, amount: float, *, request=None) -> ReferralQualification:
        rq = ReferralQualification(
            referral_id=referral_event_id,
            order_id=order_id,
            amount=amount,
            qualified_at=datetime.now(timezone.utc),
            reward_issued=False,
            reward_amount=0,
        )
        db.add(rq)
        db.flush()
        return rq

    @staticmethod
    def issue_reward(db, qualification_id: int, reward_amount: float, *, request=None) -> ReferralQualification:
        rq = db.get(ReferralQualification, qualification_id)
        if rq is None:
            raise NotFoundError("Referral qualification not found.")
        if rq.reward_issued:
            raise ConflictError("Reward already issued.")

        rq.reward_issued = True
        rq.reward_amount = reward_amount
        db.flush()
        return rq


class ReferralAntiAbuseService:
    @staticmethod
    def check_self_referral(db, referrer_customer_id: int, referred_customer_id: int) -> bool:
        return referrer_customer_id == referred_customer_id

    @staticmethod
    def check_duplicate_referral(db, referral_code_id: int, referred_customer_id: int) -> bool:
        existing = db.execute(
            sa.select(ReferralEvent).where(
                ReferralEvent.referral_code_id == referral_code_id,
                ReferralEvent.referred_customer_id == referred_customer_id,
                ReferralEvent.event_type == ReferralEventType.REGISTRATION.value,
            )
        ).scalar_one_or_none()
        return existing is not None
