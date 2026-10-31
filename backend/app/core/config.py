import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Subscription Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-hackathon-odoo-flux-key-2026-xyz-987654321")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    RESET_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./subscription_system.db")

    class Config:
        case_sensitive = True

settings = Settings()
