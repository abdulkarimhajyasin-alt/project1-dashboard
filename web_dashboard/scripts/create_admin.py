import os
import sys

from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Admin  # noqa: E402
from app.security import hash_password  # noqa: E402


settings = get_settings()


def main() -> None:
    if not settings.admin_username or not settings.admin_password:
        raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD environment variables are required.")

    init_db()
    db = SessionLocal()
    try:
        if db.query(Admin).filter(Admin.username == settings.admin_username).first():
            print("Admin already exists.")
            return

        admin = Admin(username=settings.admin_username, password_hash=hash_password(settings.admin_password))
        db.add(admin)
        db.commit()
        print("Admin created.")
    except IntegrityError:
        db.rollback()
        print("Admin already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    main()