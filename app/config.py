"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    REGISTRY_DB_URL: str
    TENANT_DB_HOST: str = "localhost"
    TENANT_DB_PORT: int = 5432
    TENANT_DB_USER: str = "arvi"
    TENANT_DB_PASSWORD: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 1

    # HealthLink
    HEALTHLINK_BASE_DIR: str = "/opt/healthlink"
    ARVI_CENTRAL_EDI: str = "ARVIHLT1"

    # Workers
    POLL_INTERVAL_SECONDS: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_TO_DATABASE: bool = True

    # Application
    APP_NAME: str = "ARVI HealthLink Integration"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
