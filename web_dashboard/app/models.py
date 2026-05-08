from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import PurePath

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


IMAGE_EXTENSIONS = {".apng", ".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}


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
    data_json: Mapped[str] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    @property
    def data_rows(self) -> list[dict[str, str]]:
        if not self.data_json:
            return []
        try:
            data = json.loads(self.data_json)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, dict):
            return []
        return [{"label": str(key), "value": str(value)} for key, value in data.items()]


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    thread: Mapped[SupportThread] = relationship(back_populates="messages")

    @property
    def is_image(self) -> bool:
        if self.attachment_content_type and self.attachment_content_type.startswith("image/"):
            return True

        for value in (self.attachment_name, self.attachment_url):
            if value and PurePath(value).suffix.lower() in IMAGE_EXTENSIONS:
                return True

        return False

    @property
    def attachment_static_path(self):
        if not self.attachment_url:
            return None
        if self.attachment_url.startswith("/static/"):
            return self.attachment_url.replace("/static", "", 1)
        if self.attachment_url.startswith("static/"):
            return "/" + self.attachment_url.replace("static/", "", 1)
        return None

    @property
    def attachment_display_url(self):
        if not self.attachment_url:
            return ""
        if self.attachment_url.startswith(("http://", "https://", "/")):
            return self.attachment_url
        return "/" + self.attachment_url
