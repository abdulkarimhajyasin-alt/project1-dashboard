from __future__ import annotations

import hmac
import re
import secrets
from collections.abc import Callable
from urllib.parse import parse_qs

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware


CSRF_SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "_csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
CSRF_ERROR_MESSAGE = "Your session expired. Please refresh the page and try again."
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def csrf_meta_tag(token: str) -> str:
    return f'<meta name="csrf-token" content="{token}">'


def csrf_input_tag(token: str) -> str:
    return f'<input type="hidden" name="{CSRF_FORM_FIELD}" value="{token}">'


def wants_json(request: Request) -> bool:
    return (
        request.headers.get("x-requested-with") == "fetch"
        or "application/json" in request.headers.get("accept", "")
    )


def csrf_failure_response(request: Request) -> Response:
    if wants_json(request):
        return JSONResponse({"ok": False, "error": CSRF_ERROR_MESSAGE}, status_code=403)

    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Session expired</title>
          <style>
            body {{
              align-items: center;
              background: radial-gradient(circle at top, #0f2740, #020617 58%);
              color: #dff7ff;
              display: grid;
              font-family: Inter, Arial, sans-serif;
              min-height: 100vh;
              margin: 0;
              padding: 24px;
            }}
            main {{
              background: linear-gradient(145deg, rgba(15, 31, 51, .96), rgba(7, 14, 28, .98));
              border: 1px solid rgba(103, 232, 249, .28);
              border-radius: 8px;
              box-shadow: 0 30px 90px rgba(0, 0, 0, .46);
              margin: auto;
              max-width: 520px;
              padding: 28px;
            }}
            h1 {{ color: #fff; font-size: 28px; margin: 0 0 12px; }}
            p {{ color: #a9bdd5; line-height: 1.7; margin: 0 0 18px; }}
            button {{
              background: linear-gradient(135deg, #25f6a4, #38bdf8);
              border: 0;
              border-radius: 8px;
              color: #04111f;
              cursor: pointer;
              font-weight: 900;
              padding: 12px 16px;
            }}
          </style>
        </head>
        <body>
          <main>
            <h1>Session expired</h1>
            <p>{CSRF_ERROR_MESSAGE}</p>
            <button type="button" onclick="window.location.reload()">Refresh page</button>
          </main>
        </body>
        </html>
        """,
        status_code=403,
    )


async def extract_submitted_token(request: Request) -> str:
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if header_token:
        return header_token

    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        body = await request.body()

        async def receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
        if "application/x-www-form-urlencoded" in content_type:
            values = parse_qs(body.decode("utf-8", errors="replace"))
            return values.get(CSRF_FORM_FIELD, [""])[0]

        match = re.search(
            rb'name=["\']' + re.escape(CSRF_FORM_FIELD.encode()) + rb'["\']\r?\n\r?\n([^\r\n]+)',
            body,
        )
        if match:
            return match.group(1).decode("utf-8", errors="replace").strip()

    return ""


def inject_csrf_into_html(html: str, token: str) -> str:
    if 'name="csrf-token"' not in html and "</head>" in html:
        html = html.replace("</head>", f"  {csrf_meta_tag(token)}\n</head>", 1)

    form_input = csrf_input_tag(token)
    form_pattern = re.compile(r"(<form\b(?=[^>]*\bmethod=[\"']post[\"'])[^>]*>)", re.IGNORECASE)
    return form_pattern.sub(lambda match: f"{match.group(1)}\n{form_input}", html)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token = get_or_create_csrf_token(request)

        if request.method.upper() not in SAFE_METHODS:
            submitted_token = await extract_submitted_token(request)
            if not submitted_token or not hmac.compare_digest(submitted_token, token):
                return csrf_failure_response(request)

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type.lower():
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip()

        html = body.decode(charset, errors="replace")
        html = inject_csrf_into_html(html, token)
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=html.encode(charset),
            status_code=response.status_code,
            headers=headers,
            media_type="text/html",
            background=response.background,
        )
