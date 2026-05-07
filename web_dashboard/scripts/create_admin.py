import os
import sys

from sqlalchemy.exc import IntegrityError

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Admin  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> None:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not password:
        raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD environment variables are required.")

    init_db()
    db = SessionLocal()
    try:
        if db.query(Admin).filter(Admin.username == username).first():
            print("Admin already exists.")
            return

        admin = Admin(username=username, password_hash=hash_password(password))
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
