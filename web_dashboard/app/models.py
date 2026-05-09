from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    capital: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    profits: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0, nullable=False)
    daily_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0, nullable=False)
    plan: Mapped[str] = mapped_column(String(30), default="none", nullable=False)
    referral_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=True)
    referred_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    last_start_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    records: Mapped[list[Record]] = relationship(back_populates="user", cascade="all, delete-orphan")
    referrer: Mapped[User] = relationship(remote_side="User.id", back_populates="referrals")
    referrals: Mapped[list[User]] = relationship(back_populates="referrer")


class Record(Base):
    __tablename__ = "records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    record_type: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="records")


class PendingRequest(Base):
    __tablename__ = "pending_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    request_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped[User | None] = relationship()

    @property
    def details_rows(self) -> list[dict[str, str]]:
        if not self.details_json:
            return []
        try:
            data = json.loads(self.details_json)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, dict):
            return []
        return [{"label": str(key), "value": str(value)} for key, value in data.items()]


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipient_type: Mapped[str] = mapped_column(String(30), default="admin", nullable=False, index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), default="system", nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_url: Mapped[str] = mapped_column(String(255), nullable=True)
    target_plan: Mapped[str] = mapped_column(String(30), nullable=True)
    data_json: Mapped[str] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def data_dict(self) -> dict[str, str]:
        if not self.data_json:
            return {}
        try:
            data = json.loads(self.data_json)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    @property
    def data_rows(self) -> list[dict[str, str]]:
        data = self.data_dict
        if not data:
            return []
        return [{"label": key, "value": value} for key, value in data.items()]

    @property
    def is_user_support_message(self) -> bool:
        data = self.data_dict
        return self.kind == "support" and self.title == "رسالة دعم جديدة" and bool(data.get("اسم المستخدم") or data.get("الاسم"))

    @property
    def is_support_reply_notification(self) -> bool:
        data = self.data_dict
        return self.kind == "support" and self.title == "رد جديد من الدعم" and bool(data.get("المحادثة") or data.get("المرسل"))

    @property
    def display_title(self) -> str:
        if self.is_user_support_message:
            data = self.data_dict
            return data.get("اسم المستخدم") or data.get("الاسم") or self.title
        if self.is_support_reply_notification:
            return "الدعم"
        return self.title

    @property
    def display_message(self) -> str:
        if self.is_user_support_message:
            attachment = self.data_dict.get("مرفق", "")
            if attachment and attachment != "بدون مرفق":
                image_extensions = (".gif", ".jpeg", ".jpg", ".png", ".webp")
                return "صورة" if attachment.lower().endswith(image_extensions) else "ملف"
        return self.message

    @property
    def is_user_modal_notification(self) -> bool:
        return self.recipient_type == "user" and self.kind in {"broadcast", "plan_broadcast"}

    @property
    def target_plan_label(self) -> str:
        plan_labels = {
            "silver": "الفضية",
            "gold": "الذهبية",
            "vip": "VIP",
        }
        return plan_labels.get(self.target_plan or "", self.target_plan or "")

    @property
    def modal_subtitle(self) -> str:
        if self.kind == "plan_broadcast" and self.target_plan_label:
            return f"رسالة خاصة بمستخدمي باقة {self.target_plan_label}"
        return ""


class SupportThread(Base):
    __tablename__ = "support_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship()
    messages: Mapped[list["SupportMessage"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("support_threads.id"), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    attachment_name: Mapped[str] = mapped_column(String(255), nullable=True)
    attachment_url: Mapped[str] = mapped_column(String(255), nullable=True)
    attachment_content_type: Mapped[str] = mapped_column(String(120), nullable=True)
    attachment_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    attachment_mime_type: Mapped[str] = mapped_column(String(120), nullable=True)
    attachment_size: Mapped[int] = mapped_column(Integer, nullable=True)
    is_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    thread: Mapped[SupportThread] = relationship(back_populates="messages")

    @property
    def has_attachment_data(self) -> bool:
        return self.attachment_data_length > 0

    @property
    def attachment_data_length(self) -> int:
        if self.attachment_data is None:
            return 0
        try:
            return len(self.attachment_data)
        except TypeError:
            return len(bytes(self.attachment_data))

    @property
    def attachment_type(self) -> str:
        return self.attachment_mime_type or self.attachment_content_type or "application/octet-stream"
