from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from urllib.parse import quote, urlencode

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, AppSetting, Notification, PendingRequest, Record, SupportMessage, SupportThread, User
from app.notifications import create_user_notification, get_admin_notifications_context
from app.support_chat import SupportAttachmentError, add_support_message, get_thread_messages


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
    users_count = db.query(User).count()
    active_users_count = db.query(User).filter(User.status == "active").count()
    records_count = db.query(Record).count()
    total_amount = db.query(func.coalesce(func.sum(Record.amount), 0)).scalar()
    total_capital = db.query(func.coalesce(func.sum(User.capital), 0)).scalar()
    total_profits = db.query(func.coalesce(func.sum(User.profits), 0)).scalar()
    active_cycles = db.query(User).filter(User.last_start_at.isnot(None)).count()
    latest_records = db.query(Record).order_by(Record.created_at.desc()).limit(5).all()
    stored_settings = {item.key: item.value for item in db.query(AppSetting).all()}
    settings = {**DEFAULT_SETTINGS, **stored_settings}

    return {
        "users_count": users_count,
        "active_users_count": active_users_count,
        "records_count": records_count,
        "total_amount": total_amount,
        "total_capital": total_capital,
        "total_profits": total_profits,
        "active_cycles": active_cycles,
        "latest_records": latest_records,
        "settings": settings,
        **get_admin_notifications_context(db),
    }


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


def get_support_notification_message(support_message: SupportMessage) -> str:
    if support_message.has_attachment_data:
        return "صورة" if support_message.is_image else "ملف"
    return support_message.body or "رسالة جديدة"


@router.get("/support/attachments/{message_id}")
def support_attachment(message_id: int, request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    user_id = request.session.get("user_id")
    print("Opening support attachment:", {"message_id": message_id, "admin_id": admin_id, "user_id": user_id})
    if not admin_id and not user_id:
        print("Support attachment denied: no active session", {"message_id": message_id})
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
        print("Support attachment missing or unauthorized:", {"message_id": message_id, "admin_id": admin_id, "user_id": user_id})
        raise HTTPException(status_code=404, detail="Attachment not found")

    print(
        "Support attachment message found:",
        {
            "id": message.id,
            "thread_id": message.thread_id,
            "sender_type": message.sender_type,
            "has_data": message.has_attachment_data,
            "data_length": message.attachment_data_length,
            "attachment_size": message.attachment_size,
            "is_image": message.is_image,
            "mime": message.attachment_type,
            "name": message.attachment_name,
        },
    )
    if message.attachment_data_length <= 0:
        print("Support attachment has no BYTEA data:", {"message_id": message_id, "attachment_size": message.attachment_size})
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
            **context,
            **pending_context,
        },
    )


@router.post("/pending-requests/{request_id}/accept")
def accept_pending_request(request_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    pending_request = db.query(PendingRequest).filter(PendingRequest.id == request_id).first()
    if pending_request:
        pending_request.status = "accepted"
        db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/pending-requests/{request_id}/reject")
def reject_pending_request(request_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    pending_request = db.query(PendingRequest).filter(PendingRequest.id == request_id).first()
    if pending_request:
        pending_request.status = "rejected"
        db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


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
def clear_notifications(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    (
        db.query(Notification)
        .filter(Notification.recipient_type == "admin", Notification.is_read.is_(False))
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
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
