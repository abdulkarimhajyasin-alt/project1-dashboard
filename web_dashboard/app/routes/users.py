from decimal import Decimal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.audit import audit_action_label, audit_action_tone, create_audit_log
from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_admin
from app.financial_state import build_admin_financial_summary, build_user_financial_state, sync_user_active_capital
from app.mining import get_referral_rank_info
from app.models import Admin, AuditLog, MiningCycle, Notification, PendingRequest, Record, SupportThread, User
from app.notifications import create_user_notification, get_admin_notifications_context
from app.support_chat import get_or_create_support_thread


router = APIRouter(prefix="/users")
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def users_redirect(**params: str) -> RedirectResponse:
    query = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(url=f"/users{query}", status_code=303)


def normalize_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def is_protected_admin_user(user: User, admin: Admin) -> bool:
    admin_identifiers = {
        normalize_identifier(admin.username),
        normalize_identifier(settings.admin_username),
    }
    admin_identifiers.discard("")
    user_identifiers = {
        normalize_identifier(user.username),
        normalize_identifier(user.email),
    }
    user_identifiers.discard("")
    return bool(admin_identifiers.intersection(user_identifiers))


def get_admin_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_user_label(user: User) -> str:
    return user.username or user.name or user.email or f"User #{user.id}"


def get_verified_full_name(user: User) -> str:
    if not user.verified:
        return ""
    return (user.legal_full_name or "").strip()


def get_user_name_display(user: User) -> str:
    return get_verified_full_name(user) or user.name or get_user_label(user)


def get_user_name_secondary(user: User, primary_label: str | None = None) -> str:
    primary = normalize_identifier(primary_label)
    for value in (user.username, user.email):
        clean_value = (value or "").strip()
        if clean_value and normalize_identifier(clean_value) != primary:
            return clean_value
    return ""


def format_admin_datetime(value, fmt: str) -> str:
    return value.strftime(fmt) if value else "-"


def format_admin_duration(seconds: int | None) -> str:
    remaining = max(0, int(seconds or 0))
    days, remainder = divmod(remaining, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_audit_amount(value: Decimal | int | float | None) -> str:
    if value is None:
        return "-"
    return f"${Decimal(value):,.8f}"


def user_initials(user: User) -> str:
    label = get_user_name_display(user)
    parts = [part for part in label.replace("_", " ").split() if part]
    if not parts:
        return "U"
    return "".join(part[0].upper() for part in parts[:2])


def get_active_miner_ids(db: Session) -> set[int]:
    rows = (
        db.query(MiningCycle.user_id)
        .filter(MiningCycle.status == "active", MiningCycle.completed_at.is_(None))
        .distinct()
        .all()
    )
    return {int(user_id) for (user_id,) in rows if user_id is not None}


def get_users_metrics(db: Session) -> dict:
    active_miner_ids = get_active_miner_ids(db)
    financial_summary = build_admin_financial_summary(db, settle_due_cycles=False)
    return {
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.status == "active").count(),
        "verified_users": db.query(User).filter(User.verified.is_(True)).count(),
        "active_miners": len(active_miner_ids),
        "total_capital": financial_summary["total_capital"],
        "total_profits": financial_summary["total_profits"],
        "total_balances": financial_summary["total_balances"],
    }


def get_direct_referral_counts(db: Session, user_ids: list[int]) -> dict[int, int]:
    if not user_ids:
        return {}

    counts: dict[int, int] = {}
    for index in range(0, len(user_ids), 500):
        batch = user_ids[index : index + 500]
        rows = (
            db.query(User.referred_by_id, func.count(User.id))
            .filter(User.referred_by_id.in_(batch))
            .group_by(User.referred_by_id)
            .all()
        )
        counts.update({int(parent_id): int(count) for parent_id, count in rows if parent_id is not None})
    return counts


def serialize_user_tree_node(
    user: User,
    children_count: int,
    admin: Admin,
    referrer_label: str = "-",
    active_miner_ids: set[int] | None = None,
) -> dict:
    rank_info = get_referral_rank_info(children_count)
    active_miner_ids = active_miner_ids or set()
    name_display = get_user_name_display(user)
    return {
        "id": user.id,
        "name": name_display,
        "name_secondary": get_user_name_secondary(user, name_display),
        "username": get_user_label(user),
        "email": user.email or "-",
        "country": user.residence_country or "-",
        "initials": user_initials(user),
        "status": user.status or "active",
        "verified": bool(user.verified),
        "is_mining": user.id in active_miner_ids,
        "plan": user.plan or "none",
        "profits": f"{Decimal(user.profits or 0):.4f}",
        "capital": f"{Decimal(user.capital or 0):.2f}",
        "rank": rank_info["rank"],
        "referrals_count": children_count,
        "has_children": children_count > 0,
        "children_count": children_count,
        "referrer": referrer_label,
        "last_start_at": format_admin_datetime(user.last_start_at, "%Y-%m-%d %H:%M"),
        "created_at": format_admin_datetime(user.created_at, "%Y-%m-%d"),
        "detail_url": f"/users/{user.id}",
        "message_url": f"/users/{user.id}/message",
        "delete_url": f"/users/{user.id}/delete",
        "delete_label": get_user_label(user),
        "delete_protected": is_protected_admin_user(user, admin),
    }


@router.get("", response_class=HTMLResponse)
def users_page(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    username = normalize_identifier(request.query_params.get("username"))
    email = normalize_identifier(request.query_params.get("email"))
    country = normalize_identifier(request.query_params.get("country"))
    plan_filter = normalize_identifier(request.query_params.get("plan"))
    verified_filter = normalize_identifier(request.query_params.get("verified"))
    user_filter = normalize_identifier(request.query_params.get("filter")) or "all"
    sort_by = normalize_identifier(request.query_params.get("sort")) or "newest"

    child_counts_subquery = (
        db.query(User.referred_by_id.label("parent_id"), func.count(User.id).label("referral_count"))
        .filter(User.referred_by_id.isnot(None))
        .group_by(User.referred_by_id)
        .subquery()
    )
    referral_count_column = func.coalesce(child_counts_subquery.c.referral_count, 0)
    active_miner_ids = get_active_miner_ids(db)

    query = (
        db.query(User, referral_count_column.label("referral_count"))
        .outerjoin(child_counts_subquery, child_counts_subquery.c.parent_id == User.id)
        .filter(User.referred_by_id.is_(None))
    )

    if username:
        query = query.filter(func.lower(func.coalesce(User.username, User.name, "")).like(f"%{username}%"))
    if email:
        query = query.filter(func.lower(User.email).like(f"%{email}%"))
    if country:
        query = query.filter(func.lower(func.coalesce(User.residence_country, "")).like(f"%{country}%"))
    if user_filter == "active":
        query = query.filter(User.status == "active")
    elif user_filter == "frozen":
        query = query.filter(User.status == "frozen")
    elif user_filter == "banned":
        query = query.filter(User.status == "banned")
    elif user_filter == "verified":
        query = query.filter(User.verified.is_(True))
    elif user_filter == "miner":
        query = query.filter(User.id.in_(list(active_miner_ids) or [-1]))
    elif user_filter == "vip":
        query = query.filter(User.plan == "vip")
    elif user_filter == "referrals":
        query = query.filter(referral_count_column > 0)
    if verified_filter == "yes":
        query = query.filter(User.verified.is_(True))
    elif verified_filter == "no":
        query = query.filter(User.verified.is_(False))
    if plan_filter in {"none", "silver", "gold", "vip"}:
        query = query.filter(User.plan == plan_filter)

    if sort_by == "capital":
        query = query.order_by(User.capital.desc(), User.created_at.desc())
    elif sort_by == "profits":
        query = query.order_by(User.profits.desc(), User.created_at.desc())
    elif sort_by == "referrals":
        query = query.order_by(referral_count_column.desc(), User.created_at.desc())
    else:
        query = query.order_by(User.created_at.desc())

    rows = query.all()
    users = [user for user, _ in rows]
    referral_counts = {user.id: int(referral_count or 0) for user, referral_count in rows}
    protected_user_ids = [user.id for user in users if is_protected_admin_user(user, admin)]
    user_cards = [
        {
            "user": user,
            "referral_count": referral_counts.get(user.id, 0),
            "rank_info": get_referral_rank_info(referral_counts.get(user.id, 0)),
            "delete_label": get_user_label(user),
            "delete_protected": user.id in protected_user_ids,
            "initials": user_initials(user),
            "is_mining": user.id in active_miner_ids,
            "display_name": get_user_name_display(user),
            "display_name_secondary": get_user_name_secondary(user, get_user_name_display(user)),
        }
        for user in users
    ]
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "users",
            "users": users,
            "user_cards": user_cards,
            "referral_counts": referral_counts,
            "protected_user_ids": protected_user_ids,
            "get_referral_rank_info": get_referral_rank_info,
            "users_metrics": get_users_metrics(db),
            "active_filter": user_filter,
            "active_sort": sort_by,
            "active_plan": plan_filter,
            "active_verified": verified_filter,
            "search_username": username,
            "search_email": email,
            "search_country": country,
            **get_admin_notifications_context(db),
        },
    )


@router.get("/{user_id}/children")
def user_children(user_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    parent = get_admin_user(db, user_id)
    children = (
        db.query(User)
        .filter(User.referred_by_id == parent.id)
        .order_by(User.created_at.desc())
        .all()
    )
    child_counts = get_direct_referral_counts(db, [child.id for child in children])
    parent_label = get_user_label(parent)
    active_miner_ids = get_active_miner_ids(db)
    return JSONResponse(
        {
            "parent_id": parent.id,
            "children": [
                serialize_user_tree_node(
                    child,
                    child_counts.get(child.id, 0),
                    admin,
                    parent_label,
                    active_miner_ids,
                )
                for child in children
            ],
        }
    )


@router.get("/{user_id}", response_class=HTMLResponse)
def user_details(user_id: int, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = get_admin_user(db, user_id)
    records = db.query(Record).filter(Record.user_id == user.id).order_by(Record.created_at.desc()).all()
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.target_user_id == user.id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(30)
        .all()
    )
    financial_state = build_user_financial_state(user, db)
    mining_status = financial_state["mining_status"]
    withdrawal_cycle = financial_state["withdrawal_cycle"]
    pending_verification_request = (
        db.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.id,
            PendingRequest.request_type == "verification",
            PendingRequest.status == "pending",
        )
        .order_by(PendingRequest.created_at.desc())
        .first()
    )
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "users",
            "user": user,
            "records": records,
            "transaction_count": len(records),
            "total_balance": financial_state["total_balance"],
            "telegram_id": getattr(user, "telegram_id", None) or "-",
            "mining_status": mining_status,
            "financial_state": financial_state,
            "next_profit_countdown": format_admin_duration(mining_status.get("remaining_seconds")),
            "withdrawal_cycle": withdrawal_cycle,
            "next_withdraw_countdown": format_admin_duration(withdrawal_cycle.get("withdrawal_remaining_seconds")),
            "pending_verification_request": pending_verification_request,
            "audit_logs": audit_logs,
            "audit_action_label": audit_action_label,
            "audit_action_tone": audit_action_tone,
            "format_audit_amount": format_audit_amount,
            "delete_protected": is_protected_admin_user(user, admin),
            "referral_rank_info": financial_state["referral_rank_info"],
            **get_admin_notifications_context(db),
        },
    )


@router.post("/{user_id}/message")
def open_user_message_thread(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    thread = get_or_create_support_thread(db, user)
    thread_id = thread.id
    db.commit()
    return RedirectResponse(url=f"/support/chat/{thread_id}", status_code=303)


@router.post("")
def create_user(
    name: str = Form(...),
    email: str = Form(...),
    status: str = Form("active"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = User(name=name.strip(), email=email.strip().lower(), status=status)
    db.add(user)
    db.commit()
    return RedirectResponse(url="/users", status_code=303)


@router.post("/{user_id}/status")
def update_user_status(
    user_id: int,
    status_action: str = Form(...),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    status_map = {
        "ban": "banned",
        "unban": "active",
        "freeze": "frozen",
        "unfreeze": "active",
        "activate": "active",
        "deactivate": "inactive",
    }
    user.status = status_map.get(status_action, user.status)
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/plan")
def update_user_plan(
    user_id: int,
    plan: str = Form("none"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    allowed_plans = {"none", "silver", "gold", "vip"}
    previous_plan = user.plan
    user.plan = plan if plan in allowed_plans else "none"
    create_audit_log(
        db,
        actor_user_id=admin.id,
        actor_role="admin",
        target_user_id=user.id,
        action_type="user_subscription_deleted" if user.plan == "none" and previous_plan != "none" else "user_subscription_updated",
        entity_type="user",
        entity_id=user.id,
        reason=f"Plan changed by admin: {admin.username}",
        metadata={"previous_plan": previous_plan, "new_plan": user.plan},
    )
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/balance")
def adjust_user_balance(
    user_id: int,
    field: str = Form(...),
    operation: str = Form(...),
    amount: Decimal = Form(0),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    safe_amount = abs(amount)
    delta = safe_amount if operation == "add" else -safe_amount

    if field == "profits":
        amount_before = Decimal(user.profits or 0)
        user.profits = max(Decimal("0"), Decimal(user.profits or 0) + delta)
        amount_after = Decimal(user.profits or 0)
        action_type = "admin_available_yield_adjustment"
    else:
        amount_before = Decimal(user.capital or 0)
        user.capital = max(Decimal("0"), Decimal(user.capital or 0) + delta)
        sync_user_active_capital(user, db)
        amount_after = Decimal(user.capital or 0)
        action_type = "admin_capital_adjustment"

    db.add(
        Record(
            user_id=user.id,
            title="Admin balance adjustment",
            amount=delta,
            record_type=f"{field}_{operation}",
            notes=f"Adjusted by admin: {admin.username}",
        )
    )
    create_audit_log(
        db,
        actor_user_id=admin.id,
        actor_role="admin",
        target_user_id=user.id,
        action_type=action_type,
        entity_type="user",
        entity_id=user.id,
        amount_before=amount_before,
        amount_after=amount_after,
        amount_delta=amount_after - amount_before,
        currency="USD",
        reason=f"Adjusted by admin: {admin.username}",
        metadata={"field": field, "operation": operation, "requested_amount": safe_amount},
    )
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/manual-withdrawal-unlock")
def toggle_manual_withdrawal_unlock(
    user_id: int,
    unlock_action: str = Form(...),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    should_unlock = unlock_action == "open"
    previous_unlock = bool(user.manual_withdrawal_unlock)
    user.manual_withdrawal_unlock = should_unlock
    create_user_notification(
        db,
        user_id=user.id,
        title="صلاحية السحب",
        message=(
            "تم فتح السحب لديك من قبل الإدارة كمكافأة على أدائك."
            if should_unlock
            else "تم إغلاق صلاحية السحب اليدوي من قبل الإدارة."
        ),
        target_url="/user/withdraw",
        kind="withdraw",
        data={
            "Status": "manual withdrawal unlocked" if should_unlock else "manual withdrawal locked",
            "Reviewed by": admin.username,
        },
    )
    create_audit_log(
        db,
        actor_user_id=admin.id,
        actor_role="admin",
        target_user_id=user.id,
        action_type="manual_withdrawal_unlocked" if should_unlock else "manual_withdrawal_locked",
        entity_type="user",
        entity_id=user.id,
        reason=f"Manual withdrawal {'unlocked' if should_unlock else 'locked'} by admin: {admin.username}",
        metadata={"previous_unlock": previous_unlock, "new_unlock": should_unlock},
    )
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}#financial", status_code=303)


@router.post("/{user_id}/reset-cycle")
def reset_user_cycle(user_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = get_admin_user(db, user_id)
    active_cycle_ids = [
        cycle_id
        for (cycle_id,) in db.query(MiningCycle.id)
        .filter(MiningCycle.user_id == user.id, MiningCycle.status == "active")
        .all()
    ]
    (
        db.query(MiningCycle)
        .filter(MiningCycle.user_id == user.id, MiningCycle.status == "active")
        .update({"status": "cancelled"}, synchronize_session=False)
    )
    user.last_start_at = None
    create_audit_log(
        db,
        actor_user_id=admin.id,
        actor_role="admin",
        target_user_id=user.id,
        action_type="mining_cycle_cancelled_by_admin",
        entity_type="mining_cycle",
        entity_id=active_cycle_ids[0] if len(active_cycle_ids) == 1 else None,
        reason=f"Active mining cycle reset by admin: {admin.username}",
        metadata={"cancelled_cycle_ids": active_cycle_ids},
    )
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/delete")
def delete_user(
    user_id: int,
    confirm_delete: str = Form(""),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if confirm_delete != "yes":
        return users_redirect(delete_error="Delete confirmation is required.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return users_redirect(delete_error="User not found.")

    if is_protected_admin_user(user, admin):
        return users_redirect(delete_error="Main admin account cannot be deleted.")

    try:
        deleted_user_id = user.id
        deleted_user_metadata = {
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "status": user.status,
            "plan": user.plan,
            "capital": user.capital,
            "profits": user.profits,
            "referrals_count": len(user.referrals),
        }
        create_audit_log(
            db,
            actor_user_id=admin.id,
            actor_role="admin",
            target_user_id=deleted_user_id,
            action_type="user_deleted",
            entity_type="user",
            entity_id=deleted_user_id,
            amount_before=Decimal(user.capital or 0) + Decimal(user.profits or 0),
            amount_after=Decimal("0"),
            currency="USD",
            reason=f"Deleted by admin: {admin.username}",
            metadata=deleted_user_metadata,
        )
        for referral in list(user.referrals):
            referral.referred_by_id = None

        db.query(PendingRequest).filter(PendingRequest.user_id == user.id).update(
            {PendingRequest.user_id: None},
            synchronize_session=False,
        )
        db.query(Notification).filter(Notification.recipient_user_id == user.id).update(
            {Notification.recipient_user_id: None},
            synchronize_session=False,
        )

        support_thread = db.query(SupportThread).filter(SupportThread.user_id == user.id).first()
        if support_thread:
            db.delete(support_thread)
        db.delete(user)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return users_redirect(delete_error="Could not delete user. Please try again.")

    return users_redirect(delete_success="1")
