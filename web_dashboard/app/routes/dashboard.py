import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from urllib.parse import quote, urlencode

from app.database import get_db
from app.dependencies import get_current_admin
from app.financial_state import build_admin_financial_summary, sync_user_active_capital
from app.mining import (
    calculate_cycle_income,
    cycle_actual_start,
    cycle_earning_ratio,
    cycle_window_end,
    cycle_window_start,
    get_referral_rank_info,
    money,
    progress_percent,
    remaining_seconds,
)
from app.models import Admin, AppSetting, MiningCycle, Notification, PendingRequest, Record, SupportMessage, SupportThread, User
from app.notifications import build_notifications_poll_payload, create_user_notification, get_admin_notifications_context
from app.plans import determine_plan_for_amount, plan_label
from app.support_chat import SupportAttachmentError, add_support_message, get_thread_messages
from app.utils import format_datetime_for_timezone


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_SETTINGS = {
    "site_name": "",
    "support_email": "",
    "maintenance_mode": "off",
}

PENDING_REQUEST_SECTIONS = {
    "deposit": {
        "title": "طلبات الإيداع",
        "badge": "إيداع",
        "amount_label": "المبلغ",
        "empty": "لا توجد طلبات إيداع معلقة.",
    },
    "plan_subscription": {
        "title": "طلبات الاشتراك",
        "badge": "اشتراك",
        "amount_label": "المبلغ",
        "empty": "لا توجد طلبات اشتراك معلقة.",
    },
    "withdraw": {
        "title": "طلبات السحب",
        "badge": "سحب",
        "amount_label": "المبلغ",
        "empty": "لا توجد طلبات سحب معلقة.",
    },
    "capital_withdraw": {
        "title": "طلبات سحب رأس المال",
        "badge": "رأس المال",
        "amount_label": "رأس المال",
        "empty": "لا توجد طلبات سحب رأس مال معلقة.",
    },
    "verification": {
        "title": "طلبات توثيق الحساب",
        "badge": "توثيق",
        "amount_label": "الاسم الكامل",
        "empty": "لا توجد طلبات توثيق معلقة.",
    },
}


def get_admin_metrics(db: Session) -> dict:
    financial_summary = build_admin_financial_summary(db)
    users_count = db.query(User).count()
    active_users_count = db.query(User).filter(User.status == "active").count()
    records_count = db.query(Record).count()
    total_amount = db.query(func.coalesce(func.sum(Record.amount), 0)).scalar()
    latest_records = db.query(Record).order_by(Record.created_at.desc()).limit(5).all()
    top_referral_users = sorted(db.query(User).all(), key=lambda item: len(item.referrals), reverse=True)[:5]
    stored_settings = {item.key: item.value for item in db.query(AppSetting).all()}
    settings = {**DEFAULT_SETTINGS, **stored_settings}

    return {
        "users_count": users_count,
        "active_users_count": active_users_count,
        "records_count": records_count,
        "total_amount": total_amount,
        "total_capital": financial_summary["total_capital"],
        "total_profits": financial_summary["total_profits"],
        "active_cycles": financial_summary["active_cycles"],
        "latest_records": latest_records,
        "top_referral_users": top_referral_users,
        "get_referral_rank_info": get_referral_rank_info,
        "settings": settings,
        **get_admin_notifications_context(db),
    }


def format_seconds(total_seconds: int | None) -> str:
    safe_seconds = max(0, int(total_seconds or 0))
    hours = safe_seconds // 3600
    minutes = (safe_seconds % 3600) // 60
    seconds = safe_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def serialize_active_mining_cycle(cycle: MiningCycle) -> dict:
    user = cycle.user
    timezone_name = user.timezone or "UTC"
    income = calculate_cycle_income(cycle.active_capital, cycle.referral_income)
    earning_ratio = cycle_earning_ratio(cycle)
    expected_earned_income = money(income["final_income"] * earning_ratio)
    cycle_remaining_seconds = remaining_seconds(cycle)
    return {
        "cycle_id": cycle.cycle_uuid,
        "user_id": user.id,
        "name": user.name or "-",
        "username": user.username or user.name or "-",
        "email": user.email or "-",
        "active_capital": f"{money(cycle.active_capital):.2f}",
        "current_daily_income": f"{income['final_income']:.4f}",
        "expected_earned_income": f"{expected_earned_income:.4f}",
        "cycle_start_time": format_datetime_for_timezone(cycle_window_start(cycle), timezone_name),
        "actual_start_time": format_datetime_for_timezone(cycle_actual_start(cycle), timezone_name),
        "end_time": format_datetime_for_timezone(cycle_window_end(cycle), timezone_name),
        "remaining_time": format_seconds(cycle_remaining_seconds),
        "missed_time": format_seconds(cycle.missed_seconds or 0),
        "progress_percent": progress_percent(cycle),
        "timezone": timezone_name,
        "detail_url": f"/users/{user.id}",
    }


def get_active_mining_cycles(db: Session) -> list[MiningCycle]:
    now = datetime.utcnow()
    return (
        db.query(MiningCycle)
        .options(joinedload(MiningCycle.user))
        .join(User, MiningCycle.user_id == User.id)
        .filter(
            MiningCycle.status == "active",
            MiningCycle.completed_at.is_(None),
            func.coalesce(MiningCycle.cycle_window_end, MiningCycle.end_at) > now,
        )
        .order_by(MiningCycle.start_at.desc(), MiningCycle.created_at.desc())
        .all()
    )


def get_support_threads(db: Session) -> list[SupportThread]:
    return db.query(SupportThread).order_by(SupportThread.updated_at.desc()).all()


def get_pending_requests_context(db: Session) -> dict:
    pending_requests = (
        db.query(PendingRequest)
        .filter(PendingRequest.status == "pending")
        .order_by(PendingRequest.created_at.desc())
        .all()
    )
    grouped_requests = {request_type: [] for request_type in PENDING_REQUEST_SECTIONS}
    for pending_request in pending_requests:
        grouped_requests.setdefault(pending_request.request_type, []).append(pending_request)

    return {
        "pending_request_sections": PENDING_REQUEST_SECTIONS,
        "pending_requests_by_type": grouped_requests,
        "pending_requests_total": len(pending_requests),
    }


def apply_verification_request_to_user(pending_request: PendingRequest, *, approve: bool = False) -> None:
    user = pending_request.user
    if not user:
        return

    user.legal_full_name = pending_request.legal_full_name or pending_request.full_name
    user.residence_country = pending_request.country
    user.timezone = pending_request.timezone
    user.document_type = pending_request.document_type
    user.verification_requested_at = pending_request.created_at
    if approve:
        user.verified = True
        user.verification_status = "verified"
        user.verification_approved_at = datetime.utcnow()
    elif user.verification_status != "verified":
        user.verified = False
        user.verification_status = pending_request.status


def update_pending_request_detail(pending_request: PendingRequest, key: str, value: str) -> None:
    if not value:
        return
    try:
        details = json.loads(pending_request.details_json or "{}")
    except json.JSONDecodeError:
        details = {}
    if not isinstance(details, dict):
        details = {}
    details[key] = value
    pending_request.details_json = json.dumps(details, ensure_ascii=False)


def update_pending_request_details(pending_request: PendingRequest, values: dict[str, str]) -> None:
    try:
        details = json.loads(pending_request.details_json or "{}")
    except json.JSONDecodeError:
        details = {}
    if not isinstance(details, dict):
        details = {}
    for key, value in values.items():
        if value:
            details[key] = value
    pending_request.details_json = json.dumps(details, ensure_ascii=False)


def clean_rejection_reason(reason: str) -> str:
    return " ".join((reason or "").split())[:500]


def request_prefers_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    requested_with = request.headers.get("x-requested-with", "")
    return "application/json" in accept.lower() or requested_with.lower() == "xmlhttprequest"


def missing_rejection_reason_response(request: Request):
    message = "Rejection reason is required."
    if request_prefers_json(request):
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    return RedirectResponse(url=f"/notifications?{urlencode({'reject_error': message})}", status_code=303)


def get_support_notification_message(support_message: SupportMessage) -> str:
    if support_message.has_attachment_data:
        return "صورة" if support_message.is_image else "ملف"
    return support_message.body or "رسالة جديدة"


def serialize_support_message(message: SupportMessage, thread: SupportThread) -> dict:
    sender_label = "الدعم" if message.sender_type == "admin" else thread.user.username or thread.user.name
    body = message.body or ""
    return {
        "id": message.id,
        "sender_type": message.sender_type,
        "sender": message.sender_type,
        "role": message.sender_type,
        "sender_label": sender_label,
        "body": body,
        "content": body,
        "created_at": message.created_at.isoformat(),
        "created_label": message.created_at.strftime("%Y-%m-%d %H:%M"),
        "has_attachment": message.has_attachment_data,
        "is_image": bool(message.is_image),
        "attachment_url": f"/support/attachments/{message.id}" if message.has_attachment_data else "",
    }


def get_admin_poll_messages(db: Session, thread_id: int | None) -> list[dict]:
    if not thread_id:
        return []
    thread = db.query(SupportThread).filter(SupportThread.id == thread_id).first()
    if not thread:
        return []
    return [serialize_support_message(message, thread) for message in get_thread_messages(db, thread)]


@router.get("/support/attachments/{message_id}")
def support_attachment(message_id: int, request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    user_id = request.session.get("user_id")
    if not admin_id and not user_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    query = (
        db.query(SupportMessage)
        .join(SupportThread, SupportMessage.thread_id == SupportThread.id)
        .filter(SupportMessage.id == message_id)
    )
    if not admin_id:
        query = query.filter(SupportThread.user_id == user_id)

    message = query.first()
    if not message:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if message.attachment_data_length <= 0:
        raise HTTPException(status_code=404, detail="Attachment not found")

    headers = {}
    filename = message.attachment_name or f"support_attachment_{message.id}"
    if not message.is_image:
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"

    return Response(content=bytes(message.attachment_data), media_type=message.attachment_type, headers=headers)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    context = get_admin_metrics(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "dashboard",
            **context,
        },
    )


@router.get("/dashboard/active-mining-cycles")
def active_mining_cycles(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    cycles = get_active_mining_cycles(db)
    return JSONResponse(
        {
            "count": len(cycles),
            "cycles": [serialize_active_mining_cycle(cycle) for cycle in cycles],
        }
    )


@router.get("/notifications", response_class=HTMLResponse)
def notifications(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    context = get_admin_metrics(db)
    pending_context = get_pending_requests_context(db)
    return templates.TemplateResponse(
        "notifications.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "notifications",
            "format_datetime_for_timezone": format_datetime_for_timezone,
            **context,
            **pending_context,
        },
    )


@router.get("/dashboard/notifications/poll")
def admin_notifications_poll(
    thread_id: int | None = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return JSONResponse(
        build_notifications_poll_payload(
            db,
            recipient_type="admin",
            open_prefix="/notifications",
            messages=get_admin_poll_messages(db, thread_id),
        )
    )


@router.post("/pending-requests/{request_id}/accept")
def accept_pending_request(request_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    pending_request = db.query(PendingRequest).filter(PendingRequest.id == request_id).with_for_update().first()
    if pending_request and pending_request.status == "pending":
        if pending_request.request_type in {"deposit", "plan_subscription"} and pending_request.user and pending_request.amount:
            amount = money(pending_request.amount)
            final_plan = determine_plan_for_amount(amount)
            pending_request.user.capital = max(Decimal("0"), Decimal(pending_request.user.capital or 0) + amount)
            pending_request.user.plan = final_plan
            sync_user_active_capital(pending_request.user, db)
            db.add(
                Record(
                    user_id=pending_request.user.id,
                    title="Approved capital deposit",
                    amount=amount,
                    record_type="capital_deposit",
                    notes=f"Approved by admin: {admin.username}; activated plan: {plan_label(final_plan)}",
                )
            )
            update_pending_request_detail(pending_request, "Activated plan", plan_label(final_plan))
            create_user_notification(
                db,
                user_id=pending_request.user.id,
                title="Plan subscription approved" if pending_request.request_type == "plan_subscription" else "Deposit approved",
                message=(
                    f"Your {plan_label(final_plan)} subscription was approved for {amount:.2f} USDT."
                    if pending_request.request_type == "plan_subscription"
                    else f"Your deposit was approved for {amount:.2f} USDT. Activated plan: {plan_label(final_plan)}."
                ),
                target_url="/user/plans",
                kind=pending_request.request_type,
                data={
                    "Status": "approved",
                    "Amount": f"{amount:.2f} USDT",
                    "Activated plan": plan_label(final_plan),
                    "Reviewed by": admin.username,
                },
            )
        elif pending_request.request_type == "withdraw" and pending_request.user and pending_request.amount:
            amount = money(pending_request.amount)
            pending_request.user.profits = max(Decimal("0"), Decimal(pending_request.user.profits or 0) - amount)
            db.add(
                Record(
                    user_id=pending_request.user.id,
                    title="Approved profit withdrawal",
                    amount=-amount,
                    record_type="profit_withdraw",
                    notes=f"Approved by admin: {admin.username}",
                )
            )
            create_user_notification(
                db,
                user_id=pending_request.user.id,
                title="تمت الموافقة على طلب سحب الأرباح",
                message=f"تمت الموافقة على طلب سحب الأرباح بقيمة {amount:.2f} USDT.",
                target_url="/user/withdraw",
                kind="withdraw",
                data={
                    "Status": "approved",
                    "Amount": f"{amount:.2f} USDT",
                    "Reviewed by": admin.username,
                },
            )
        elif pending_request.request_type == "capital_withdraw" and pending_request.user and pending_request.amount:
            amount = money(pending_request.amount)
            pending_request.user.capital = max(Decimal("0"), Decimal(pending_request.user.capital or 0) - amount)
            db.add(
                Record(
                    user_id=pending_request.user.id,
                    title="Approved capital withdrawal",
                    amount=-amount,
                    record_type="capital_withdraw",
                    notes=f"Approved by admin: {admin.username}",
                )
            )
        elif pending_request.request_type == "verification":
            apply_verification_request_to_user(pending_request, approve=True)
            if pending_request.user:
                create_user_notification(
                    db,
                    user_id=pending_request.user.id,
                    title="Verification approved",
                    message="Your account verification request has been approved.",
                    target_url="/user/account",
                    kind="verification",
                    data={"Status": "approved", "Reviewed by": admin.username},
                )
        pending_request.status = "approved"
        db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/pending-requests/{request_id}/reject")
def reject_pending_request(
    request_id: int,
    request: Request,
    reject_reason: str = Form(""),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    pending_request = db.query(PendingRequest).filter(PendingRequest.id == request_id).with_for_update().first()
    if pending_request and pending_request.status == "pending":
        clean_reason = clean_rejection_reason(reject_reason)
        if not clean_reason:
            return missing_rejection_reason_response(request)

        pending_request.status = "rejected"
        update_pending_request_details(
            pending_request,
            {
                "rejection_reason": clean_reason,
                "rejected_at": datetime.utcnow().isoformat(),
            },
        )
        if pending_request.request_type == "verification" and pending_request.user:
            pending_request.user.verified = False
            pending_request.user.verification_status = "rejected"
            pending_request.user.verification_approved_at = None
            message = f"Your account verification request has been rejected. Reason: {clean_reason}"
            create_user_notification(
                db,
                user_id=pending_request.user.id,
                title="Verification rejected",
                message=message,
                target_url="/user/account",
                kind="verification",
                data={
                    "Status": "rejected",
                    "Reason": clean_reason,
                    "Reviewed by": admin.username,
                },
            )
        elif pending_request.request_type in {"deposit", "plan_subscription"} and pending_request.user:
            amount = money(pending_request.amount or 0)
            message = (
                "Your plan subscription request was rejected."
                if pending_request.request_type == "plan_subscription"
                else "Your deposit request was rejected."
            )
            message = f"{message} Reason: {clean_reason}"
            create_user_notification(
                db,
                user_id=pending_request.user.id,
                title="Plan subscription rejected" if pending_request.request_type == "plan_subscription" else "Deposit rejected",
                message=message,
                target_url="/user/plans",
                kind=pending_request.request_type,
                data={
                    "Status": "rejected",
                    "Amount": f"{amount:.2f} USDT" if amount else "-",
                    "Reason": clean_reason,
                    "Reviewed by": admin.username,
                },
            )
        elif pending_request.request_type == "withdraw" and pending_request.user:
            message = "تم رفض طلب سحب الأرباح."
            if clean_reason:
                message = f"{message} السبب: {clean_reason}"
            create_user_notification(
                db,
                user_id=pending_request.user.id,
                title="تم رفض طلب سحب الأرباح",
                message=message,
                target_url="/user/withdraw",
                kind="withdraw",
                data={
                    "Status": "rejected",
                    "Reason": clean_reason,
                    "Reviewed by": admin.username,
                },
            )
        db.commit()
        if request_prefers_json(request):
            return JSONResponse({"ok": True})
    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/pending-requests/{request_id}/save")
def save_pending_request(request_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    pending_request = db.query(PendingRequest).filter(PendingRequest.id == request_id).with_for_update().first()
    if pending_request and pending_request.request_type == "verification":
        apply_verification_request_to_user(pending_request, approve=False)
        db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@router.get("/pending-requests/{request_id}/image/{image_type}")
def pending_request_image(
    request_id: int,
    image_type: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    pending_request = db.query(PendingRequest).filter(PendingRequest.id == request_id).first()
    if not pending_request or pending_request.request_type not in {"verification", "deposit", "plan_subscription"}:
        raise HTTPException(status_code=404, detail="Image not found")

    if pending_request.request_type in {"deposit", "plan_subscription"}:
        if image_type != "proof" or not pending_request.front_image_data:
            raise HTTPException(status_code=404, detail="Image not found")
        return Response(
            content=bytes(pending_request.front_image_data),
            media_type=pending_request.front_image_mime_type or "image/jpeg",
        )

    image_map = {
        "front": (pending_request.front_image_data, pending_request.front_image_mime_type),
        "back": (pending_request.back_image_data, pending_request.back_image_mime_type),
        "passport": (pending_request.passport_image_data, pending_request.passport_image_mime_type),
    }
    image_data, mime_type = image_map.get(image_type, (None, None))
    if not image_data:
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(content=bytes(image_data), media_type=mime_type or "image/jpeg")


@router.get("/notifications/{notification_id}/open")
def open_notification(
    notification_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.recipient_type == "admin")
        .first()
    )
    if not notification:
        return RedirectResponse(url="/notifications", status_code=303)

    notification.is_read = True
    target_url = notification.target_url or "/notifications"
    db.commit()
    return RedirectResponse(url=target_url, status_code=303)


@router.post("/notifications/clear")
def clear_notifications(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    (
        db.query(Notification)
        .filter(Notification.recipient_type == "admin", Notification.is_read.is_(False))
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    if request.headers.get("x-requested-with") == "fetch" or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            build_notifications_poll_payload(
                db,
                recipient_type="admin",
                open_prefix="/notifications",
            )
        )
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/support", response_class=HTMLResponse)
def support(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    context = get_admin_metrics(db)
    return templates.TemplateResponse(
        "support.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "support",
            "support_threads": get_support_threads(db),
            "active_support_thread": None,
            "support_messages": [],
            "support_chat_open": False,
            **context,
        },
    )


@router.get("/support/chat/{thread_id}", response_class=HTMLResponse)
def support_chat(
    thread_id: int,
    request: Request,
    error: str = "",
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    context = get_admin_metrics(db)
    thread = db.query(SupportThread).filter(SupportThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Support thread not found")

    return templates.TemplateResponse(
        "support.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "support",
            "support_threads": get_support_threads(db),
            "active_support_thread": thread,
            "support_thread": thread,
            "support_messages": get_thread_messages(db, thread),
            "support_chat_mode": "admin",
            "support_chat_open": True,
            "support_chat_post_url": f"/support/chat/{thread.id}/reply",
            "support_chat_title": f"محادثة {thread.user.username or thread.user.name}",
            "support_chat_subtitle": thread.user.email,
            "support_chat_error": error,
            "can_user_send_support": True,
            **context,
        },
    )


@router.post("/support/chat/{thread_id}/reply")
def support_chat_reply(
    thread_id: int,
    request: Request,
    message: str = Form(""),
    attachment: UploadFile | None = File(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    thread = db.query(SupportThread).filter(SupportThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Support thread not found")

    try:
        support_message = add_support_message(
            db,
            thread=thread,
            sender_type="admin",
            body=message,
            attachment=attachment,
        )
    except SupportAttachmentError as exc:
        if request.headers.get("x-requested-with") == "fetch":
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return RedirectResponse(url=f"/support/chat/{thread.id}?{urlencode({'error': str(exc)})}", status_code=303)
    if support_message:
        create_user_notification(
            db,
            user_id=thread.user_id,
            title="الدعم",
            message=get_support_notification_message(support_message),
            target_url="/user/support?chat=open",
            kind="support",
        )
        db.commit()
        db.refresh(support_message)
        if request.headers.get("x-requested-with") == "fetch":
            messages = [serialize_support_message(item, thread) for item in get_thread_messages(db, thread)]
            return JSONResponse(
                {
                    "ok": True,
                    "message": serialize_support_message(support_message, thread),
                    "messages": messages,
                }
            )
    elif request.headers.get("x-requested-with") == "fetch":
        return JSONResponse({"ok": False, "error": "Message is empty."}, status_code=400)
    return RedirectResponse(url=f"/support/chat/{thread.id}", status_code=303)


@router.post("/support/chat/{thread_id}/delete")
def delete_support_chat(
    thread_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    thread = db.query(SupportThread).filter(SupportThread.id == thread_id).first()
    if thread:
        (
            db.query(Notification)
            .filter(
                or_(
                    Notification.target_url == f"/support/chat/{thread.id}",
                    (
                        (Notification.recipient_type == "user")
                        & (Notification.recipient_user_id == thread.user_id)
                        & (Notification.kind == "support")
                    ),
                )
            )
            .update({"is_read": True}, synchronize_session=False)
        )
        db.delete(thread)
        db.commit()
    return RedirectResponse(url="/support", status_code=303)
