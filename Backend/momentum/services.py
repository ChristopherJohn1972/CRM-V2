import logging
from datetime import datetime, timezone

import sqlalchemy as sa

from common import audit
from common.exceptions import ConflictError, NotFoundError
from momentum.enums import MomentumEntryType, MomentumTriggerType
from momentum.models import MomentumLedger, MomentumRule, MomentumRuleVersion

logger = logging.getLogger(__name__)


class MomentumRuleService:
    @staticmethod
    def create_rule(db, payload: dict, user_id: int, *, request=None) -> MomentumRule:
        rule = MomentumRule(
            name=payload["name"],
            code=payload["code"],
            trigger_type=payload["trigger_type"],
            config=payload["config"],
            is_active=payload.get("is_active", True),
            valid_from=payload["valid_from"],
            valid_until=payload.get("valid_until"),
        )
        db.add(rule)
        db.flush()

        version = MomentumRuleVersion(
            rule_id=rule.id,
            version=1,
            config=payload["config"],
            created_by=user_id,
        )
        db.add(version)
        db.flush()

        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="MOMENTUM_RULE_CREATED",
            resource_type="momentum_rule",
            resource_id=rule.id,
            description=f"Momentum rule '{rule.name}' created",
            request=request,
        )
        db.commit()
        return rule

    @staticmethod
    def update_rule(db, rule_id: int, payload: dict, user_id: int, *, request=None) -> MomentumRule:
        rule = db.get(MomentumRule, rule_id)
        if rule is None:
            raise NotFoundError("Momentum rule not found.")

        if "name" in payload:
            rule.name = payload["name"]
        if "config" in payload:
            rule.config = payload["config"]
            latest_version = db.execute(
                sa.select(sa.func.max(MomentumRuleVersion.version))
                .where(MomentumRuleVersion.rule_id == rule_id)
            ).scalar() or 0
            version = MomentumRuleVersion(
                rule_id=rule_id,
                version=latest_version + 1,
                config=payload["config"],
                created_by=user_id,
            )
            db.add(version)
        if "is_active" in payload:
            rule.is_active = payload["is_active"]
        if "valid_until" in payload:
            rule.valid_until = payload["valid_until"]

        db.flush()
        audit.record_audit(
            db,
            actor_user_id=user_id,
            action="MOMENTUM_RULE_UPDATED",
            resource_type="momentum_rule",
            resource_id=rule.id,
            description=f"Momentum rule '{rule.name}' updated",
            request=request,
        )
        db.commit()
        return rule

    @staticmethod
    def get_active_rules(db):
        now = datetime.now(timezone.utc)
        return db.execute(
            sa.select(MomentumRule).where(
                MomentumRule.is_active == True,
                MomentumRule.valid_from <= now,
                sa.or_(MomentumRule.valid_until == None, MomentumRule.valid_until > now),
            )
        ).scalars().all()


class MomentumLedgerService:
    @staticmethod
    def record_entry(
        db,
        *,
        customer_id: int,
        entry_type: str,
        points: int,
        source_type: str,
        source_id: str = None,
        rule_id: int = None,
        description: str = None,
        user_id: int = None,
        request=None,
    ) -> MomentumLedger:
        current_balance = MomentumLedgerService.get_balance(db, customer_id)

        if entry_type == MomentumEntryType.EARN.value:
            new_balance = current_balance + points
        elif entry_type in {MomentumEntryType.REDEEM.value, MomentumEntryType.FORFEIT.value}:
            if points > current_balance:
                raise ConflictError(f"Insufficient balance. Current: {current_balance}, Requested: {points}")
            new_balance = current_balance - points
        elif entry_type == MomentumEntryType.EXPIRE.value:
            new_balance = current_balance - points if points <= current_balance else 0
        elif entry_type == MomentumEntryType.ADJUST.value:
            new_balance = current_balance + points
        else:
            raise ConflictError(f"Unknown entry type: {entry_type}")

        entry = MomentumLedger(
            customer_id=customer_id,
            entry_type=entry_type,
            points=points,
            balance_after=new_balance,
            source_type=source_type,
            source_id=str(source_id) if source_id else None,
            rule_id=rule_id,
            description=description,
            created_by=user_id,
        )
        db.add(entry)
        db.flush()

        if user_id:
            audit.record_audit(
                db,
                actor_user_id=user_id,
                action=f"MOMENTUM_{entry_type}",
                resource_type="momentum_ledger",
                resource_id=entry.id,
                description=f"Momentum {entry_type}: {points} points for customer {customer_id}",
                request=request,
            )
        db.commit()
        return entry

    @staticmethod
    def get_balance(db, customer_id: int) -> int:
        latest = db.execute(
            sa.select(MomentumLedger.balance_after)
            .where(MomentumLedger.customer_id == customer_id)
            .order_by(sa.desc(MomentumLedger.id))
            .limit(1)
        ).scalar_one_or_none()
        return latest if latest else 0

    @staticmethod
    def get_ledger_entries(db, customer_id: int, limit: int = 50, offset: int = 0):
        stmt = (
            sa.select(MomentumLedger)
            .where(MomentumLedger.customer_id == customer_id)
            .order_by(sa.desc(MomentumLedger.created_at))
            .limit(limit)
            .offset(offset)
        )
        return db.execute(stmt).scalars().all()

    @staticmethod
    def earn_for_purchase(db, customer_id: int, order_id: int, order_amount: float, *, request=None):
        rules = MomentumRuleService.get_active_rules(db)
        purchase_rules = [r for r in rules if r.trigger_type == MomentumTriggerType.PURCHASE.value]

        if not purchase_rules:
            default_points = int(order_amount // 100)
            if default_points > 0:
                return MomentumLedgerService.record_entry(
                    db,
                    customer_id=customer_id,
                    entry_type=MomentumEntryType.EARN.value,
                    points=default_points,
                    source_type="PURCHASE",
                    source_id=order_id,
                    description=f"Earned {default_points} points for order {order_id}",
                    request=request,
                )
            return None

        rule = purchase_rules[0]
        config = rule.config or {}
        points_per_kes = config.get("points_per_kes", 0.01)
        min_purchase = config.get("min_purchase", 0)
        tier_multipliers = config.get("tier_multipliers", [])

        if order_amount < min_purchase:
            return None

        base_points = int(order_amount * points_per_kes)
        multiplier = 1.0
        for tier in sorted(tier_multipliers, key=lambda t: t.get("min_amount", 0), reverse=True):
            if order_amount >= tier.get("min_amount", 0):
                multiplier = tier.get("multiplier", 1.0)
                break

        final_points = int(base_points * multiplier)
        if final_points <= 0:
            return None

        return MomentumLedgerService.record_entry(
            db,
            customer_id=customer_id,
            entry_type=MomentumEntryType.EARN.value,
            points=final_points,
            source_type="PURCHASE",
            source_id=order_id,
            rule_id=rule.id,
            description=f"Earned {final_points} points for order {order_id} (rule: {rule.name})",
            request=request,
        )
