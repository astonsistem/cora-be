import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")

        self.secret_key = os.getenv("SECRET_KEY")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "1"))

        self.asis_base_url = os.getenv("ASIS_BASE_URL")
        self.asis_username = os.getenv("ASIS_USERNAME")
        self.asis_password = os.getenv("ASIS_PASSWORD")
        self.asis_secret_key = os.getenv("ASIS_SECRET_KEY")

        self.customer_trash_retention_days = int(os.getenv("CUSTOMER_TRASH_RETENTION_DAYS", "90"))
        self.voucher_archive_after_days = int(os.getenv("VOUCHER_ARCHIVE_AFTER_DAYS", "90"))
        self.activity_log_archive_after_days = int(os.getenv("ACTIVITY_LOG_ARCHIVE_AFTER_DAYS", "90"))

        self.public_rate_limit_per_minute = int(os.getenv("PUBLIC_RATE_LIMIT_PER_MINUTE", "240"))
        self.public_submit_rate_limit_per_minute = int(os.getenv("PUBLIC_SUBMIT_RATE_LIMIT_PER_MINUTE", "60"))
        self.public_code_rate_limit_per_minute = int(os.getenv("PUBLIC_CODE_RATE_LIMIT_PER_MINUTE", "60"))
        self.trust_proxy_headers = os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("1", "true", "yes")

        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        self.public_api_keys = tuple(
            key.strip() for key in os.getenv("PUBLIC_API_KEY", "").split(",") if key.strip()
        )

settings = Settings()
