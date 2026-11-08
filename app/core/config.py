from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_port: int = 8000
    log_level: str = "INFO"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None

    encryption_key: str

    default_ttl_seconds: int = 3600
    max_ttl_seconds: int = 604_800
    max_file_size_mb: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
