from decimal import Decimal

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models import Admin, Record, User


router = APIRouter(prefix="/users")
templates = Jinja2Templates(directory="app/templates")


def get_admin_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_class=HTMLResponse)
def users_page(request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "admin": admin, "active_page": "users", "users": users},
    )


@router.get("/{user_id}", response_class=HTMLResponse)
def user_details(user_id: int, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = get_admin_user(db, user_id)
    records = db.query(Record).filter(Record.user_id == user.id).order_by(Record.created_at.desc()).all()
    return templates.TemplateResponse(
        "user_detail.html",
        {
            "request": request,
            "admin": admin,
            "active_page": "users",
            "user": user,
            "records": records,
        },
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


@router.post("/{user_id}/status")
def update_user_status(
    user_id: int,
    status_action: str = Form(...),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    status_map = {
        "ban": "banned",
        "unban": "active",
        "freeze": "frozen",
        "unfreeze": "active",
        "activate": "active",
        "deactivate": "inactive",
    }
    user.status = status_map.get(status_action, user.status)
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/plan")
def update_user_plan(
    user_id: int,
    plan: str = Form("none"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    allowed_plans = {"none", "silver", "gold", "vip"}
    user.plan = plan if plan in allowed_plans else "none"
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/balance")
def adjust_user_balance(
    user_id: int,
    field: str = Form(...),
    operation: str = Form(...),
    amount: Decimal = Form(0),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = get_admin_user(db, user_id)
    safe_amount = abs(amount)
    delta = safe_amount if operation == "add" else -safe_amount

    if field == "profits":
        user.profits = max(Decimal("0"), Decimal(user.profits or 0) + delta)
    else:
        user.capital = max(Decimal("0"), Decimal(user.capital or 0) + delta)

    db.add(
        Record(
            user_id=user.id,
            title="Admin balance adjustment",
            amount=delta,
            record_type=f"{field}_{operation}",
            notes=f"Adjusted by admin: {admin.username}",
        )
    )
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/reset-cycle")
def reset_user_cycle(user_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = get_admin_user(db, user_id)
    user.last_start_at = None
    db.commit()
    return RedirectResponse(url=f"/users/{user.id}", status_code=303)


@router.post("/{user_id}/delete")
def delete_user(user_id: int, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/users", status_code=303)
