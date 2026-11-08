from fastapi import APIRouter, Depends

from app.schemas.secret import (
    CreateSecretRequest,
    SecretContentResponse,
    SecretCreatedResponse,
    SecretKind,
)
from app.services.secret_service import SecretService, get_secret_service

router = APIRouter(prefix="/secrets", tags=["secrets"])


@router.post("", response_model=SecretCreatedResponse, status_code=201)
async def create_secret(
    payload: CreateSecretRequest,
    service: SecretService = Depends(get_secret_service),
) -> SecretCreatedResponse:
    secret_id, ttl = await service.create_text_secret(payload.content, payload.ttl_seconds)
    return SecretCreatedResponse(id=secret_id, ttl_seconds=ttl)


@router.get("/{secret_id}", response_model=SecretContentResponse)
async def read_secret(
    secret_id: str,
    service: SecretService = Depends(get_secret_service),
) -> SecretContentResponse:
    content = await service.read_text_secret(secret_id)
    return SecretContentResponse(kind=SecretKind.TEXT, content=content)
