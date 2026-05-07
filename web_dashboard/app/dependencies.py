from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise_login_redirect()

    admin = db.query(Admin).filter(Admin.id == admin_id, Admin.is_active.is_(True)).first()
    if not admin:
        request.session.clear()
        raise_login_redirect()

    return admin


def raise_login_redirect() -> None:
    response = RedirectResponse(url="/login", status_code=303)
    raise LoginRedirect(response)


class LoginRedirect(Exception):
    def __init__(self, response: RedirectResponse):
        self.response = response
