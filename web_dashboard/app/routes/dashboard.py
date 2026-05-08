from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, AppSetting, Notification, Record, SupportThread, User
from app.notifications import create_user_notification, get_admin_notifications_context
from app.support_chat import add_support_message, get_thread_messages


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_SETTINGS = {
    "site_name": "",
    "support_email": "",
    "maintenance_mode": "off",
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
    return templates.TemplateResponse(
        "notifications.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "notifications",
            **context,
        },
    )


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

    support_message = add_support_message(
        db,
        thread=thread,
        sender_type="admin",
        body=message,
        attachment=attachment,
    )
    if support_message:
        create_user_notification(
            db,
            user_id=thread.user_id,
            title="رد جديد من الدعم",
            message="قام الدعم بالرد على محادثتك.",
            target_url="/user/support?chat=open",
            kind="support",
            data={
                "المحادثة": f"#{thread.id}",
                "المرسل": admin.username,
            },
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
