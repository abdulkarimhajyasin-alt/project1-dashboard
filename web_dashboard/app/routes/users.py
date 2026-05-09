from decimal import Decimal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, Notification, PendingRequest, Record, SupportThread, User
from app.notifications import get_admin_notifications_context
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


@router.get("", response_class=HTMLResponse)
def users_page(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    protected_user_ids = [user.id for user in users if is_protected_admin_user(user, admin)]
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "users",
            "users": users,
            "protected_user_ids": protected_user_ids,
            **get_admin_notifications_context(db),
        },
    )


@router.get("/{user_id}", response_class=HTMLResponse)
def user_details(user_id: int, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = get_admin_user(db, user_id)
    records = db.query(Record).filter(Record.user_id == user.id).order_by(Record.created_at.desc()).all()
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "users",
            "user": user,
            "records": records,
            "delete_protected": is_protected_admin_user(user, admin),
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
    user.plan = plan if plan in allowed_plans else "none"
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
        user.profits = max(Decimal("0"), Decimal(user.profits or 0) + delta)
    else:
        user.capital = max(Decimal("0"), Decimal(user.capital or 0) + delta)

    db.add(
        Record(
            user_id=user.id,
            title="Admin balance adjustment",
            amount=delta,
            record_type=f"{field}_{operation}",
            notes=f"Adjusted by admin: {admin.username}",
        )
    )
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/reset-cycle")
def reset_user_cycle(user_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = get_admin_user(db, user_id)
    user.last_start_at = None
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
