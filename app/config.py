import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")

        self.secret_key = os.getenv("SECRET_KEY")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

        self.asis_base_url = os.getenv("ASIS_BASE_URL")
        self.asis_username = os.getenv("ASIS_USERNAME")
        self.asis_password = os.getenv("ASIS_PASSWORD")

        self.public_api_keys = tuple(
            key.strip() for key in os.getenv("PUBLIC_API_KEY", "").split(",") if key.strip()
        )

settings = Settings()
