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


def create_user_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    target_url: str,
    kind: str = "system",
    target_plan: str | None = None,
    data: dict[str, str] | None = None,
) -> Notification:
    notification = Notification(
        recipient_type="user",
        recipient_user_id=user_id,
        kind=kind,
        title=title,
        message=message,
        target_url=target_url,
        target_plan=target_plan,
        data_json=json.dumps(data or {}, ensure_ascii=False),
    )
    db.add(notification)
    return notification


def serialize_notification(notification: Notification, open_prefix: str) -> dict:
    return {
        "id": notification.id,
        "title": notification.display_title,
        "message": notification.display_message,
        "created_at": notification.created_at.isoformat(),
        "created_label": notification.created_at.strftime("%Y-%m-%d %H:%M"),
        "target_url": notification.target_url or "",
        "open_url": f"{open_prefix}/{notification.id}/open",
        "kind": notification.kind or "system",
        "is_read": bool(notification.is_read),
        "data_rows": notification.data_rows if notification.kind != "support" else [],
    }


def build_notifications_poll_payload(
    db: Session,
    *,
    recipient_type: str,
    open_prefix: str,
    recipient_user_id: int | None = None,
    limit: int = 10,
    messages: list[dict] | None = None,
) -> dict:
    query = db.query(Notification).filter(Notification.recipient_type == recipient_type)
    if recipient_type == "user":
        query = query.filter(Notification.recipient_user_id == recipient_user_id)
    unread_query = query.filter(Notification.is_read.is_(False))
    unread_count = unread_query.count()
    notifications = unread_query.order_by(Notification.created_at.desc()).limit(limit).all()
    latest_notification_id = notifications[0].id if notifications else 0
    return {
        "unread_count": unread_count,
        "notifications": [serialize_notification(item, open_prefix) for item in notifications],
        "messages": messages or [],
        "latest_notification_id": latest_notification_id,
    }


def get_admin_notifications_context(db: Session, limit: int = 10) -> dict:
    notifications = (
        db.query(Notification)
        .filter(Notification.recipient_type == "admin", Notification.is_read.is_(False))
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
        "notification_open_prefix": "/notifications",
        "notification_clear_url": "/notifications/clear",
    }


def get_user_notifications_context(db: Session, user_id: int, limit: int = 10) -> dict:
    notifications = (
        db.query(Notification)
        .filter(
            Notification.recipient_type == "user",
            Notification.recipient_user_id == user_id,
            Notification.is_read.is_(False),
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    unread_count = (
        db.query(Notification)
        .filter(
            Notification.recipient_type == "user",
            Notification.recipient_user_id == user_id,
            Notification.is_read.is_(False),
        )
        .count()
    )
    return {
        "notifications": notifications,
        "unread_notifications_count": unread_count,
        "notification_open_prefix": "/user/notifications",
        "notification_clear_url": "/user/notifications/clear",
    }
