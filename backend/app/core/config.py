from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    debug: bool = True

    database_url: str = "sqlite+aiosqlite:///./data/tastecraft_dev.db"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    tikhub_api_key: str = ""

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    cors_origins: list[str] = ["*"]

    wechat_app_id: str = ""
    wechat_app_secret: str = ""

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
