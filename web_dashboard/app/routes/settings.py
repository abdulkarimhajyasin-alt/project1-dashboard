import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, AppSetting, User
from app.notifications import create_user_notification, get_admin_notifications_context


router = APIRouter(prefix="/settings")
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("uvicorn.error")


PLAN_LABELS = {
    "silver": "الفضية",
    "gold": "الذهبية",
    "vip": "VIP",
}


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str) -> None:
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        setting.value = value
        return
    db.add(AppSetting(key=key, value=value))


@router.get("", response_class=HTMLResponse)
def settings_page(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    maintenance_mode = get_setting(db, "maintenance_mode", "off")
    plan_counts = {
        plan: db.query(User).filter(User.plan == plan).count()
        for plan in PLAN_LABELS
    }
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "settings",
            "maintenance_enabled": maintenance_mode == "on",
            "users_count": db.query(User).count(),
            "plan_counts": plan_counts,
            "plan_labels": PLAN_LABELS,
            **get_admin_notifications_context(db),
        },
    )


@router.post("/maintenance")
def toggle_maintenance(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    current_mode = get_setting(db, "maintenance_mode", "off")
    next_mode = "off" if current_mode == "on" else "on"
    set_setting(db, "maintenance_mode", next_mode)
    db.commit()
    if next_mode == "on":
        logger.info("maintenance enabled by admin %s", admin.username)
    else:
        logger.info("maintenance disabled by admin %s", admin.username)
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/broadcast")
def broadcast_to_all_users(
    title: str = Form(...),
    message: str = Form(...),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_title = title.strip()
    clean_message = message.strip()
    if clean_title and clean_message:
        users = db.query(User).all()
        for user in users:
            create_user_notification(
                db,
                user_id=user.id,
                title=clean_title,
                message=clean_message,
                target_url="/user/dashboard",
                kind="broadcast",
            )
        db.commit()
        logger.info("broadcast created by admin %s for %s users", admin.username, len(users))
    return RedirectResponse(url="/settings", status_code=303)


@router.post("/plan-broadcast")
def broadcast_to_plan_users(
    target_plan: str = Form(...),
    title: str = Form(...),
    message: str = Form(...),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    clean_title = title.strip()
    clean_message = message.strip()
    if target_plan in PLAN_LABELS and clean_title and clean_message:
        users = db.query(User).filter(User.plan == target_plan).all()
        for user in users:
            create_user_notification(
                db,
                user_id=user.id,
                title=clean_title,
                message=clean_message,
                target_url="/user/dashboard",
                kind="plan_broadcast",
                target_plan=target_plan,
            )
        db.commit()
        logger.info(
            "plan broadcast created by admin %s for plan %s (%s users)",
            admin.username,
            target_plan,
            len(users),
        )
    return RedirectResponse(url="/settings", status_code=303)
