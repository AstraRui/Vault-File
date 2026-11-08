from enum import Enum

from pydantic import BaseModel, Field


class SecretKind(str, Enum):
    TEXT = "text"
    FILE = "file"


class CreateSecretRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Текст секрета")
    ttl_seconds: int | None = Field(
        default=None, gt=0, description="Время жизни секрета в секундах"
    )


class SecretCreatedResponse(BaseModel):
    id: str = Field(..., description="UUID созданного секрета — используется в ссылке")
    ttl_seconds: int = Field(..., description="Фактическое время жизни в секундах")


class SecretContentResponse(BaseModel):
    kind: SecretKind
    content: str = Field(..., description="Расшифрованное содержимое секрета")


class ErrorResponse(BaseModel):
    detail: str
