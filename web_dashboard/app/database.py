from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


settings = get_settings()


def get_database_url() -> str:
    if settings.database_url.startswith("postgresql+psycopg://"):
        return settings.database_url
    if settings.database_url.startswith("postgresql+psycopg2://"):
        return settings.database_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if settings.database_url.startswith("postgresql://"):
        return settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return settings.database_url


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_user_columns() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    column_sql = {
        "username": "ALTER TABLE users ADD COLUMN username VARCHAR(80)",
        "password_hash": "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)",
        "capital": "ALTER TABLE users ADD COLUMN capital NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "profits": "ALTER TABLE users ADD COLUMN profits NUMERIC(12, 4) NOT NULL DEFAULT 0",
        "daily_earnings": "ALTER TABLE users ADD COLUMN daily_earnings NUMERIC(12, 4) NOT NULL DEFAULT 0",
        "plan": "ALTER TABLE users ADD COLUMN plan VARCHAR(30) NOT NULL DEFAULT 'none'",
        "referral_code": "ALTER TABLE users ADD COLUMN referral_code VARCHAR(64)",
        "referred_by_id": "ALTER TABLE users ADD COLUMN referred_by_id INTEGER REFERENCES users(id)",
        "last_start_at": "ALTER TABLE users ADD COLUMN last_start_at TIMESTAMP",
    }

    with engine.begin() as connection:
        for column_name, ddl in column_sql.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def ensure_notification_columns() -> None:
    inspector = inspect(engine)
    if "notifications" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("notifications")}
    column_sql = {
        "recipient_user_id": "ALTER TABLE notifications ADD COLUMN recipient_user_id INTEGER REFERENCES users(id)",
    }

    with engine.begin() as connection:
        for column_name, ddl in column_sql.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_user_columns()
    ensure_notification_columns()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
