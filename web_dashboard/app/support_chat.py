from __future__ import annotations

import mimetypes
from datetime import datetime
from pathlib import Path, PurePath
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models import SupportMessage, SupportThread, User


GENERIC_CONTENT_TYPES = {"application/octet-stream", "binary/octet-stream", "application/x-download"}
MAX_SUPPORT_ATTACHMENT_SIZE = 5 * 1024 * 1024
IMAGE_SIGNATURE_EXTENSIONS = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
)


class SupportAttachmentError(ValueError):
    pass


def detect_image_extension(content: bytes) -> str | None:
    for signature, extension in IMAGE_SIGNATURE_EXTENSIONS:
        if content.startswith(signature):
            return extension
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


def get_safe_extension(original_name: str, content_type: str, content: bytes) -> str:
    detected_image_extension = detect_image_extension(content)
    if detected_image_extension:
        return detected_image_extension

    guessed_extension = mimetypes.guess_extension(content_type or "")
    if guessed_extension:
        return ".jpg" if guessed_extension == ".jpe" else guessed_extension.lower()

    original_extension = Path(original_name).suffix.lower()
    if original_extension:
        return original_extension[:16]

    return ".bin"


def is_image_attachment(content: bytes, mime_type: str, filename: str) -> bool:
    if detect_image_extension(content):
        return True
    if mime_type.startswith("image/"):
        return True
    return Path(filename).suffix.lower() in {".gif", ".jpeg", ".jpg", ".png", ".webp"}


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


def save_support_attachment(upload: UploadFile | None) -> dict[str, object] | None:
    if not upload or not upload.filename:
        return None

    original_name = PurePath(upload.filename).name
    uploaded_content_type = (upload.content_type or "").lower()
    guessed_content_type = mimetypes.guess_type(original_name)[0]
    content_type = uploaded_content_type if uploaded_content_type not in GENERIC_CONTENT_TYPES else guessed_content_type
    upload.file.seek(0)
    content = upload.file.read()
    size = len(content)
    if size > MAX_SUPPORT_ATTACHMENT_SIZE:
        raise SupportAttachmentError("حجم المرفق أكبر من الحد المسموح 5MB.")
    if size == 0:
        raise SupportAttachmentError("المرفق فارغ ولا يمكن إرساله.")

    suffix = get_safe_extension(original_name, content_type or "", content)
    stored_content_type = mimetypes.guess_type(f"attachment{suffix}")[0] or content_type or guessed_content_type
    stored_name = f"support_{uuid4().hex}{suffix}"
    is_image = is_image_attachment(content, stored_content_type or "", stored_name)

    return {
        "name": stored_name,
        "data": content,
        "mime_type": stored_content_type or "application/octet-stream",
        "size": size,
        "is_image": is_image,
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
        attachment_url=None,
        attachment_content_type=attachment_data["mime_type"] if attachment_data else None,
        attachment_data=attachment_data["data"] if attachment_data else None,
        attachment_mime_type=attachment_data["mime_type"] if attachment_data else None,
        attachment_size=attachment_data["size"] if attachment_data else None,
        is_image=bool(attachment_data["is_image"]) if attachment_data else False,
    )
    thread.status = "waiting_admin" if sender_type == "user" else "answered"
    thread.updated_at = datetime.utcnow()
    db.add(message)
    db.add(thread)
    db.flush()
    return message
