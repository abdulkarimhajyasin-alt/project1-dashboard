from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import MiningCycle, Record, User
from app.utils import format_datetime_for_timezone


MINING_CYCLE_DURATION = timedelta(hours=24)
MINING_CYCLE_SECONDS = int(MINING_CYCLE_DURATION.total_seconds())
OFFICIAL_CYCLE_START_HOUR = 18
BASE_MINING_INCOME = Decimal("0.05")
CAPITAL_DAILY_RATE = Decimal("0.02")
REFERRAL_REWARD_RATE = Decimal("0.50")
MONEY_QUANT = Decimal("0.00000001")
CAPITAL_QUANT = Decimal("0.01")
RATIO_QUANT = Decimal("0.000001")

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


def ratio_decimal(value: Decimal | int | float | str | None) -> Decimal:
    return as_decimal(value).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)


def normalize_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=None)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_user_timezone(timezone_name: str | None) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError:
        return timezone.utc


def get_official_cycle_window(timezone_name: str | None, now: datetime | None = None) -> tuple[datetime, datetime]:
    now_utc = normalize_utc(now or utc_now()).replace(tzinfo=timezone.utc)
    user_timezone = get_user_timezone(timezone_name)
    local_now = now_utc.astimezone(user_timezone)
    today_start = datetime.combine(
        local_now.date(),
        time(hour=OFFICIAL_CYCLE_START_HOUR),
        tzinfo=user_timezone,
    )
    window_start_local = today_start if local_now >= today_start else today_start - MINING_CYCLE_DURATION
    window_end_local = window_start_local + MINING_CYCLE_DURATION
    return (
        window_start_local.astimezone(timezone.utc).replace(tzinfo=None),
        window_end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def get_cycle_timing(timezone_name: str | None, now: datetime | None = None) -> dict[str, datetime | int | Decimal]:
    actual_start = normalize_utc(now or utc_now())
    window_start, window_end = get_official_cycle_window(timezone_name, actual_start)
    missed_seconds = min(
        MINING_CYCLE_SECONDS,
        max(0, int((actual_start - window_start).total_seconds())),
    )
    active_seconds = min(
        MINING_CYCLE_SECONDS,
        max(0, int((window_end - actual_start).total_seconds())),
    )
    return {
        "cycle_window_start": window_start,
        "cycle_window_end": window_end,
        "actual_start_time": actual_start,
        "missed_seconds": missed_seconds,
        "active_seconds": active_seconds,
        "earning_ratio": ratio_decimal(Decimal(active_seconds) / Decimal(MINING_CYCLE_SECONDS)),
    }


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


def apply_income_to_cycle(cycle: MiningCycle, active_capital: Decimal | None = None) -> dict[str, Decimal]:
    if active_capital is not None:
        cycle.active_capital = capital_money(active_capital)
    income = calculate_cycle_income(cycle.active_capital, cycle.referral_income)
    earned_income = money(income["final_income"] * cycle_earning_ratio(cycle))
    cycle.active_capital = income["active_capital"]
    cycle.mining_income = income["mining_income"]
    cycle.referral_income = income["referral_income"]
    cycle.capital_bonus = income["capital_bonus"]
    cycle.full_daily_income = income["final_income"]
    cycle.final_income = earned_income
    cycle.final_income_after_time_deduction = earned_income
    return income


def sync_active_cycle_with_user_capital(user: User, db: Session) -> MiningCycle | None:
    cycle = get_active_mining_cycle(db, user.id)
    if not cycle:
        return None

    user_capital = capital_money(user.capital)
    if capital_money(cycle.active_capital) != user_capital:
        apply_income_to_cycle(cycle, user_capital)
        db.add(cycle)
    return cycle


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
        .filter(
            MiningCycle.user_id == user_id,
            MiningCycle.status == "active",
            MiningCycle.completed_at.is_(None),
        )
        .order_by(MiningCycle.start_at.desc())
        .first()
    )


def get_cycle_for_window(db: Session, user_id: int, window_start: datetime, window_end: datetime) -> MiningCycle | None:
    return (
        db.query(MiningCycle)
        .filter(
            MiningCycle.user_id == user_id,
            or_(MiningCycle.cycle_window_start == window_start, MiningCycle.start_at == window_start),
            or_(MiningCycle.cycle_window_end == window_end, MiningCycle.end_at == window_end),
        )
        .order_by(MiningCycle.created_at.desc())
        .first()
    )


def cycle_window_start(cycle: MiningCycle | None) -> datetime | None:
    if not cycle:
        return None
    return cycle.cycle_window_start or cycle.start_at


def cycle_window_end(cycle: MiningCycle | None) -> datetime | None:
    if not cycle:
        return None
    return cycle.cycle_window_end or cycle.end_at


def cycle_actual_start(cycle: MiningCycle | None) -> datetime | None:
    if not cycle:
        return None
    return cycle.actual_start_time or cycle.start_at


def cycle_earning_ratio(cycle: MiningCycle | None) -> Decimal:
    if not cycle:
        return Decimal("0")
    stored_ratio = as_decimal(cycle.earning_ratio)
    if stored_ratio > 0:
        return ratio_decimal(stored_ratio)
    active_seconds = as_decimal(cycle.active_seconds or MINING_CYCLE_SECONDS)
    return ratio_decimal(active_seconds / Decimal(MINING_CYCLE_SECONDS))


def base_referral_source_income(cycle: MiningCycle) -> Decimal:
    active_seconds = as_decimal(cycle.active_seconds or MINING_CYCLE_SECONDS)
    earning_ratio = active_seconds / Decimal(MINING_CYCLE_SECONDS)
    return money(BASE_MINING_INCOME * earning_ratio)


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
    window_start = cycle_window_start(cycle) or cycle.start_at
    window_end = cycle_window_end(cycle) or cycle.end_at
    total_seconds = max(1, int((window_end - window_start).total_seconds()))
    elapsed_seconds = min(max(0, int((normalize_utc(now) - window_start).total_seconds())), total_seconds)
    progress = (Decimal(elapsed_seconds) * Decimal("100") / Decimal(total_seconds)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(progress)


def remaining_seconds(cycle: MiningCycle | None, now: datetime | None = None) -> int:
    if not cycle:
        return 0
    now = now or utc_now()
    window_end = cycle_window_end(cycle) or cycle.end_at
    return max(0, int((window_end - normalize_utc(now)).total_seconds()))


def get_existing_referral_reward_record(
    db: Session,
    completed_cycle: MiningCycle,
    recipient_user_id: int,
    referral_level: int,
) -> Record | None:
    return (
        db.query(Record)
        .filter(
            Record.user_id == recipient_user_id,
            Record.record_type == "referral_reward",
            Record.notes.like(f"%mining_cycle_id={completed_cycle.cycle_uuid}%"),
            Record.notes.like(f"%recipient_user_id={recipient_user_id};%"),
            Record.notes.like(f"%referral_level={referral_level};%"),
        )
        .first()
    )


def build_referral_reward_notes(
    completed_cycle: MiningCycle,
    source_user: User,
    recipient_user: User,
    level: int,
    base_referral_source_income: Decimal,
    reward: Decimal,
) -> str:
    return (
        f"source_user_id={source_user.id}; "
        f"recipient_user_id={recipient_user.id}; "
        f"referral_level={level}; "
        f"base_referral_source_income={base_referral_source_income}; "
        f"reward_amount={reward}; "
        f"mining_cycle_id={completed_cycle.cycle_uuid};"
    )


def grant_referral_rewards(db: Session, completed_cycle: MiningCycle, completed_user: User) -> None:
    if completed_cycle.referral_reward_paid:
        return

    source_income = base_referral_source_income(completed_cycle)
    if source_income <= 0 or not completed_user.referrer:
        completed_cycle.referral_reward_paid = True
        completed_cycle.referrer_reward_amount = Decimal("0")
        return

    total_paid = Decimal("0")
    level = 1
    recipient = completed_user.referrer
    visited_user_ids = {completed_user.id}

    while recipient and recipient.id not in visited_user_ids:
        visited_user_ids.add(recipient.id)
        reward = money(source_income * (REFERRAL_REWARD_RATE ** level))
        existing_record = get_existing_referral_reward_record(db, completed_cycle, recipient.id, level)
        if existing_record:
            total_paid = money(total_paid + existing_record.amount)
        elif reward > 0:
            recipient.profits = money(as_decimal(recipient.profits) + reward)
            total_paid = money(total_paid + reward)
            db.add(
                Record(
                    user_id=recipient.id,
                    title=f"Level {level} referral mining reward",
                    amount=reward,
                    record_type="referral_reward",
                    notes=build_referral_reward_notes(
                        completed_cycle,
                        completed_user,
                        recipient,
                        level,
                        source_income,
                        reward,
                    ),
                )
            )
            db.add(recipient)
        recipient = recipient.referrer
        level += 1

    completed_cycle.referral_reward_paid = True
    completed_cycle.referrer_reward_amount = money(total_paid)


def add_cycle_records(db: Session, cycle: MiningCycle, user: User) -> None:
    notes = (
        f"Mining cycle: {cycle.cycle_uuid} | "
        f"Earning ratio: {cycle_earning_ratio(cycle)} | "
        f"Missed seconds: {cycle.missed_seconds or 0}"
    )
    remaining_income = money(cycle.final_income)
    earned_mining_income = money(as_decimal(cycle.mining_income) * cycle_earning_ratio(cycle))
    earned_referral_income = money(as_decimal(cycle.referral_income) * cycle_earning_ratio(cycle))

    mining_record_amount = min(earned_mining_income, remaining_income)
    remaining_income = money(remaining_income - mining_record_amount)
    referral_record_amount = min(earned_referral_income, remaining_income)
    remaining_income = money(remaining_income - referral_record_amount)
    capital_record_amount = remaining_income

    if mining_record_amount > 0:
        db.add(
            Record(
                user_id=user.id,
                title="Daily mining income",
                amount=mining_record_amount,
                record_type="mining_income",
                notes=notes,
            )
        )
    if referral_record_amount > 0:
        db.add(
            Record(
                user_id=user.id,
                title="Referral mining rewards",
                amount=referral_record_amount,
                record_type="referral_reward",
                notes=notes,
            )
        )
    if capital_record_amount > 0:
        db.add(
            Record(
                user_id=user.id,
                title="Capital income bonus",
                amount=capital_record_amount,
                record_type="capital_bonus",
                notes=notes,
            )
        )


def complete_mining_cycle(db: Session, user: User, cycle: MiningCycle, now: datetime | None = None) -> MiningCycle | None:
    now = now or utc_now()
    window_end = cycle_window_end(cycle) or cycle.end_at
    if cycle.status != "active" or cycle.completed_at is not None or window_end > normalize_utc(now):
        return None

    income = apply_income_to_cycle(cycle)
    earned_income = money(income["final_income"] * cycle_earning_ratio(cycle))
    cycle.status = "completed"
    cycle.completed_at = normalize_utc(now)
    user.profits = money(as_decimal(user.profits) + earned_income)
    user.daily_earnings = earned_income
    user.last_start_at = None

    add_cycle_records(db, cycle, user)
    grant_referral_rewards(db, cycle, user)
    return cycle


def settle_due_mining_cycle(user: User, db: Session, now: datetime | None = None) -> MiningCycle | None:
    now = now or utc_now()
    cycle = sync_active_cycle_with_user_capital(user, db)
    completed_cycle = complete_mining_cycle(db, user, cycle, now) if cycle else None
    if completed_cycle:
        db.commit()
        db.refresh(user)
        db.refresh(completed_cycle)
    return completed_cycle


def start_mining_cycle(user: User, db: Session, now: datetime | None = None) -> tuple[MiningCycle | None, str | None]:
    now = normalize_utc(now or utc_now())
    settle_due_mining_cycle(user, db, now)
    timing = get_cycle_timing(user.timezone, now)
    active_cycle = get_active_mining_cycle(db, user.id)
    if active_cycle and (cycle_window_end(active_cycle) or active_cycle.end_at) > now:
        return None, "You already have an active mining cycle."

    existing_window_cycle = get_cycle_for_window(
        db,
        user.id,
        timing["cycle_window_start"],
        timing["cycle_window_end"],
    )
    if existing_window_cycle:
        return None, "You already started mining for the current 18:00 cycle window."

    cycle = MiningCycle(
        cycle_uuid=uuid4().hex,
        user_id=user.id,
        start_at=timing["cycle_window_start"],
        end_at=timing["cycle_window_end"],
        cycle_window_start=timing["cycle_window_start"],
        cycle_window_end=timing["cycle_window_end"],
        actual_start_time=timing["actual_start_time"],
        status="active",
        active_seconds=timing["active_seconds"],
        missed_seconds=timing["missed_seconds"],
        earning_ratio=timing["earning_ratio"],
        active_capital=capital_money(user.capital),
        mining_income=BASE_MINING_INCOME,
    )
    user.last_start_at = timing["actual_start_time"]
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
    now = normalize_utc(now or utc_now())
    cycle = sync_active_cycle_with_user_capital(user, db)
    income = calculate_cycle_income(cycle.active_capital if cycle else user.capital, cycle.referral_income if cycle else Decimal("0"))
    earning_ratio = cycle_earning_ratio(cycle) if cycle else Decimal("0")
    expected_earned_income = money(income["final_income"] * earning_ratio) if cycle else Decimal("0")
    user_timezone = user.timezone or "UTC"
    window_start = cycle_window_start(cycle)
    window_end = cycle_window_end(cycle)
    actual_start = cycle_actual_start(cycle)
    return {
        "cycle": cycle,
        "cycle_id": cycle.cycle_uuid if cycle else "",
        "status": "active" if cycle else "ready",
        "can_start": cycle is None,
        "progress_percent": progress_percent(cycle, now),
        "remaining_seconds": remaining_seconds(cycle, now),
        "duration_seconds": MINING_CYCLE_SECONDS,
        "start_time": format_datetime_for_timezone(window_start, user_timezone),
        "actual_start_time": format_datetime_for_timezone(actual_start, user_timezone),
        "end_time": format_datetime_for_timezone(window_end, user_timezone),
        "start_time_iso": cycle_to_iso(window_start),
        "actual_start_time_iso": cycle_to_iso(actual_start),
        "end_time_iso": cycle_to_iso(window_end),
        "active_seconds": (cycle.active_seconds or MINING_CYCLE_SECONDS) if cycle else 0,
        "missed_seconds": (cycle.missed_seconds or 0) if cycle else 0,
        "earning_ratio": earning_ratio,
        "active_capital": income["active_capital"],
        "mining_income": income["mining_income"],
        "referral_income": income["referral_income"],
        "capital_bonus": income["capital_bonus"],
        "current_daily_income": income["final_income"],
        "full_daily_income": income["final_income"],
        "expected_earned_income": expected_earned_income,
        "current_total_balance": money(user.profits),
        "target_income": income["target_income"],
        "timezone": user_timezone,
    }
