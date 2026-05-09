from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import MiningCycle, Record, User
from app.utils import format_datetime_for_timezone


MINING_CYCLE_DURATION = timedelta(hours=24)
BASE_MINING_INCOME = Decimal("0.05")
CAPITAL_DAILY_RATE = Decimal("0.02")
REFERRAL_REWARD_RATE = Decimal("0.50")
MONEY_QUANT = Decimal("0.0001")
CAPITAL_QUANT = Decimal("0.01")

REFERRAL_RANKS = [
    (0, 10, "Beginner"),
    (11, 20, "Bronze Promoter"),
    (21, 30, "Silver Promoter"),
    (31, 40, "Gold Promoter"),
    (41, 50, "Platinum Promoter"),
    (51, 60, "Diamond Promoter"),
    (61, 70, "Elite Promoter"),
    (71, 80, "Master Promoter"),
    (81, 90, "Ambassador"),
    (91, 100, "Legend Ambassador"),
]
GLOBAL_PARTNER = "Global Partner"


def utc_now() -> datetime:
    return datetime.utcnow()


def as_decimal(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def money(value: Decimal | int | float | str | None) -> Decimal:
    return as_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def capital_money(value: Decimal | int | float | str | None) -> Decimal:
    return as_decimal(value).quantize(CAPITAL_QUANT, rounding=ROUND_HALF_UP)


def calculate_cycle_income(active_capital: Decimal, referral_income: Decimal = Decimal("0")) -> dict[str, Decimal]:
    mining_income = money(BASE_MINING_INCOME)
    referral_income = money(referral_income)
    active_capital = capital_money(active_capital)
    current_free_income = money(mining_income + referral_income)
    target_income = money(active_capital * CAPITAL_DAILY_RATE)
    capital_bonus = money(max(Decimal("0"), target_income - current_free_income))
    final_income = money(current_free_income + capital_bonus)
    return {
        "mining_income": mining_income,
        "referral_income": referral_income,
        "current_free_income": current_free_income,
        "target_income": target_income,
        "capital_bonus": capital_bonus,
        "final_income": final_income,
        "active_capital": active_capital,
    }


def get_referral_rank_info(referrals_count: int) -> dict[str, int | str | None]:
    if referrals_count > 100:
        return {
            "rank": GLOBAL_PARTNER,
            "referrals_count": referrals_count,
            "next_rank": None,
            "remaining": 0,
        }

    for index, (start, end, rank) in enumerate(REFERRAL_RANKS):
        if start <= referrals_count <= end:
            next_rank = REFERRAL_RANKS[index + 1][2] if index + 1 < len(REFERRAL_RANKS) else GLOBAL_PARTNER
            next_threshold = REFERRAL_RANKS[index + 1][0] if index + 1 < len(REFERRAL_RANKS) else 101
            return {
                "rank": rank,
                "referrals_count": referrals_count,
                "next_rank": next_rank,
                "remaining": max(0, next_threshold - referrals_count),
            }

    return {
        "rank": "Beginner",
        "referrals_count": referrals_count,
        "next_rank": "Bronze Promoter",
        "remaining": max(0, 11 - referrals_count),
    }


def get_active_mining_cycle(db: Session, user_id: int) -> MiningCycle | None:
    return (
        db.query(MiningCycle)
        .filter(MiningCycle.user_id == user_id, MiningCycle.status == "active")
        .order_by(MiningCycle.start_at.desc())
        .first()
    )


def get_earning_referrer_cycle(db: Session, user_id: int, at_time: datetime) -> MiningCycle | None:
    return (
        db.query(MiningCycle)
        .filter(
            MiningCycle.user_id == user_id,
            MiningCycle.status == "active",
            MiningCycle.start_at <= at_time,
            MiningCycle.end_at >= at_time,
        )
        .order_by(MiningCycle.start_at.desc())
        .first()
    )


def progress_percent(cycle: MiningCycle | None, now: datetime | None = None) -> int:
    if not cycle:
        return 0
    now = now or utc_now()
    total_seconds = max(1, (cycle.end_at - cycle.start_at).total_seconds())
    elapsed_seconds = min(max(0, (now - cycle.start_at).total_seconds()), total_seconds)
    return int((elapsed_seconds / total_seconds) * 100)


def remaining_seconds(cycle: MiningCycle | None, now: datetime | None = None) -> int:
    if not cycle:
        return 0
    now = now or utc_now()
    return max(0, int((cycle.end_at - now).total_seconds()))


def grant_referral_reward(db: Session, completed_cycle: MiningCycle, completed_user: User, final_income: Decimal, now: datetime) -> None:
    if completed_cycle.referral_reward_paid:
        return

    if not completed_user.referrer:
        completed_cycle.referral_reward_paid = True
        completed_cycle.referrer_reward_amount = Decimal("0")
        return

    referrer_cycle = get_earning_referrer_cycle(db, completed_user.referrer.id, now)
    if not referrer_cycle:
        completed_cycle.referral_reward_paid = True
        completed_cycle.referrer_reward_amount = Decimal("0")
        return

    reward = money(final_income * REFERRAL_REWARD_RATE)
    referrer_cycle.referral_income = money(as_decimal(referrer_cycle.referral_income) + reward)
    completed_cycle.referral_reward_paid = True
    completed_cycle.referrer_reward_amount = reward
    completed_cycle.referrer_cycle_id = referrer_cycle.id


def add_cycle_records(db: Session, cycle: MiningCycle, user: User) -> None:
    notes = f"Mining cycle: {cycle.cycle_uuid}"
    if as_decimal(cycle.mining_income) > 0:
        db.add(
            Record(
                user_id=user.id,
                title="Daily mining income",
                amount=cycle.mining_income,
                record_type="mining_income",
                notes=notes,
            )
        )
    if as_decimal(cycle.referral_income) > 0:
        db.add(
            Record(
                user_id=user.id,
                title="Referral mining rewards",
                amount=cycle.referral_income,
                record_type="referral_reward",
                notes=notes,
            )
        )
    if as_decimal(cycle.capital_bonus) > 0:
        db.add(
            Record(
                user_id=user.id,
                title="Capital income bonus",
                amount=cycle.capital_bonus,
                record_type="capital_bonus",
                notes=notes,
            )
        )


def complete_mining_cycle(db: Session, user: User, cycle: MiningCycle, now: datetime | None = None) -> MiningCycle | None:
    now = now or utc_now()
    if cycle.status != "active" or cycle.completed_at is not None or cycle.end_at > now:
        return None

    income = calculate_cycle_income(cycle.active_capital, cycle.referral_income)
    cycle.mining_income = income["mining_income"]
    cycle.referral_income = income["referral_income"]
    cycle.capital_bonus = income["capital_bonus"]
    cycle.final_income = income["final_income"]
    cycle.status = "completed"
    cycle.completed_at = now
    user.profits = money(as_decimal(user.profits) + income["final_income"])
    user.daily_earnings = income["final_income"]
    user.last_start_at = None

    add_cycle_records(db, cycle, user)
    grant_referral_reward(db, cycle, user, income["final_income"], now)
    return cycle


def settle_due_mining_cycle(user: User, db: Session, now: datetime | None = None) -> MiningCycle | None:
    now = now or utc_now()
    cycle = get_active_mining_cycle(db, user.id)
    completed_cycle = complete_mining_cycle(db, user, cycle, now) if cycle else None
    if completed_cycle:
        db.commit()
        db.refresh(user)
        db.refresh(completed_cycle)
    return completed_cycle


def start_mining_cycle(user: User, db: Session, now: datetime | None = None) -> tuple[MiningCycle | None, str | None]:
    now = now or utc_now()
    settle_due_mining_cycle(user, db, now)
    active_cycle = get_active_mining_cycle(db, user.id)
    if active_cycle and active_cycle.end_at > now:
        return None, "You already have an active mining cycle."

    cycle = MiningCycle(
        cycle_uuid=uuid4().hex,
        user_id=user.id,
        start_at=now,
        end_at=now + MINING_CYCLE_DURATION,
        status="active",
        active_capital=capital_money(user.capital),
        mining_income=BASE_MINING_INCOME,
    )
    user.last_start_at = now
    db.add(cycle)
    db.add(user)
    db.commit()
    db.refresh(cycle)
    db.refresh(user)
    return cycle, None


def cycle_to_iso(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def build_mining_status(user: User, db: Session, now: datetime | None = None) -> dict:
    now = now or utc_now()
    cycle = get_active_mining_cycle(db, user.id)
    income = calculate_cycle_income(cycle.active_capital if cycle else user.capital, cycle.referral_income if cycle else Decimal("0"))
    user_timezone = user.timezone or "UTC"
    return {
        "cycle": cycle,
        "cycle_id": cycle.cycle_uuid if cycle else "",
        "status": "active" if cycle else "ready",
        "can_start": cycle is None,
        "progress_percent": progress_percent(cycle, now),
        "remaining_seconds": remaining_seconds(cycle, now),
        "start_time": format_datetime_for_timezone(cycle.start_at if cycle else None, user_timezone),
        "end_time": format_datetime_for_timezone(cycle.end_at if cycle else None, user_timezone),
        "start_time_iso": cycle_to_iso(cycle.start_at if cycle else None),
        "end_time_iso": cycle_to_iso(cycle.end_at if cycle else None),
        "active_capital": income["active_capital"],
        "mining_income": income["mining_income"],
        "referral_income": income["referral_income"],
        "capital_bonus": income["capital_bonus"],
        "current_daily_income": income["final_income"],
        "target_income": income["target_income"],
        "timezone": user_timezone,
    }
