from __future__ import annotations

import mimetypes
import shutil
from datetime import datetime
from pathlib import Path, PurePath
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models import SupportMessage, SupportThread, User


UPLOAD_ROOT = Path(__file__).resolve().parent / "static" / "uploads" / "support"
GENERIC_CONTENT_TYPES = {"application/octet-stream", "binary/octet-stream", "application/x-download"}


def get_support_attachment_path(filename: str) -> Path | None:
    safe_filename = PurePath(filename).name
    if not safe_filename or safe_filename != filename:
        return None

    upload_root = UPLOAD_ROOT.resolve()
    attachment_path = (upload_root / safe_filename).resolve()
    if upload_root not in attachment_path.parents:
        return None
    return attachment_path


def get_or_create_support_thread(db: Session, user: User) -> SupportThread:
    thread = db.query(SupportThread).filter(SupportThread.user_id == user.id).first()
    if thread:
        return thread

    thread = SupportThread(user_id=user.id, status="open")
    db.add(thread)
    db.flush()
    return thread


def get_thread_messages(db: Session, thread: SupportThread) -> list[SupportMessage]:
    return db.query(SupportMessage).filter(SupportMessage.thread_id == thread.id).order_by(SupportMessage.created_at.asc()).all()


def get_latest_thread_message(db: Session, thread: SupportThread) -> SupportMessage | None:
    return (
        db.query(SupportMessage)
        .filter(SupportMessage.thread_id == thread.id)
        .order_by(SupportMessage.created_at.desc())
        .first()
    )


def can_user_send_support_message(db: Session, thread: SupportThread) -> bool:
    latest = get_latest_thread_message(db, thread)
    return latest is None or latest.sender_type != "user"


def save_support_attachment(upload: UploadFile | None) -> dict[str, str] | None:
    if not upload or not upload.filename:
        return None

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    original_name = PurePath(upload.filename).name
    suffix = Path(original_name).suffix[:16]
    stored_name = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_ROOT / stored_name

    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    guessed_content_type = mimetypes.guess_type(original_name)[0]
    uploaded_content_type = (upload.content_type or "").lower()
    content_type = uploaded_content_type if uploaded_content_type not in GENERIC_CONTENT_TYPES else guessed_content_type

    return {
        "name": original_name,
        "url": f"/support/attachments/{stored_name}",
        "content_type": content_type or guessed_content_type or "application/octet-stream",
    }


def add_support_message(
    db: Session,
    *,
    thread: SupportThread,
    sender_type: str,
    body: str,
    attachment: UploadFile | None,
) -> SupportMessage | None:
    clean_body = body.strip()
    attachment_data = save_support_attachment(attachment)

    if not clean_body and not attachment_data:
        return None

    message = SupportMessage(
        thread_id=thread.id,
        sender_type=sender_type,
        body=clean_body or None,
        attachment_name=attachment_data["name"] if attachment_data else None,
        attachment_url=attachment_data["url"] if attachment_data else None,
        attachment_content_type=attachment_data["content_type"] if attachment_data else None,
    )
    thread.status = "waiting_admin" if sender_type == "user" else "answered"
    thread.updated_at = datetime.utcnow()
    db.add(message)
    db.add(thread)
    return message
