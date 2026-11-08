from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None

    encryption_key: str

    default_ttl_seconds: int = Field(default=3600, gt=0)
    max_ttl_seconds: int = Field(default=604_800, gt=0)
    max_file_size_mb: int = Field(default=20, gt=0)

    @model_validator(mode="after")
    def _check_ttl_bounds(self) -> "Settings":
        if self.default_ttl_seconds > self.max_ttl_seconds:
            raise ValueError("DEFAULT_TTL_SECONDS не может превышать MAX_TTL_SECONDS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
