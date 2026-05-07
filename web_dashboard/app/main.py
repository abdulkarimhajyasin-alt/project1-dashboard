from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import init_db
from app.dependencies import LoginRedirect
from app.routes import auth, dashboard, records, settings, users


app_settings = get_settings()

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
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


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
