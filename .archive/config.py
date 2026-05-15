"""Application configuration."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    APP_ENV: str = "development"
    DEBUG: bool = True

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/crew.db"

    # LLM Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Platform APIs
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/crew.log"

    # CrewAI
    CREW_MAX_ITER: int = 15
    CREW_VERBOSE: bool = True
    CREW_MEMORY_BACKEND: str = "local"

    # Scheduler
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    # Browser
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000

    # Security
    CORS_ORIGINS: str = "http://localhost:3000"
    INTERNAL_API_KEY: str = ""
    JWT_EXPIRES_IN: int = 86400
    ENCRYPTION_KEY: str = ""
    AUDIT_LOGGING_ENABLED: bool = True
    API_RATE_LIMIT: int = 60

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> str:
        """Parse CORS_ORIGINS from comma-separated string."""
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return ",".join(v)
        return str(v)

    def get_cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Content
    DEFAULT_LANGUAGE: str = "zh-CN"
    MAX_CONTENT_LENGTH_XHS: int = 1000
    MAX_CONTENT_LENGTH_WECHAT: int = 20000


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
