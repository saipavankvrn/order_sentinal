import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "OrderFlow Sentinel"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database Configuration (SQLite default with SQLAlchemy portability)
    DATABASE_URL: str = "sqlite:///./orderflow_sentinel.db"

    # AI Engine Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_ID: str = "gemini-flash-latest"

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

