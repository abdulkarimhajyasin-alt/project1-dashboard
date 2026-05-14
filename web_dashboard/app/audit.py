from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


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
