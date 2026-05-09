import os
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


class Settings:
    app_name: str = os.getenv("APP_NAME", "NovaHash")
    database_url: str = os.getenv("DATABASE_URL", "")
    secret_key: str = os.getenv("SECRET_KEY", "")
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "dashboard_session")
    admin_username: str = os.getenv("ADMIN_USERNAME", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    usdt_wallet_address: str = os.getenv("USDT_WALLET_ADDRESS", "ضع_عنوان_محفظة_USDT_هنا")

    @property
    def is_configured(self) -> bool:
        return bool(self.database_url and self.secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
