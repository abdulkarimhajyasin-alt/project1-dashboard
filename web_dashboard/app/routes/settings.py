from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, AppSetting


router = APIRouter(prefix="/settings")
templates = Jinja2Templates(directory="app/templates")


DEFAULT_KEYS = ["site_name", "support_email", "maintenance_mode"]


@router.get("", response_class=HTMLResponse)
def settings_page(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    stored = {item.key: item.value for item in db.query(AppSetting).all()}
    values = {key: stored.get(key, "") for key in DEFAULT_KEYS}
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "admin": admin, "active_page": "settings", "settings": values},
    )


@router.post("")
def update_settings(
    site_name: str = Form(""),
    support_email: str = Form(""),
    maintenance_mode: str = Form("off"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    values = {
        "site_name": site_name.strip(),
        "support_email": support_email.strip(),
        "maintenance_mode": maintenance_mode,
    }

    for key, value in values.items():
        setting = db.query(AppSetting).filter(AppSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(AppSetting(key=key, value=value))

    db.commit()
    return RedirectResponse(url="/settings", status_code=303)
