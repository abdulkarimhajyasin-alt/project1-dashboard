from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.mining import (
    build_mining_status,
    get_referral_rank_info,
    money,
    settle_due_mining_cycle,
    settle_due_mining_cycles,
    sync_active_cycle_with_user_capital,
)
from app.models import MiningCycle, PendingRequest, Record, User


# Keep plan withdrawal timing here so user and admin screens read the same
# cycle state without importing route modules from each other.
MIN_WITHDRAWAL = Decimal("10.00")
WITHDRAWAL_CYCLE_DAYS = {
    "silver": 20,
    "gold": 15,
    "vip": 10,
}


def get_active_capital(user: User) -> Decimal:
    return Decimal(user.capital or 0)


def get_available_yield(user: User) -> Decimal:
    return money(user.profits)


def get_plan_status(user: User) -> dict[str, str | bool]:
    plan = (user.plan or "none").lower()
    return {
        "plan": plan,
        "has_active_plan": bool(plan and plan != "none"),
    }


def get_withdrawal_cycle_days(plan: str | None) -> int:
    return WITHDRAWAL_CYCLE_DAYS.get((plan or "").lower(), 0)


def get_withdrawal_cycle_start(user: User, db: Session) -> datetime:
    last_approved_withdrawal = (
        db.query(Record)
        .filter(Record.user_id == user.id, Record.record_type == "profit_withdraw")
        .order_by(Record.created_at.desc())
        .first()
    )
    if last_approved_withdrawal:
        return last_approved_withdrawal.created_at

    last_approved_activation = (
        db.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.id,
            PendingRequest.request_type.in_(("plan_subscription", "deposit")),
            PendingRequest.status == "approved",
        )
        .order_by(PendingRequest.updated_at.desc(), PendingRequest.created_at.desc())
        .first()
    )
    if last_approved_activation:
        return last_approved_activation.updated_at or last_approved_activation.created_at

    return user.created_at or datetime.utcnow()


def build_withdrawal_cycle_status(user: User, db: Session, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    cycle_days = get_withdrawal_cycle_days(user.plan)
    cycle_start = get_withdrawal_cycle_start(user, db)
    cycle_end = cycle_start + timedelta(days=cycle_days) if cycle_days else cycle_start
    total_seconds = max(1, cycle_days * 24 * 60 * 60)
    elapsed_seconds = max(0, int((now - cycle_start).total_seconds()))
    remaining = max(0, int((cycle_end - now).total_seconds())) if cycle_days else 0
    progress = 100 if not cycle_days else min(100, int((elapsed_seconds / total_seconds) * 100))
    available_profits = Decimal(user.profits or 0)
    manual_unlock = bool(user.manual_withdrawal_unlock)
    has_pending_withdrawal = (
        db.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.id,
            PendingRequest.request_type == "withdraw",
            PendingRequest.status == "pending",
        )
        .first()
        is not None
    )

    return {
        "withdrawal_cycle_start": cycle_start,
        "withdrawal_cycle_end": cycle_end,
        "withdrawal_cycle_days": cycle_days,
        "withdrawal_progress_percent": progress,
        "withdrawal_remaining_seconds": remaining,
        "manual_withdrawal_unlock": manual_unlock,
        "has_pending_withdrawal": has_pending_withdrawal,
        "can_withdraw": bool(
            user.verified
            and cycle_days
            and (remaining == 0 or manual_unlock)
            and available_profits > 0
            and not has_pending_withdrawal
        ),
    }


def get_referral_earnings_total(user: User, db: Session) -> Decimal:
    return (
        db.query(func.coalesce(func.sum(Record.amount), 0))
        .filter(
            Record.user_id == user.id,
            Record.record_type == "referral_reward",
        )
        .scalar()
        or Decimal("0")
    )


def build_user_financial_state(user: User, db: Session) -> dict:
    # Mining formulas stay in app.mining. This wrapper only names and groups
    # display values so pages do not rebuild them slightly differently.
    mining_status = build_mining_status(user, db)
    withdrawal_cycle = build_withdrawal_cycle_status(user, db)
    referrals_count = len(user.referrals)
    rank_info = get_referral_rank_info(referrals_count)
    active_capital = get_active_capital(user)
    available_yield = get_available_yield(user)
    total_referral_earnings = get_referral_earnings_total(user, db)
    dashboard_earnings_total = mining_status.get("dashboard_earnings_total", available_yield)
    return {
        "active_capital": active_capital,
        "available_yield": available_yield,
        "live_available_yield": mining_status.get("live_available_yield", available_yield),
        "settled_user_profits": available_yield,
        "dashboard_earnings_total": dashboard_earnings_total,
        "live_total_earnings": mining_status.get("live_total_earnings", dashboard_earnings_total),
        "total_balance": active_capital + available_yield,
        "mining_status": mining_status,
        "withdrawal_cycle": withdrawal_cycle,
        "plan_status": get_plan_status(user),
        "referrals_count": referrals_count,
        "referral_rank_info": rank_info,
        "total_referral_earnings": total_referral_earnings,
    }


def refresh_user_financial_state(user: User, db: Session) -> dict:
    settle_due_mining_cycle(user, db)
    return build_user_financial_state(user, db)


def sync_user_active_capital(user: User, db: Session):
    return sync_active_cycle_with_user_capital(user, db)


def build_admin_financial_summary(db: Session, *, settle_due_cycles: bool = True) -> dict:
    if settle_due_cycles:
        settle_due_mining_cycles(db)
    now = datetime.utcnow()
    total_capital = db.query(func.coalesce(func.sum(User.capital), 0)).scalar() or Decimal("0")
    total_profits = db.query(func.coalesce(func.sum(User.profits), 0)).scalar() or Decimal("0")
    active_cycles = (
        db.query(MiningCycle)
        .filter(
            MiningCycle.status == "active",
            MiningCycle.completed_at.is_(None),
            func.coalesce(MiningCycle.cycle_window_end, MiningCycle.end_at) > now,
        )
        .count()
    )
    return {
        "total_capital": total_capital,
        "total_profits": total_profits,
        "total_balances": Decimal(total_capital or 0) + Decimal(total_profits or 0),
        "active_cycles": active_cycles,
    }
