from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin, AppSetting, User


def is_maintenance_enabled(db: Session) -> bool:
    setting = db.query(AppSetting).filter(AppSetting.key == "maintenance_mode").first()
    return bool(setting and setting.value == "on")


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise_login_redirect()

    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.is_active.is_(True)).first()
    if not admin:
        request.session.clear()
        raise_login_redirect()

    return admin


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise_user_login_redirect()

    user = db.query(User).filter(User.id == user_id, User.status == "active").first()
    if not user:
        request.session.pop("user_id", None)
        raise_user_login_redirect()

    if is_maintenance_enabled(db) and request.method not in {"GET", "HEAD"} and request.url.path != "/user/logout":
        response = RedirectResponse(url="/user/dashboard", status_code=303)
        raise LoginRedirect(response)

    return user


def raise_login_redirect() -> None:
    response = RedirectResponse(url="/login", status_code=303)
    raise LoginRedirect(response)


def raise_user_login_redirect() -> None:
    response = RedirectResponse(url="/user/login", status_code=303)
    raise LoginRedirect(response)


class LoginRedirect(Exception):
    def __init__(self, response: RedirectResponse):
        self.response = response
