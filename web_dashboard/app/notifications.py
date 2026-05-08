import json

from sqlalchemy.orm import Session

from app.models import Notification


def create_admin_notification(
    db: Session,
    *,
    title: str,
    message: str,
    target_url: str,
    kind: str = "system",
    data: dict[str, str] | None = None,
) -> Notification:
    notification = Notification(
        recipient_type="admin",
        kind=kind,
        title=title,
        message=message,
        target_url=target_url,
        data_json=json.dumps(data or {}, ensure_ascii=False),
    )
    db.add(notification)
    return notification


def get_admin_notifications_context(db: Session, limit: int = 10) -> dict:
    notifications = (
        db.query(Notification)
        .filter(Notification.recipient_type == "admin")
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    unread_count = (
        db.query(Notification)
        .filter(Notification.recipient_type == "admin", Notification.is_read.is_(False))
        .count()
    )
    return {
        "notifications": notifications,
        "unread_notifications_count": unread_count,
    }
