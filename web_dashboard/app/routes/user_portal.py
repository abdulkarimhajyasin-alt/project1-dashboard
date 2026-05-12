# -*- coding: utf-8 -*-
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.branding import PLATFORM_NAME, PLATFORM_TAGLINE, build_referral_share_context
from app.countries import COUNTRY_TIMEZONE_CHOICES, get_country_timezone
from app.database import get_db
from app.dependencies import get_current_user, is_maintenance_enabled
from app.financial_state import MIN_WITHDRAWAL, build_user_financial_state, build_withdrawal_cycle_status
from app.mining import build_mining_status, cycle_earning_ratio, settle_due_mining_cycle, start_mining_cycle
from app.models import Notification, PendingRequest, Record, User
from app.notifications import build_notifications_poll_payload, create_admin_notification, get_user_notifications_context
from app.config import get_settings
from app.plans import MIN_DEPOSIT_AMOUNT, determine_plan_for_amount, parse_deposit_amount, plan_label, validate_amount_for_plan
from app.security import hash_password, verify_password
from app.support_chat import (
    SupportAttachmentError,
    add_support_message,
    can_user_send_support_message,
    get_or_create_support_thread,
    get_thread_messages,
)
from app.utils import format_datetime_for_timezone


router = APIRouter(prefix="/user")
templates = Jinja2Templates(directory="app/templates")
app_settings = get_settings()
PENDING_PLAN_SUBSCRIPTION_MESSAGE = "لديك طلب اشتراك قيد المراجعة حالياً. يرجى انتظار موافقة الإدارة قبل إرسال طلب جديد."
ACTIVE_PLAN_SUBSCRIPTION_MESSAGE = "لديك باقة مفعّلة حالياً. لا يمكنك إرسال طلب اشتراك جديد قبل انتهاء أو حذف الاشتراك الحالي."
MAX_VERIFICATION_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DEPOSIT_PROOF_SIZE = 5 * 1024 * 1024
DOCUMENT_TYPES = {
    "id_card": "بطاقة شخصية",
    "driver_license": "رخصة قيادة",
    "passport": "جواز سفر",
}
IMAGE_SIGNATURES = (
    b"\xff\xd8\xff",
    b"\x89PNG\r\n\x1a\n",
    b"GIF87a",
    b"GIF89a",
    b"RIFF",
    b"BM",
)


def ensure_no_pending_request(db: Session, user: User, request_type: str, message: str) -> None:
    db.query(User).filter(User.id == user.id).with_for_update().first()
    existing_pending = (
        db.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.id,
            PendingRequest.request_type == request_type,
            PendingRequest.status == "pending",
        )
        .with_for_update()
        .first()
    )
    if existing_pending:
        raise ValueError(message)


def parse_withdrawal_amount(value: str | Decimal | int | float | None) -> Decimal:
    try:
        amount = Decimal(str(value or "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError("يرجى إدخال مبلغ سحب صحيح.")

    if amount <= 0:
        raise ValueError("يجب أن يكون مبلغ السحب أكبر من 0.")
    return amount.quantize(Decimal("0.01"))


def make_referral_code() -> str:
    return uuid4().hex[:10]


def get_referral_url(request: Request, user: User) -> str:
    code = user.referral_code or ""
    return str(request.url_for("user_register")) + f"?ref={code}"


def build_register_context(request: Request, ref: str = "", error: str | None = None, selected_country: str = "") -> dict:
    return {
        "request": request,
        "error": error,
        "ref": ref,
        "countries": COUNTRY_TIMEZONE_CHOICES,
        "selected_country": selected_country,
        "platform_name": PLATFORM_NAME,
        "platform_tagline": PLATFORM_TAGLINE,
    }


def build_user_context(request: Request, user: User, active_user_page: str, db: Session) -> dict:
    withdraw_percent = min(100, int((Decimal(user.profits or 0) / MIN_WITHDRAWAL) * 100))
    financial_state = build_user_financial_state(user, db)
    withdrawal_cycle = financial_state["withdrawal_cycle"]
    mining_status = financial_state["mining_status"]
    referrals_count = financial_state["referrals_count"]
    rank_info = financial_state["referral_rank_info"]
    referral_url = get_referral_url(request, user)
    referral_share = build_referral_share_context(referral_url)
    next_rank_target = referrals_count + int(rank_info.get("remaining") or 0)
    rank_progress_percent = 100 if not rank_info.get("next_rank") else min(100, int((referrals_count / max(1, next_rank_target)) * 100))
    return {
        "request": request,
        "user": user,
        "platform_name": PLATFORM_NAME,
        "platform_tagline": PLATFORM_TAGLINE,
        "active_user_page": active_user_page,
        "format_datetime_for_timezone": format_datetime_for_timezone,
        "progress_percent": mining_status["progress_percent"],
        "can_start": mining_status["can_start"],
        "mining_status": mining_status,
        "financial_state": financial_state,
        "withdraw_percent": withdraw_percent,
        "min_withdrawal": MIN_WITHDRAWAL,
        **withdrawal_cycle,
        "referral_url": referral_url,
        "invite_message": referral_share["invite_message"],
        "whatsapp_share_url": referral_share["whatsapp_share_url"],
        "telegram_share_url": referral_share["telegram_share_url"],
        "facebook_share_url": referral_share["facebook_share_url"],
        "referrals_count": referrals_count,
        "referral_rank_info": rank_info,
        "rank_progress_percent": rank_progress_percent,
        "total_referral_earnings": financial_state["total_referral_earnings"],
        "user_is_verified": bool(user.verified),
        "verification_status": user.verification_status,
        "maintenance_enabled": is_maintenance_enabled(db),
        "user_notification_modal": request.session.pop("user_notification_modal", None),
        **get_user_notifications_context(db, user.id),
    }


def wants_json_response(request: Request) -> bool:
    return (
        request.headers.get("x-requested-with") == "fetch"
        or "application/json" in request.headers.get("accept", "")
    )


def decimal_display(value: Decimal | int | str | None, places: int = 4) -> str:
    return f"{Decimal(value or 0):.{places}f}"


REQUEST_HISTORY_TYPES = ("plan_subscription", "withdraw", "verification", "deposit")
REQUEST_TYPE_LABELS = {
    "plan_subscription": "Plan Subscription",
    "withdraw": "Withdrawal",
    "verification": "Verification",
    "deposit": "Legacy Deposit",
}
REQUEST_STATUS_LABELS = {
    "pending": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
}


def pending_request_details(request_item: PendingRequest) -> dict[str, str]:
    if not request_item.details_json:
        return {}
    try:
        data = json.loads(request_item.details_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def detail_value(details: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = details.get(key)
        if value:
            return value
    return ""


def detail_datetime(details: dict[str, str], *keys: str) -> datetime | None:
    value = detail_value(details, *keys)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def serialize_user_request_history_item(request_item: PendingRequest) -> dict:
    details = pending_request_details(request_item)
    request_type = request_item.request_type
    status = (request_item.status or "pending").lower()
    amount_label = f"{Decimal(request_item.amount or 0):.2f} USDT" if request_item.amount is not None else "-"
    plan_name = detail_value(details, "Activated plan", "Final plan", "الباقة النهائية", "الباقة المختارة", "الباقة")
    wallet = detail_value(details, "Wallet address", "عنوان المحفظة")
    network = detail_value(details, "Network", "Payment network", "شبكة التحويل", "الشبكة")
    rejection_reason = detail_value(details, "rejection_reason", "Rejection reason", "Reason", "سبب الرفض")
    rejected_at = detail_datetime(details, "rejected_at", "Rejected at", "تاريخ الرفض")

    if request_type in {"plan_subscription", "deposit"}:
        primary = plan_name or REQUEST_TYPE_LABELS.get(request_type, request_type)
        secondary = amount_label
    elif request_type == "withdraw":
        primary = amount_label
        secondary = network or "Withdrawal request"
    elif request_type == "verification":
        primary = request_item.document_type_label
        secondary = request_item.legal_full_name or request_item.full_name or "Account verification"
        amount_label = "-"
    else:
        primary = REQUEST_TYPE_LABELS.get(request_type, request_type.replace("_", " ").title())
        secondary = amount_label

    visible_details = []
    if plan_name and request_type in {"plan_subscription", "deposit", "withdraw"}:
        visible_details.append({"label": "Plan", "value": plan_name})
    if wallet:
        visible_details.append({"label": "Wallet", "value": wallet})
    if network:
        visible_details.append({"label": "Network", "value": network})
    if request_type == "verification" and request_item.legal_full_name:
        visible_details.append({"label": "Full name", "value": request_item.legal_full_name})
    if status == "rejected":
        visible_details.append(
            {
                "label": "Rejection reason",
                "value": rejection_reason or "No rejection reason was provided.",
            }
        )

    return {
        "id": request_item.id,
        "request_type": request_type,
        "type_label": REQUEST_TYPE_LABELS.get(request_type, request_type.replace("_", " ").title()),
        "status": status,
        "status_label": REQUEST_STATUS_LABELS.get(status, status.title()),
        "amount_label": amount_label,
        "plan_name": plan_name or "-",
        "primary": primary,
        "secondary": secondary,
        "submitted_at": request_item.created_at,
        "updated_at": request_item.updated_at,
        "details": visible_details,
        "rejection_reason": rejection_reason,
        "rejected_at": rejected_at or (request_item.updated_at if status == "rejected" else None),
    }


def serialize_mining_status(status: dict, completed_cycle=None) -> dict:
    timezone_name = status["timezone"]
    if completed_cycle is not None:
        completed_window_start = completed_cycle.cycle_window_start or completed_cycle.start_at
        completed_window_end = completed_cycle.cycle_window_end or completed_cycle.end_at
        completed_actual_start = completed_cycle.actual_start_time or completed_cycle.start_at
        duration_seconds = status["duration_seconds"]
        earning_ratio = cycle_earning_ratio(completed_cycle)
        active_seconds = completed_cycle.active_seconds or int(Decimal(duration_seconds) * earning_ratio)
        missed_seconds = completed_cycle.missed_seconds or max(0, duration_seconds - active_seconds)
        full_daily_income = completed_cycle.full_daily_income or completed_cycle.final_income or Decimal("0")
        completed_income = completed_cycle.final_income_after_time_deduction or completed_cycle.final_income or Decimal("0")
        return {
            "cycle_id": completed_cycle.cycle_uuid,
            "status": "completed",
            "can_start": status["can_start"],
            "progress_percent": 100,
            "remaining_seconds": 0,
            "duration_seconds": duration_seconds,
            "start_time": format_datetime_for_timezone(completed_window_start, timezone_name),
            "cycle_window_start": format_datetime_for_timezone(completed_window_start, timezone_name),
            "actual_start_time": format_datetime_for_timezone(completed_actual_start, timezone_name),
            "end_time": format_datetime_for_timezone(completed_window_end, timezone_name),
            "cycle_window_end": format_datetime_for_timezone(completed_window_end, timezone_name),
            "start_time_iso": completed_window_start.replace(tzinfo=None).isoformat() + "Z",
            "cycle_window_start_iso": completed_window_start.replace(tzinfo=None).isoformat() + "Z",
            "actual_start_time_iso": completed_actual_start.replace(tzinfo=None).isoformat() + "Z",
            "end_time_iso": completed_window_end.replace(tzinfo=None).isoformat() + "Z",
            "cycle_window_end_iso": completed_window_end.replace(tzinfo=None).isoformat() + "Z",
            "active_seconds": active_seconds,
            "missed_seconds": missed_seconds,
            "earning_ratio": str(earning_ratio),
            "timezone": timezone_name,
            "active_capital": str(completed_cycle.active_capital),
            "referral_income": str(completed_cycle.referral_income),
            "current_daily_income": str(full_daily_income),
            "full_daily_income": str(full_daily_income),
            "expected_earned_income": str(completed_income),
            "current_total_balance": decimal_display(status.get("current_total_balance"), 8),
            "live_earned_income": "0.00000000",
            "live_available_yield": decimal_display(status.get("current_total_balance"), 8),
            "status_at_iso": status.get("status_at_iso", ""),
            "completed": True,
            "completed_income": str(completed_income),
        }

    return {
        "cycle_id": status["cycle_id"],
        "status": status["status"],
        "can_start": status["can_start"],
        "progress_percent": status["progress_percent"],
        "remaining_seconds": status["remaining_seconds"],
        "duration_seconds": status["duration_seconds"],
        "start_time": status["start_time"],
        "cycle_window_start": status["start_time"],
        "actual_start_time": status["actual_start_time"],
        "end_time": status["end_time"],
        "cycle_window_end": status["end_time"],
        "start_time_iso": status["start_time_iso"],
        "cycle_window_start_iso": status["start_time_iso"],
        "actual_start_time_iso": status["actual_start_time_iso"],
        "end_time_iso": status["end_time_iso"],
        "cycle_window_end_iso": status["end_time_iso"],
        "active_seconds": status["active_seconds"],
        "missed_seconds": status["missed_seconds"],
        "earning_ratio": str(status["earning_ratio"]),
        "timezone": status["timezone"],
        "active_capital": str(status["active_capital"]),
        "referral_income": str(status["referral_income"]),
        "current_daily_income": str(status["current_daily_income"]),
        "full_daily_income": str(status["full_daily_income"]),
        "expected_earned_income": str(status["expected_earned_income"]),
        "current_total_balance": decimal_display(status.get("current_total_balance"), 8),
        "live_earned_income": decimal_display(status.get("live_earned_income"), 8),
        "live_available_yield": decimal_display(status.get("live_available_yield"), 8),
        "status_at_iso": status.get("status_at_iso", ""),
        "completed": False,
        "completed_income": "0.0000",
    }


def get_support_notification_message(support_message) -> str:
    if support_message.has_attachment_data:
        return "صورة" if support_message.is_image else "ملف"
    return support_message.body or "رسالة جديدة"


def serialize_user_support_message(message, thread) -> dict:
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


def get_user_poll_messages(db: Session, user: User, thread_id: int | None) -> list[dict]:
    thread = get_or_create_support_thread(db, user)
    if thread_id and thread.id != thread_id:
        return []
    return [serialize_user_support_message(message, thread) for message in get_thread_messages(db, thread)]


def get_user_display_name(user: User) -> str:
    return user.username or user.name or user.email


def get_safe_user_redirect(request: Request, fallback: str = "/user/dashboard") -> str:
    referer = request.headers.get("referer", "")
    if not referer:
        return fallback

    parsed = urlsplit(referer)
    if parsed.path.startswith("/user/"):
        return parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return fallback


def read_verification_image(upload: UploadFile | None, label: str) -> dict[str, object]:
    if not upload or not upload.filename:
        raise ValueError(f"يرجى رفع {label}.")

    content_type = (upload.content_type or "application/octet-stream").lower()
    if not content_type.startswith("image/"):
        raise ValueError(f"{label} يجب أن تكون صورة.")

    upload.file.seek(0)
    content = upload.file.read()
    size = len(content)
    if size <= 0:
        raise ValueError(f"{label} فارغة ولا يمكن رفعها.")
    if size > MAX_VERIFICATION_IMAGE_SIZE:
        raise ValueError(f"{label} أكبر من الحد المسموح 5MB.")
    if not is_supported_image_content(content, content_type):
        raise ValueError(f"{label} يجب أن تكون صورة بصيغة مدعومة.")

    return {
        "data": content,
        "mime_type": content_type,
        "size": size,
    }


def is_supported_image_content(content: bytes, content_type: str) -> bool:
    if not content_type.startswith("image/"):
        return False
    if content.startswith(b"RIFF") and b"WEBP" not in content[:16]:
        return False
    return any(content.startswith(signature) for signature in IMAGE_SIGNATURES)


def read_deposit_proof_image(upload: UploadFile | None) -> dict[str, object]:
    if not upload or not upload.filename:
        raise ValueError("يرجى رفع صورة إثبات التحويل.")

    content_type = (upload.content_type or "application/octet-stream").lower()
    if not content_type.startswith("image/"):
        raise ValueError("ملف إثبات التحويل يجب أن يكون صورة.")

    upload.file.seek(0)
    content = upload.file.read()
    size = len(content)
    if size <= 0:
        raise ValueError("صورة إثبات التحويل فارغة ولا يمكن رفعها.")
    if size > MAX_DEPOSIT_PROOF_SIZE:
        raise ValueError("صورة إثبات التحويل أكبر من الحد المسموح 5MB.")
    if not is_supported_image_content(content, content_type):
        raise ValueError("ملف إثبات التحويل يجب أن يكون صورة بصيغة مدعومة.")

    return {
        "data": content,
        "mime_type": content_type,
        "size": size,
    }


@router.get("/register", response_class=HTMLResponse, name="user_register")
def register_page(request: Request, ref: str = ""):
    return templates.TemplateResponse("user_register.html", build_register_context(request, ref=ref))


@router.post("/register")
def register(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    confirm_password: str = Form(""),
    residence_country: str = Form(""),
    ref: str = Form(""),
    db: Session = Depends(get_db),
):
    username = username.strip().lower()
    clean_country = residence_country.strip()
    timezone = get_country_timezone(clean_country)
    generated_email = f"{username}@novahash.local"

    if not username or any(char.isspace() for char in username):
        return templates.TemplateResponse(
            "user_register.html",
            build_register_context(request, ref=ref, error="يرجى إدخال اسم مستخدم صحيح بدون مسافات.", selected_country=clean_country),
            status_code=400,
        )
    if not password:
        return templates.TemplateResponse(
            "user_register.html",
            build_register_context(request, ref=ref, error="يرجى إدخال كلمة المرور.", selected_country=clean_country),
            status_code=400,
        )
    if password != confirm_password:
        return templates.TemplateResponse(
            "user_register.html",
            build_register_context(request, ref=ref, error="كلمة المرور وتأكيد كلمة المرور غير متطابقين.", selected_country=clean_country),
            status_code=400,
        )
    if not timezone:
        return templates.TemplateResponse(
            "user_register.html",
            build_register_context(request, ref=ref, error="يرجى اختيار مكان الإقامة من القائمة.", selected_country=clean_country),
            status_code=400,
        )

    existing = db.query(User).filter(or_(User.username == username, User.email == generated_email)).first()
    if existing:
        return templates.TemplateResponse(
            "user_register.html",
            build_register_context(request, ref=ref, error="اسم المستخدم مستخدم مسبقاً.", selected_country=clean_country),
            status_code=400,
        )

    referrer = db.query(User).filter(User.referral_code == ref).first() if ref else None
    user = User(
        name=username,
        username=username,
        email=generated_email,
        password_hash=hash_password(password),
        residence_country=clean_country,
        timezone=timezone,
        referral_code=make_referral_code(),
        referred_by_id=referrer.id if referrer else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_admin_notification(
        db,
        title="إنشاء حساب جديد",
        message=f"قام {user.name} بإنشاء حساب جديد.",
        target_url=f"/users/{user.id}",
        kind="account",
        data={
            "اسم المستخدم": user.username or "-",
            "مكان الإقامة": user.residence_country or "-",
            "المنطقة الزمنية": user.timezone or "UTC",
            "كلمة السر": "محفوظة كـ hash ولا يتم عرضها كنص صريح",
            "كود الإحالة": user.referral_code or "-",
            "كود الدعوة المستخدم": ref.strip() or "-",
            "المحيل": referrer.username if referrer else "-",
        },
    )
    db.commit()
    request.session["user_id"] = user.id
    request.session.pop("user_intro_seen", None)
    return RedirectResponse(url="/user/dashboard", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/user/dashboard", status_code=303)
    return templates.TemplateResponse(
        "user_login.html",
        {"request": request, "error": None, "platform_name": PLATFORM_NAME, "platform_tagline": PLATFORM_TAGLINE},
    )


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    login_value = username.strip().lower()
    user = db.query(User).filter(User.username == login_value, User.status == "active").first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "user_login.html",
            {"request": request, "error": "بيانات الدخول غير صحيحة.", "platform_name": PLATFORM_NAME, "platform_tagline": PLATFORM_TAGLINE},
            status_code=401,
        )

    request.session["user_id"] = user.id
    request.session.pop("user_intro_seen", None)
    return RedirectResponse(url="/user/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.pop("user_id", None)
    request.session.pop("user_intro_seen", None)
    return RedirectResponse(url="/user/login", status_code=303)


@router.get("/notifications/{notification_id}/open")
def open_user_notification(
    notification_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_type == "user",
            Notification.recipient_user_id == user.id,
        )
        .first()
    )
    if not notification:
        return RedirectResponse(url="/user/dashboard", status_code=303)

    notification.is_read = True
    if notification.is_user_modal_notification:
        request.session["user_notification_modal"] = {
            "title": notification.display_title,
            "message": notification.display_message,
            "subtitle": notification.modal_subtitle,
        }
        target_url = get_safe_user_redirect(request)
    else:
        target_url = notification.target_url or "/user/dashboard"
    db.commit()
    return RedirectResponse(url=target_url, status_code=303)


@router.post("/notifications/clear")
def clear_user_notifications(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    (
        db.query(Notification)
        .filter(
            Notification.recipient_type == "user",
            Notification.recipient_user_id == user.id,
            Notification.is_read.is_(False),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    if wants_json_response(request):
        return JSONResponse(
            build_notifications_poll_payload(
                db,
                recipient_type="user",
                recipient_user_id=user.id,
                open_prefix="/user/notifications",
            )
        )
    return RedirectResponse(url="/user/dashboard", status_code=303)


@router.get("/notifications/poll")
def user_notifications_poll(
    thread_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JSONResponse(
        build_notifications_poll_payload(
            db,
            recipient_type="user",
            recipient_user_id=user.id,
            open_prefix="/user/notifications",
            messages=get_user_poll_messages(db, user, thread_id),
        )
    )


@router.get("/support/messages")
def user_support_messages(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = get_or_create_support_thread(db, user)
    return JSONResponse(
        {
            "ok": True,
            "thread_id": thread.id,
            "messages": [serialize_user_support_message(item, thread) for item in get_thread_messages(db, thread)],
        }
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    completed_cycle = settle_due_mining_cycle(user, db)
    intro_seen = bool(request.session.get("user_intro_seen"))
    request.session["user_intro_seen"] = True
    context = build_user_context(request, user, "dashboard", db)
    return templates.TemplateResponse(
        "user_dashboard.html",
        {
            "intro_seen": intro_seen,
            "mining_completed_cycle": completed_cycle,
            "cycle_started": request.query_params.get("cycle_started") == "1",
            "mining_error": request.query_params.get("mining_error", ""),
            **context,
        },
    )


@router.get("/plans", response_class=HTMLResponse)
def plans_page(
    request: Request,
    plan_request_error: str = "",
    plan_request_sent: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settle_due_mining_cycle(user, db)
    has_active_plan = bool(user.plan and user.plan.lower() != "none")
    has_pending_plan_subscription = (
        db.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.id,
            PendingRequest.request_type == "plan_subscription",
            PendingRequest.status == "pending",
        )
        .first()
        is not None
    )
    plan_subscription_block_message = ""
    if has_active_plan:
        plan_subscription_block_message = ACTIVE_PLAN_SUBSCRIPTION_MESSAGE
    elif has_pending_plan_subscription:
        plan_subscription_block_message = PENDING_PLAN_SUBSCRIPTION_MESSAGE

    context = build_user_context(request, user, "plans", db)
    context.update(
        {
            "plan_request_error": plan_request_error,
            "plan_request_sent": plan_request_sent == "1",
            "deposit_wallet_address": app_settings.usdt_wallet_address,
            "min_deposit_amount": MIN_DEPOSIT_AMOUNT,
            "has_active_plan": has_active_plan,
            "has_pending_plan_subscription": has_pending_plan_subscription,
            "can_submit_plan_subscription": not has_active_plan and not has_pending_plan_subscription,
            "plan_subscription_block_message": plan_subscription_block_message,
        }
    )
    return templates.TemplateResponse("user_plans.html", context)


@router.post("/plans/subscribe")
def submit_plan_subscription_request(
    selected_plan: str = Form(""),
    amount: str = Form(""),
    network: str = Form("TRC20"),
    proof: UploadFile = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selected_plan = selected_plan.strip().lower()
    if selected_plan not in {"silver", "gold", "vip"}:
        return RedirectResponse(
            url=f"/user/plans?{urlencode({'plan_request_error': 'الباقة غير صحيحة.'})}",
            status_code=303,
        )

    try:
        ensure_no_pending_request(db, user, "plan_subscription", PENDING_PLAN_SUBSCRIPTION_MESSAGE)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/user/plans?{urlencode({'plan_request_error': str(exc)})}",
            status_code=303,
        )

    if user.plan and user.plan.lower() != "none":
        return RedirectResponse(
            url=f"/user/plans?{urlencode({'plan_request_error': ACTIVE_PLAN_SUBSCRIPTION_MESSAGE})}",
            status_code=303,
        )

    try:
        user_amount = Decimal(str(amount or "").strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return RedirectResponse(
            url=f"/user/plans?{urlencode({'plan_request_error': 'يرجى إدخال مبلغ صحيح.'})}",
            status_code=303,
        )

    is_valid_amount, amount_error = validate_amount_for_plan(selected_plan, user_amount)
    if not is_valid_amount:
        matching_plan = determine_plan_for_amount(user_amount)
        plan_rank = {"silver": 1, "gold": 2, "vip": 3}
        if plan_rank.get(matching_plan, 0) > plan_rank.get(selected_plan, 0):
            matching_label = {
                "silver": "الباقة الفضية",
                "gold": "الباقة الذهبية",
                "vip": "باقة VIP",
            }.get(matching_plan, plan_label(matching_plan))
            amount_error = (
                f"المبلغ الذي أدخلته يقع ضمن حدود {matching_label}. "
                f"يرجى اختيار {matching_label} قبل إرسال الطلب."
            )
        return RedirectResponse(
            url=f"/user/plans?{urlencode({'plan_request_error': amount_error})}",
            status_code=303,
        )

    if network.strip().upper() != "TRC20":
        return RedirectResponse(
            url=f"/user/plans?{urlencode({'plan_request_error': 'الشبكة يجب أن تكون TRC20 فقط.'})}",
            status_code=303,
        )

    try:
        proof_data = read_deposit_proof_image(proof)
    except ValueError as e:
        return RedirectResponse(
            url=f"/user/plans?{urlencode({'plan_request_error': str(e)})}",
            status_code=303,
        )

    pending_request = PendingRequest(
        user_id=user.id,
        request_type="plan_subscription",
        amount=user_amount,
        status="pending",
        full_name=user.username or user.name,
        timezone=user.timezone or "UTC",
        front_image_data=proof_data["data"],
        front_image_mime_type=proof_data["mime_type"],
        front_image_size=proof_data["size"],
        details_json=json.dumps(
            {
                "اسم المستخدم": get_user_display_name(user),
                "الباقة المختارة": plan_label(selected_plan),
                "المبلغ": f"{user_amount:.2f} USDT",
                "شبكة التحويل": "TRC20",
                "عنوان المحفظة": app_settings.usdt_wallet_address,
            },
            ensure_ascii=False,
        ),
    )

    db.add(pending_request)
    create_admin_notification(
        db,
        title="طلب اشتراك جديد",
        message=f"طلب اشتراك بقيمة {user_amount:.2f} USDT من {get_user_display_name(user)}",
        target_url="/notifications#pending-plan_subscription",
        kind="plan_subscription",
        data={
            "User": get_user_display_name(user),
            "Amount": f"{user_amount:.2f} USDT",
            "Selected plan": plan_label(selected_plan),
            "Wallet address": app_settings.usdt_wallet_address,
            "Payment network": "TRC20",
        },
    )
    db.commit()
    return RedirectResponse(url="/user/plans?plan_request_sent=1", status_code=303)


@router.get("/withdraw", response_class=HTMLResponse)
def withdraw_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_due_mining_cycle(user, db)
    return templates.TemplateResponse("user_withdraw.html", build_user_context(request, user, "withdraw", db))


@router.post("/withdraw/profits")
def submit_profit_withdrawal_request(
    request: Request,
    amount: str = Form(""),
    wallet_address: str = Form(""),
    network: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settle_due_mining_cycle(user, db)
    clean_wallet = wallet_address.strip()
    clean_network = network.strip()

    try:
        clean_amount = parse_withdrawal_amount(amount)
        if not user.verified:
            raise ValueError("لا يمكنك سحب الأرباح قبل توثيق الحساب.")
        withdrawal_cycle = build_withdrawal_cycle_status(user, db)
        if not withdrawal_cycle["withdrawal_cycle_days"]:
            raise ValueError("لا توجد باقة فعالة تسمح بسحب الأرباح.")
        if withdrawal_cycle["withdrawal_remaining_seconds"] > 0 and not withdrawal_cycle["manual_withdrawal_unlock"]:
            raise ValueError("دورة السحب لم تنتهِ بعد.")
        if Decimal(user.profits or 0) <= 0:
            raise ValueError("لا توجد أرباح متاحة للسحب.")
        if clean_amount > Decimal(user.profits or 0):
            raise ValueError("المبلغ المطلوب يتجاوز الأرباح المتاحة للسحب.")
        if not clean_wallet:
            raise ValueError("يرجى إدخال عنوان المحفظة.")
        if not clean_network:
            raise ValueError("يرجى إدخال الشبكة.")
        ensure_no_pending_request(db, user, "withdraw", "لديك طلب سحب أرباح قيد المراجعة بالفعل.")
    except ValueError as exc:
        if wants_json_response(request):
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return RedirectResponse(url=f"/user/withdraw?{urlencode({'withdraw_error': str(exc)})}", status_code=303)

    pending_request = PendingRequest(
        user_id=user.id,
        request_type="withdraw",
        amount=clean_amount,
        status="pending",
        full_name=user.username or user.name,
        timezone=user.timezone or "UTC",
        details_json=json.dumps(
            {
                "نوع الطلب": "سحب أرباح",
                "اسم المستخدم": get_user_display_name(user),
                "المبلغ": f"{clean_amount:.2f} USDT",
                "عنوان المحفظة": clean_wallet,
                "الشبكة": clean_network,
                "الباقة": plan_label(user.plan),
            },
            ensure_ascii=False,
        ),
    )
    if user.manual_withdrawal_unlock:
        user.manual_withdrawal_unlock = False
        db.add(user)
    db.add(pending_request)
    create_admin_notification(
        db,
        title="طلب سحب أرباح جديد",
        message=f"طلب سحب أرباح جديد من {get_user_display_name(user)} بقيمة {clean_amount:.2f}.",
        target_url="/notifications#pending-withdraw",
        kind="withdraw",
        data={
            "User": get_user_display_name(user),
            "Amount": f"{clean_amount:.2f} USDT",
            "Wallet address": clean_wallet,
            "Network": clean_network,
            "Status": "pending",
        },
    )
    db.commit()

    if wants_json_response(request):
        return JSONResponse(
            {
                "ok": True,
                "message": "تم إرسال طلب السحب بنجاح وسيتم مراجعته من الإدارة.",
            }
        )
    return RedirectResponse(url="/user/withdraw?withdraw_sent=1", status_code=303)


@router.get("/referral", response_class=HTMLResponse)
def referral_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_due_mining_cycle(user, db)
    return templates.TemplateResponse("user_referral.html", build_user_context(request, user, "referral", db))


@router.get("/guide", response_class=HTMLResponse)
def guide_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_due_mining_cycle(user, db)
    return templates.TemplateResponse("user_guide.html", build_user_context(request, user, "guide", db))


@router.get("/support", response_class=HTMLResponse)
def support_page(
    request: Request,
    chat: str = "",
    locked: str = "",
    error: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settle_due_mining_cycle(user, db)
    thread = get_or_create_support_thread(db, user)
    messages = get_thread_messages(db, thread)
    context = build_user_context(request, user, "support", db)
    context.update(
        {
            "support_thread": thread,
            "support_messages": messages,
            "support_chat_mode": "user",
            "support_chat_open": chat == "open",
            "support_chat_post_url": "/user/support/messages",
            "support_chat_title": "مراسلة الدعم",
            "support_chat_subtitle": "اكتب رسالتك وارفق صورة أو ملفاً عند الحاجة.",
            "can_user_send_support": can_user_send_support_message(db, thread),
            "support_waiting_message": bool(locked),
            "support_chat_error": error,
        }
    )
    return templates.TemplateResponse("user_support.html", context)


@router.post("/support/messages")
def send_support_message(
    request: Request,
    message: str = Form(""),
    attachment: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thread = get_or_create_support_thread(db, user)
    if not can_user_send_support_message(db, thread):
        if request.headers.get("x-requested-with") == "fetch":
            return JSONResponse({"ok": False, "error": "Please wait for support to reply before sending another message."}, status_code=409)
        return RedirectResponse(url="/user/support?chat=open&locked=1", status_code=303)

    try:
        support_message = add_support_message(
            db,
            thread=thread,
            sender_type="user",
            body=message,
            attachment=attachment,
        )
    except SupportAttachmentError as exc:
        if request.headers.get("x-requested-with") == "fetch":
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return RedirectResponse(url=f"/user/support?chat=open&{urlencode({'error': str(exc)})}", status_code=303)
    if support_message:
        create_admin_notification(
            db,
            title=user.username or user.name,
            message=get_support_notification_message(support_message),
            target_url=f"/support/chat/{thread.id}",
            kind="support",
        )
        db.commit()
        db.refresh(support_message)
        if request.headers.get("x-requested-with") == "fetch":
            messages = [serialize_user_support_message(item, thread) for item in get_thread_messages(db, thread)]
            return JSONResponse(
                {
                    "ok": True,
                    "message": serialize_user_support_message(support_message, thread),
                    "messages": messages,
                }
            )
    elif request.headers.get("x-requested-with") == "fetch":
        return JSONResponse({"ok": False, "error": "Message is empty."}, status_code=400)

    return RedirectResponse(url="/user/support?chat=open", status_code=303)


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_due_mining_cycle(user, db)
    context = build_user_context(request, user, "history", db)
    context["records"] = db.query(Record).filter(Record.user_id == user.id).order_by(Record.created_at.desc()).all()
    request_items = (
        db.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.id,
            PendingRequest.request_type.in_(REQUEST_HISTORY_TYPES),
        )
        .order_by(PendingRequest.created_at.desc(), PendingRequest.id.desc())
        .all()
    )
    request_history = [serialize_user_request_history_item(item) for item in request_items]
    context["request_history"] = request_history
    context["request_history_counts"] = {
        "total": len(request_history),
        "pending": sum(1 for item in request_history if item["status"] == "pending"),
        "approved": sum(1 for item in request_history if item["status"] == "approved"),
        "rejected": sum(1 for item in request_history if item["status"] == "rejected"),
    }
    return templates.TemplateResponse("user_history.html", context)


@router.get("/account", response_class=HTMLResponse)
def account_page(
    request: Request,
    verification_error: str = "",
    verification_sent: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settle_due_mining_cycle(user, db)
    has_pending_verification = (
        db.query(PendingRequest)
        .filter(
            PendingRequest.user_id == user.id,
            PendingRequest.request_type == "verification",
            PendingRequest.status == "pending",
        )
        .first()
        is not None
    )
    if user.verified:
        verification_state = "verified"
    elif has_pending_verification or user.verification_status == "pending":
        verification_state = "pending"
    else:
        verification_state = "action_required"
    context = build_user_context(request, user, "account", db)
    context.update(
        {
            "verification_error": verification_error,
            "verification_sent": verification_sent == "1",
            "verification_state": verification_state,
            "can_submit_verification": verification_state == "action_required",
            "has_pending_verification": verification_state == "pending",
            "security_error": request.query_params.get("security_error", ""),
            "security_success": request.query_params.get("security_success", "") == "1",
            "profile_error": request.query_params.get("profile_error", ""),
            "profile_success": request.query_params.get("profile_success", "") == "1",
            "document_types": DOCUMENT_TYPES,
            "countries": COUNTRY_TIMEZONE_CHOICES,
        }
    )
    return templates.TemplateResponse("user_account.html", context)


@router.post("/account/security")
def update_account_security(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        return RedirectResponse(
            url=f"/user/account?security_error=كلمة المرور الحالية غير صحيحة.",
            status_code=303,
        )

    if new_password != confirm_password:
        return RedirectResponse(
            url=f"/user/account?security_error=كلمة المرور الجديدة وتأكيدها غير متطابقين.",
            status_code=303,
        )

    if len(new_password) < 8:
        return RedirectResponse(
            url=f"/user/account?security_error=يجب أن تكون كلمة المرور الجديدة 8 أحرف على الأقل.",
            status_code=303,
        )

    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()

    return RedirectResponse(url="/user/account?security_success=1", status_code=303)


@router.post("/account/profile")
def update_account_profile(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    clean_name = name.strip()
    clean_username = username.strip().lower()
    clean_email = email.strip().lower()

    if not clean_name:
        return RedirectResponse(
            url=f"/user/account?profile_error=يرجى إدخال اسم صحيح.",
            status_code=303,
        )

    if not clean_username or any(char.isspace() for char in clean_username):
        return RedirectResponse(
            url=f"/user/account?profile_error=يرجى إدخال اسم مستخدم صالح بدون مسافات.",
            status_code=303,
        )

    if not clean_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        return RedirectResponse(
            url=f"/user/account?profile_error=يرجى إدخال بريد إلكتروني صالح.",
            status_code=303,
        )

    existing_user = db.query(User).filter(User.username == clean_username, User.id != user.id).first()
    if existing_user:
        return RedirectResponse(
            url=f"/user/account?profile_error=اسم المستخدم هذا مستخدم بالفعل.",
            status_code=303,
        )

    existing_email = db.query(User).filter(User.email == clean_email, User.id != user.id).first()
    if existing_email:
        return RedirectResponse(
            url=f"/user/account?profile_error=هذا البريد الإلكتروني مستخدم بالفعل.",
            status_code=303,
        )

    user.name = clean_name
    user.username = clean_username
    user.email = clean_email

    db.add(user)
    db.commit()

    return RedirectResponse(url="/user/account?profile_success=1", status_code=303)


@router.post("/account/verification")
def submit_account_verification(
    legal_full_name: str = Form(...),
    document_type: str = Form(...),
    front_image: UploadFile | None = File(None),
    back_image: UploadFile | None = File(None),
    passport_image: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.verified:
        return RedirectResponse(
            url=f"/user/account?{urlencode({'verification_error': 'حسابك موثق بالفعل ولا يحتاج إلى طلب توثيق جديد.'})}",
            status_code=303,
        )

    try:
        ensure_no_pending_request(db, user, "verification", "طلب التوثيق قيد المراجعة بالفعل.")
    except ValueError as exc:
        return RedirectResponse(
            url=f"/user/account?{urlencode({'verification_error': str(exc)})}",
            status_code=303,
        )

    if user.verification_status == "pending":
        return RedirectResponse(
            url=f"/user/account?{urlencode({'verification_error': 'طلب التوثيق قيد المراجعة بالفعل.'})}",
            status_code=303,
        )

    clean_name = legal_full_name.strip()
    clean_country = (user.residence_country or "").strip()
    timezone = user.timezone or get_country_timezone(clean_country) or "UTC"

    try:
        if not clean_name:
            raise ValueError("يرجى كتابة الاسم والكنية كما في البطاقة الشخصية.")
        if document_type not in DOCUMENT_TYPES:
            raise ValueError("يرجى اختيار نوع وثيقة صحيح.")

        front_data = back_data = passport_data = None
        if document_type in {"id_card", "driver_license"}:
            front_data = read_verification_image(front_image, "صورة الوجه الأمامي")
            back_data = read_verification_image(back_image, "صورة الوجه الخلفي")
        else:
            passport_data = read_verification_image(passport_image, "صورة جواز السفر")
    except ValueError as exc:
        return RedirectResponse(url=f"/user/account?{urlencode({'verification_error': str(exc)})}", status_code=303)

    now = datetime.utcnow()
    user.legal_full_name = clean_name
    user.timezone = timezone
    user.document_type = document_type
    user.verification_status = "pending"
    user.verified = False
    user.verification_requested_at = now

    pending_request = PendingRequest(
        user_id=user.id,
        request_type="verification",
        status="pending",
        full_name=clean_name,
        legal_full_name=clean_name,
        country=clean_country,
        timezone=timezone,
        document_type=document_type,
        details_json=json.dumps(
            {
                "نوع الوثيقة": DOCUMENT_TYPES[document_type],
            },
            ensure_ascii=False,
        ),
    )
    if front_data:
        pending_request.front_image_data = front_data["data"]
        pending_request.front_image_mime_type = front_data["mime_type"]
        pending_request.front_image_size = front_data["size"]
    if back_data:
        pending_request.back_image_data = back_data["data"]
        pending_request.back_image_mime_type = back_data["mime_type"]
        pending_request.back_image_size = back_data["size"]
    if passport_data:
        pending_request.passport_image_data = passport_data["data"]
        pending_request.passport_image_mime_type = passport_data["mime_type"]
        pending_request.passport_image_size = passport_data["size"]

    db.add(pending_request)
    db.add(user)
    create_admin_notification(
        db,
        title="New verification request",
        message=f"New verification request from {get_user_display_name(user)}",
        target_url="/notifications#pending-verification",
        kind="verification",
        data={
            "User": get_user_display_name(user),
            "Email": user.email,
            "Full name": clean_name,
            "Country": clean_country,
            "Timezone": timezone,
            "Document type": DOCUMENT_TYPES[document_type],
        },
    )
    db.commit()
    return RedirectResponse(url="/user/account?verification_sent=1", status_code=303)


@router.post("/start")
def start_daily_cycle(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cycle, error = start_mining_cycle(user, db)
    if error:
        if wants_json_response(request):
            return JSONResponse(
                {"ok": False, "error": error, "status": serialize_mining_status(build_mining_status(user, db))},
                status_code=409,
            )
        return RedirectResponse(url=f"/user/dashboard?{urlencode({'mining_error': error})}", status_code=303)
    if wants_json_response(request):
        return JSONResponse(
            {
                "ok": True,
                "message": "Mining cycle started successfully.",
                "status": serialize_mining_status(build_mining_status(user, db)),
            }
        )
    return RedirectResponse(url="/user/dashboard?cycle_started=1", status_code=303)


@router.get("/mining/status")
def mining_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    completed_cycle = settle_due_mining_cycle(user, db)
    status = build_mining_status(user, db)
    return JSONResponse(serialize_mining_status(status, completed_cycle))


@router.post("/mining/complete")
def complete_mining(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    completed_cycle = settle_due_mining_cycle(user, db)
    query = {"cycle_completed": "1"} if completed_cycle else {}
    suffix = f"?{urlencode(query)}" if query else ""
    return RedirectResponse(url=f"/user/dashboard{suffix}", status_code=303)
