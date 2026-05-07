from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, Record, User


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    users_count = db.query(User).count()
    active_users_count = db.query(User).filter(User.status == "active").count()
    records_count = db.query(Record).count()
    total_amount = db.query(func.coalesce(func.sum(Record.amount), 0)).scalar()
    total_capital = db.query(func.coalesce(func.sum(User.capital), 0)).scalar()
    total_profits = db.query(func.coalesce(func.sum(User.profits), 0)).scalar()
    active_cycles = db.query(User).filter(User.last_start_at.isnot(None)).count()
    latest_records = db.query(Record).order_by(Record.created_at.desc()).limit(5).all()

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
        },
    )