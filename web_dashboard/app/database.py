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
        "verified": "ALTER TABLE users ADD COLUMN verified BOOLEAN NOT NULL DEFAULT FALSE",
        "verification_status": "ALTER TABLE users ADD COLUMN verification_status VARCHAR(30) NOT NULL DEFAULT 'unverified'",
        "legal_full_name": "ALTER TABLE users ADD COLUMN legal_full_name VARCHAR(160)",
        "residence_country": "ALTER TABLE users ADD COLUMN residence_country VARCHAR(120)",
        "timezone": "ALTER TABLE users ADD COLUMN timezone VARCHAR(80)",
        "document_type": "ALTER TABLE users ADD COLUMN document_type VARCHAR(40)",
        "verification_requested_at": "ALTER TABLE users ADD COLUMN verification_requested_at TIMESTAMP",
        "verification_approved_at": "ALTER TABLE users ADD COLUMN verification_approved_at TIMESTAMP",
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
        "target_plan": "ALTER TABLE notifications ADD COLUMN target_plan VARCHAR(30)",
    }

    with engine.begin() as connection:
        for column_name, ddl in column_sql.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def ensure_support_message_columns() -> None:
    inspector = inspect(engine)
    if "support_messages" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("support_messages")}
    binary_type = "BYTEA" if engine.dialect.name.startswith("postgresql") else "BLOB"
    column_sql = {
        "attachment_data": f"ALTER TABLE support_messages ADD COLUMN attachment_data {binary_type}",
        "attachment_mime_type": "ALTER TABLE support_messages ADD COLUMN attachment_mime_type VARCHAR(120)",
        "attachment_size": "ALTER TABLE support_messages ADD COLUMN attachment_size INTEGER",
        "is_image": "ALTER TABLE support_messages ADD COLUMN is_image BOOLEAN NOT NULL DEFAULT FALSE",
    }

    with engine.begin() as connection:
        for column_name, ddl in column_sql.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def ensure_pending_request_columns() -> None:
    inspector = inspect(engine)
    if "pending_requests" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("pending_requests")}
    binary_type = "BYTEA" if engine.dialect.name.startswith("postgresql") else "BLOB"
    column_sql = {
        "legal_full_name": "ALTER TABLE pending_requests ADD COLUMN legal_full_name VARCHAR(160)",
        "country": "ALTER TABLE pending_requests ADD COLUMN country VARCHAR(120)",
        "timezone": "ALTER TABLE pending_requests ADD COLUMN timezone VARCHAR(80)",
        "document_type": "ALTER TABLE pending_requests ADD COLUMN document_type VARCHAR(40)",
        "front_image_data": f"ALTER TABLE pending_requests ADD COLUMN front_image_data {binary_type}",
        "front_image_mime_type": "ALTER TABLE pending_requests ADD COLUMN front_image_mime_type VARCHAR(120)",
        "front_image_size": "ALTER TABLE pending_requests ADD COLUMN front_image_size INTEGER",
        "back_image_data": f"ALTER TABLE pending_requests ADD COLUMN back_image_data {binary_type}",
        "back_image_mime_type": "ALTER TABLE pending_requests ADD COLUMN back_image_mime_type VARCHAR(120)",
        "back_image_size": "ALTER TABLE pending_requests ADD COLUMN back_image_size INTEGER",
        "passport_image_data": f"ALTER TABLE pending_requests ADD COLUMN passport_image_data {binary_type}",
        "passport_image_mime_type": "ALTER TABLE pending_requests ADD COLUMN passport_image_mime_type VARCHAR(120)",
        "passport_image_size": "ALTER TABLE pending_requests ADD COLUMN passport_image_size INTEGER",
    }

    with engine.begin() as connection:
        for column_name, ddl in column_sql.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


def ensure_record_amount_precision() -> None:
    inspector = inspect(engine)
    if "records" not in inspector.get_table_names():
        return
    if not engine.dialect.name.startswith("postgresql"):
        return

    amount_column = next(
        (column for column in inspector.get_columns("records") if column["name"] == "amount"),
        None,
    )
    if not amount_column:
        return
    column_type = amount_column["type"]
    if getattr(column_type, "precision", None) == 12 and getattr(column_type, "scale", None) == 4:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE records ALTER COLUMN amount TYPE NUMERIC(12, 4)"))


def ensure_mining_cycle_columns() -> None:
    inspector = inspect(engine)
    if "mining_cycles" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("mining_cycles")}
    column_sql = {
        "cycle_window_start": "ALTER TABLE mining_cycles ADD COLUMN cycle_window_start TIMESTAMP",
        "cycle_window_end": "ALTER TABLE mining_cycles ADD COLUMN cycle_window_end TIMESTAMP",
        "actual_start_time": "ALTER TABLE mining_cycles ADD COLUMN actual_start_time TIMESTAMP",
        "active_seconds": "ALTER TABLE mining_cycles ADD COLUMN active_seconds INTEGER NOT NULL DEFAULT 86400",
        "missed_seconds": "ALTER TABLE mining_cycles ADD COLUMN missed_seconds INTEGER NOT NULL DEFAULT 0",
        "earning_ratio": "ALTER TABLE mining_cycles ADD COLUMN earning_ratio NUMERIC(12, 6) NOT NULL DEFAULT 1",
        "full_daily_income": "ALTER TABLE mining_cycles ADD COLUMN full_daily_income NUMERIC(12, 4) NOT NULL DEFAULT 0",
        "final_income_after_time_deduction": (
            "ALTER TABLE mining_cycles ADD COLUMN final_income_after_time_deduction NUMERIC(12, 4) NOT NULL DEFAULT 0"
        ),
    }

    with engine.begin() as connection:
        for column_name, ddl in column_sql.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))

        connection.execute(
            text(
                """
                UPDATE mining_cycles
                SET
                    status = CASE
                        WHEN completed_at IS NOT NULL AND status = 'active'
                        THEN 'completed'
                        ELSE status
                    END,
                    cycle_window_start = COALESCE(cycle_window_start, start_at),
                    cycle_window_end = COALESCE(cycle_window_end, end_at),
                    actual_start_time = COALESCE(actual_start_time, start_at),
                    active_seconds = COALESCE(active_seconds, 86400),
                    missed_seconds = COALESCE(missed_seconds, 0),
                    earning_ratio = COALESCE(earning_ratio, 1),
                    full_daily_income = CASE
                        WHEN COALESCE(full_daily_income, 0) = 0 AND COALESCE(final_income, 0) > 0
                        THEN final_income
                        ELSE COALESCE(full_daily_income, 0)
                    END,
                    final_income_after_time_deduction = CASE
                        WHEN COALESCE(final_income_after_time_deduction, 0) = 0 AND COALESCE(final_income, 0) > 0
                        THEN final_income
                        ELSE COALESCE(final_income_after_time_deduction, 0)
                    END
                """
            )
        )


def ensure_user_financial_defaults() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    updates = []
    if "capital" in existing_columns:
        updates.append("capital = COALESCE(capital, 0)")
    if "profits" in existing_columns:
        updates.append("profits = COALESCE(profits, 0)")
    if "daily_earnings" in existing_columns:
        updates.append("daily_earnings = COALESCE(daily_earnings, 0)")

    if not updates:
        return

    with engine.begin() as connection:
        connection.execute(text(f"UPDATE users SET {', '.join(updates)}"))


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_user_columns()
    ensure_user_financial_defaults()
    ensure_notification_columns()
    ensure_support_message_columns()
    ensure_pending_request_columns()
    ensure_mining_cycle_columns()
    ensure_record_amount_precision()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
