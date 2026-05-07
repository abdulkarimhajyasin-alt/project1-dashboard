from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, User


router = APIRouter(prefix="/users")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def users_page(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "admin": admin, "active_page": "users", "users": users},
    )


@router.post("")
def create_user(
    name: str = Form(...),
    email: str = Form(...),
    status: str = Form("active"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = User(name=name.strip(), email=email.strip().lower(), status=status)
    db.add(user)
    db.commit()
    return RedirectResponse(url="/users", status_code=303)


@router.post("/{user_id}/delete")
def delete_user(user_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/users", status_code=303)
