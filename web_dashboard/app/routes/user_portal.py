# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Record, User
from app.notifications import create_admin_notification
from app.security import hash_password, verify_password


router = APIRouter(prefix="/user")
templates = Jinja2Templates(directory="app/templates")
DAILY_DURATION = timedelta(hours=24)
MIN_WITHDRAWAL = Decimal("10.00")
BASE_DAILY_REWARD = Decimal("0.001")
REFERRAL_DAILY_REWARD = Decimal("0.0005")


def make_referral_code() -> str:
    return uuid4().hex[:10]


def get_daily_reward(user: User) -> Decimal:
    capital = Decimal(user.capital or 0)
    if capital <= 0:
        return BASE_DAILY_REWARD
    units = int(capital // Decimal("10"))
    return BASE_DAILY_REWARD * Decimal(max(units, 1))


def settle_daily_cycle(user: User, db: Session) -> None:
    if not user.last_start_at:
        return
    if datetime.utcnow() - user.last_start_at < DAILY_DURATION:
        return

    reward = get_daily_reward(user)
    user.profits = Decimal(user.profits or 0) + reward
    user.daily_earnings = reward
    db.add(
        Record(
            user_id=user.id,
            title="Daily mining reward",
            amount=reward,
            record_type="daily_reward",
            notes="Automatic daily reward after 24 hour cycle.",
        )
    )
    user.last_start_at = None
    db.commit()
    db.refresh(user)


def get_progress_percent(user: User) -> int:
    if not user.last_start_at:
        return 0
    elapsed = datetime.utcnow() - user.last_start_at
    return min(100, int((elapsed.total_seconds() / DAILY_DURATION.total_seconds()) * 100))


def get_referral_url(request: Request, user: User) -> str:
    code = user.referral_code or ""
    return str(request.url_for("user_register")) + f"?ref={code}"


def build_user_context(request: Request, user: User, active_user_page: str) -> dict:
    withdraw_percent = min(100, int((Decimal(user.profits or 0) / MIN_WITHDRAWAL) * 100))
    return {
        "request": request,
        "user": user,
        "active_user_page": active_user_page,
        "progress_percent": get_progress_percent(user),
        "can_start": user.last_start_at is None,
        "withdraw_percent": withdraw_percent,
        "min_withdrawal": MIN_WITHDRAWAL,
        "referral_url": get_referral_url(request, user),
        "referrals_count": len(user.referrals),
    }


@router.get("/register", response_class=HTMLResponse, name="user_register")
def register_page(request: Request, ref: str = ""):
    return templates.TemplateResponse("user_register.html", {"request": request, "error": None, "ref": ref})


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    ref: str = Form(""),
    db: Session = Depends(get_db),
):
    username = username.strip().lower()
    email = email.strip().lower()
    existing = db.query(User).filter(or_(User.username == username, User.email == email)).first()
    if existing:
        return templates.TemplateResponse(
            "user_register.html",
            {"request": request, "error": "اسم المستخدم أو البريد مستخدم مسبقاً.", "ref": ref},
            status_code=400,
        )

    referrer = db.query(User).filter(User.referral_code == ref).first() if ref else None
    user = User(
        name=name.strip(),
        username=username,
        email=email,
        password_hash=hash_password(password),
        referral_code=make_referral_code(),
        referred_by_id=referrer.id if referrer else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_admin_notification(
        db,
        title="إنشاء حساب جديد",
        message=f"قام {user.name} بإنشاء حساب جديد.",
        target_url=f"/users/{user.id}",
        kind="account",
        data={
            "الاسم": user.name,
            "اسم المستخدم": user.username or "-",
            "البريد الإلكتروني": user.email,
            "كلمة السر": "محفوظة كـ hash ولا يتم عرضها كنص صريح",
            "كود الإحالة": user.referral_code or "-",
            "كود الدعوة المستخدم": ref.strip() or "-",
            "المحيل": referrer.username if referrer else "-",
        },
    )
    db.commit()
    request.session["user_id"] = user.id
    request.session.pop("user_intro_seen", None)
    return RedirectResponse(url="/user/dashboard", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/user/dashboard", status_code=303)
    return templates.TemplateResponse("user_login.html", {"request": request, "error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    login_value = username.strip().lower()
    user = db.query(User).filter(or_(User.username == login_value, User.email == login_value), User.status == "active").first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "user_login.html",
            {"request": request, "error": "بيانات الدخول غير صحيحة."},
            status_code=401,
        )

    request.session["user_id"] = user.id
    request.session.pop("user_intro_seen", None)
    return RedirectResponse(url="/user/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.pop("user_id", None)
    request.session.pop("user_intro_seen", None)
    return RedirectResponse(url="/user/login", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    intro_seen = bool(request.session.get("user_intro_seen"))
    request.session["user_intro_seen"] = True
    context = build_user_context(request, user, "dashboard")
    return templates.TemplateResponse(
        "user_dashboard.html",
        {
            "intro_seen": intro_seen,
            **context,
        },
    )


@router.get("/plans", response_class=HTMLResponse)
def plans_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    return templates.TemplateResponse("user_plans.html", build_user_context(request, user, "plans"))


@router.get("/withdraw", response_class=HTMLResponse)
def withdraw_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    return templates.TemplateResponse("user_withdraw.html", build_user_context(request, user, "withdraw"))


@router.get("/referral", response_class=HTMLResponse)
def referral_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    return templates.TemplateResponse("user_referral.html", build_user_context(request, user, "referral"))


@router.get("/support", response_class=HTMLResponse)
def support_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    return templates.TemplateResponse("user_support.html", build_user_context(request, user, "support"))


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    context = build_user_context(request, user, "history")
    context["records"] = db.query(Record).filter(Record.user_id == user.id).order_by(Record.created_at.desc()).all()
    return templates.TemplateResponse("user_history.html", context)


@router.get("/account", response_class=HTMLResponse)
def account_page(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    return templates.TemplateResponse("user_account.html", build_user_context(request, user, "account"))


@router.post("/start")
def start_daily_cycle(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settle_daily_cycle(user, db)
    if user.last_start_at is None:
        user.last_start_at = datetime.utcnow()
        if user.referrer:
            user.referrer.profits = Decimal(user.referrer.profits or 0) + REFERRAL_DAILY_REWARD
            db.add(
                Record(
                    user_id=user.referrer.id,
                    title="Referral activity reward",
                    amount=REFERRAL_DAILY_REWARD,
                    record_type="referral_reward",
                    notes=f"Referral started daily cycle: {user.username or user.email}",
                )
            )
        db.commit()
    return RedirectResponse(url="/user/dashboard", status_code=303)
