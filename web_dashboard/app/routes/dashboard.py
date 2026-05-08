from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, AppSetting, Record, User


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

DEFAULT_SETTINGS = {
    "site_name": "",
    "support_email": "",
    "maintenance_mode": "off",
}


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    users_count = db.query(User).count()
    active_users_count = db.query(User).filter(User.status == "active").count()
    records_count = db.query(Record).count()
    total_amount = db.query(func.coalesce(func.sum(Record.amount), 0)).scalar()
    total_capital = db.query(func.coalesce(func.sum(User.capital), 0)).scalar()
    total_profits = db.query(func.coalesce(func.sum(User.profits), 0)).scalar()
    active_cycles = db.query(User).filter(User.last_start_at.isnot(None)).count()
    users = db.query(User).order_by(User.created_at.desc()).all()
    records = db.query(Record).order_by(Record.created_at.desc()).all()
    latest_records = records[:5]
    stored_settings = {item.key: item.value for item in db.query(AppSetting).all()}
    settings = {**DEFAULT_SETTINGS, **stored_settings}

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "dashboard",
            "users_count": users_count,
            "active_users_count": active_users_count,
            "records_count": records_count,
            "total_amount": total_amount,
            "total_capital": total_capital,
            "total_profits": total_profits,
            "active_cycles": active_cycles,
            "latest_records": latest_records,
            "users": users,
            "records": records,
            "settings": settings,
        },
    )
