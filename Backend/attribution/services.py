import logging
from datetime import datetime, timezone

import sqlalchemy as sa

from common import audit
from common.exceptions import NotFoundError, ValidationError_
from attribution.enums import AttributionModelType
from attribution.models import AttributionEvent, AttributionModel, AttributionResult

logger = logging.getLogger(__name__)


class AttributionTrackingService:
    @staticmethod
    def record_touchpoint(db, payload: dict, user_id: int = None, *, request=None) -> AttributionEvent:
        ae = AttributionEvent(
            customer_id=payload["customer_id"],
            campaign_id=payload["campaign_id"],
            source_id=payload.get("source_id"),
            event_type=payload["event_type"],
            touch_point_at=payload.get("touch_point_at", datetime.now(timezone.utc)),
            metadata_=payload.get("metadata"),
            session_id=payload.get("session_id"),
        )
        db.add(ae)
        db.flush()

        if user_id:
            audit.record_audit(
                db,
                actor_user_id=user_id,
                action="ATTRIBUTION_TOUCHPOINT_RECORDED",
                resource_type="attribution_event",
                resource_id=ae.id,
                description=f"Touchpoint '{ae.event_type}' recorded for customer {ae.customer_id}",
                request=request,
            )
        db.commit()
        return ae


class AttributionComputationService:
    @staticmethod
    def compute_for_order(db, order_id: int, customer_id: int, order_amount: float, *, request=None):
        model = db.execute(
            sa.select(AttributionModel).where(
                AttributionModel.is_default == True,
                AttributionModel.is_active == True,
            )
        ).scalar_one_or_none()
        if model is None:
            model = db.execute(
                sa.select(AttributionModel).where(AttributionModel.code == "LAST_TOUCH")
            ).scalar_one_or_none()
        if model is None:
            return []

        touchpoints = db.execute(
            sa.select(AttributionEvent)
            .where(
                AttributionEvent.customer_id == customer_id,
                AttributionEvent.touch_point_at <= datetime.now(timezone.utc),
            )
            .order_by(AttributionEvent.touch_point_at)
        ).scalars().all()

        if not touchpoints:
            return []

        if model.code == "LAST_TOUCH":
            return AttributionComputationService._last_touch(
                db, order_id, customer_id, order_amount, touchpoints
            )
        elif model.code == "FIRST_TOUCH":
            return AttributionComputationService._first_touch(
                db, order_id, customer_id, order_amount, touchpoints
            )
        elif model.code == "LINEAR":
            return AttributionComputationService._linear(
                db, order_id, customer_id, order_amount, touchpoints
            )
        return []

    @staticmethod
    def _last_touch(db, order_id, customer_id, order_amount, touchpoints):
        last = touchpoints[-1]
        result = AttributionResult(
            order_id=order_id,
            customer_id=customer_id,
            campaign_id=last.campaign_id,
            model_type=AttributionModelType.LAST_TOUCH.value,
            attributed_revenue=order_amount,
            attributed_weight=1.0,
        )
        db.add(result)
        db.flush()
        return [result]

    @staticmethod
    def _first_touch(db, order_id, customer_id, order_amount, touchpoints):
        first = touchpoints[0]
        result = AttributionResult(
            order_id=order_id,
            customer_id=customer_id,
            campaign_id=first.campaign_id,
            model_type=AttributionModelType.FIRST_TOUCH.value,
            attributed_revenue=order_amount,
            attributed_weight=1.0,
        )
        db.add(result)
        db.flush()
        return [result]

    @staticmethod
    def _linear(db, order_id, customer_id, order_amount, touchpoints):
        unique_campaigns = {}
        for tp in touchpoints:
            unique_campaigns[tp.campaign_id] = tp

        count = len(unique_campaigns)
        if count == 0:
            return []

        weight = 1.0 / count
        per_campaign = order_amount / count
        results = []
        for campaign_id, tp in unique_campaigns.items():
            result = AttributionResult(
                order_id=order_id,
                customer_id=customer_id,
                campaign_id=campaign_id,
                model_type=AttributionModelType.LINEAR.value,
                attributed_revenue=per_campaign,
                attributed_weight=weight,
            )
            db.add(result)
            results.append(result)
        db.flush()
        return results


class AttributionAnalyticsService:
    @staticmethod
    def revenue_by_campaign(db, start_date=None, end_date=None):
        stmt = (
            sa.select(
                AttributionResult.campaign_id,
                sa.func.sum(AttributionResult.attributed_revenue).label("total_revenue"),
                sa.func.count(AttributionResult.order_id).label("order_count"),
            )
            .group_by(AttributionResult.campaign_id)
        )
        if start_date:
            stmt = stmt.where(AttributionResult.computed_at >= start_date)
        if end_date:
            stmt = stmt.where(AttributionResult.computed_at <= end_date)
        return db.execute(stmt).all()
