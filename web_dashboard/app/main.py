import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.dependencies import LoginRedirect
from app.models import Admin
from app.routes import auth, dashboard, records, settings, user_portal, users
from app.security import hash_password


logger = logging.getLogger("uvicorn.error")
app_settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent

if not app_settings.is_configured:
    raise RuntimeError("DATABASE_URL and SECRET_KEY environment variables are required.")

app = FastAPI(title=app_settings.app_name)
app.add_middleware(
    SessionMiddleware,
    secret_key=app_settings.secret_key,
    session_cookie=app_settings.session_cookie_name,
    https_only=False,
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def create_initial_admin() -> None:
    db = SessionLocal()
    try:
        if db.query(Admin).first():
            logger.info("Admin already exists")
            return

        print(f"Admin password length: {len(app_settings.admin_password)}")
        if not app_settings.admin_username or not app_settings.admin_password:
            raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD environment variables are required.")

        admin = Admin(username=app_settings.admin_username, password_hash=hash_password(app_settings.admin_password))
        db.add(admin)
        db.commit()
        logger.info("Admin created")
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    create_initial_admin()


@app.exception_handler(LoginRedirect)
async def login_redirect_handler(request: Request, exc: LoginRedirect):
    return exc.response


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=303)


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(records.router)
app.include_router(settings.router)
app.include_router(user_portal.router)
