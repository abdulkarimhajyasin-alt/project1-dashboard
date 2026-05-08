from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, AppSetting, Notification, Record, User
from app.notifications import get_admin_notifications_context


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


@router.get("/support", response_class=HTMLResponse)
def support(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    context = get_admin_metrics(db)
    return templates.TemplateResponse(
        "support.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "support",
            **context,
        },
    )
