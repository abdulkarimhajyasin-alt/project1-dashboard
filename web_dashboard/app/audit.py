from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


AUDIT_ACTION_LABELS = {
    "admin_capital_adjustment": "Admin capital adjustment",
    "admin_available_yield_adjustment": "Admin available-yield adjustment",
    "plan_subscription_approved": "Plan subscription approved",
    "plan_subscription_rejected": "Plan subscription rejected",
    "deposit_approved": "Deposit approved",
    "deposit_rejected": "Deposit rejected",
    "withdrawal_approved": "Withdrawal approved",
    "withdrawal_rejected": "Withdrawal rejected",
    "capital_withdrawal_approved": "Capital withdrawal approved",
    "capital_withdrawal_rejected": "Capital withdrawal rejected",
    "verification_approved": "Verification approved",
    "verification_rejected": "Verification rejected",
    "manual_withdrawal_unlocked": "Manual withdrawal unlocked",
    "manual_withdrawal_locked": "Manual withdrawal locked",
    "user_subscription_updated": "Subscription updated",
    "user_subscription_deleted": "Subscription removed",
    "user_deleted": "User deleted",
    "referral_reward_granted": "Referral reward granted",
    "mining_cycle_settled": "Mining cycle settled",
    "mining_cycle_cancelled_by_admin": "Mining cycle cancelled",
}

AUDIT_ACTION_TONES = {
    "admin_capital_adjustment": "warning",
    "admin_available_yield_adjustment": "warning",
    "plan_subscription_approved": "success",
    "plan_subscription_rejected": "danger",
    "deposit_approved": "success",
    "deposit_rejected": "danger",
    "withdrawal_approved": "success",
    "withdrawal_rejected": "danger",
    "capital_withdrawal_approved": "success",
    "capital_withdrawal_rejected": "danger",
    "verification_approved": "success",
    "verification_rejected": "danger",
    "manual_withdrawal_unlocked": "info",
    "manual_withdrawal_locked": "warning",
    "user_subscription_updated": "info",
    "user_subscription_deleted": "danger",
    "user_deleted": "danger",
    "referral_reward_granted": "success",
    "mining_cycle_settled": "success",
    "mining_cycle_cancelled_by_admin": "warning",
}


def audit_action_label(action_type: str | None) -> str:
    if not action_type:
        return "Audit event"
    return AUDIT_ACTION_LABELS.get(action_type, action_type.replace("_", " ").title())


def audit_action_tone(action_type: str | None) -> str:
    return AUDIT_ACTION_TONES.get(action_type or "", "neutral")


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return value


def decimal_or_none(value: Decimal | int | float | str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def create_audit_log(
    db: Session,
    *,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    target_user_id: int | None = None,
    action_type: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    amount_before: Decimal | int | float | str | None = None,
    amount_after: Decimal | int | float | str | None = None,
    amount_delta: Decimal | int | float | str | None = None,
    currency: str = "USD",
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    before = decimal_or_none(amount_before)
    after = decimal_or_none(amount_after)
    delta = decimal_or_none(amount_delta)
    if delta is None and before is not None and after is not None:
        delta = after - before

    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        target_user_id=target_user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        amount_before=before,
        amount_after=after,
        amount_delta=delta,
        currency=currency,
        reason=reason,
        metadata_json=json_safe(metadata) if metadata else None,
    )
    db.add(audit_log)
    return audit_log
