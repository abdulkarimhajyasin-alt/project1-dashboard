from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, Record, User
from app.notifications import get_admin_notifications_context


router = APIRouter(prefix="/records")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def records_page(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    records = db.query(Record).order_by(Record.created_at.desc()).all()
    users = db.query(User).order_by(User.name.asc()).all()
    return templates.TemplateResponse(
        "records.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "records",
            "records": records,
            "users": users,
            **get_admin_notifications_context(db),
        },
    )


@router.post("")
def create_record(
    title: str = Form(...),
    amount: Decimal = Form(0),
    record_type: str = Form("general"),
    user_id: str = Form(""),
    notes: str | None = Form(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    record = Record(
        title=title.strip(),
        amount=amount,
        record_type=record_type.strip() or "general",
        user_id=int(user_id) if user_id else None,
        notes=notes.strip() if notes else None,
    )
    db.add(record)
    db.commit()
    return RedirectResponse(url="/records", status_code=303)


@router.post("/{record_id}/delete")
def delete_record(record_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    record = db.query(Record).filter(Record.id == record_id).first()
    if record:
        db.delete(record)
        db.commit()
    return RedirectResponse(url="/records", status_code=303)
