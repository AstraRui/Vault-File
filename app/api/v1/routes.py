import base64
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.core.config import Settings, get_settings
from app.core.exceptions import PayloadTooLargeError
from app.schemas.secret import (
    CreateSecretRequest,
    SecretContentResponse,
    SecretCreatedResponse,
    SecretKind,
)
from app.services.secret_service import SecretService, get_secret_service

_UPLOAD_CHUNK_SIZE = 1024 * 1024

router = APIRouter(prefix="/secrets", tags=["secrets"])


@router.post("", response_model=SecretCreatedResponse, status_code=201)
async def create_text_secret(
    payload: CreateSecretRequest,
    service: SecretService = Depends(get_secret_service),
) -> SecretCreatedResponse:
    secret_id, ttl = await service.create_text_secret(payload.content, payload.ttl_seconds)
    return SecretCreatedResponse(id=secret_id, ttl_seconds=ttl)


@router.post("/file", response_model=SecretCreatedResponse, status_code=201)
async def create_file_secret(
    file: UploadFile = File(...),
    ttl_seconds: int | None = Form(None),
    service: SecretService = Depends(get_secret_service),
    settings: Settings = Depends(get_settings),
) -> SecretCreatedResponse:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    chunks = bytearray()
    while chunk := await file.read(_UPLOAD_CHUNK_SIZE):
        chunks.extend(chunk)
        if len(chunks) > max_bytes:
            raise PayloadTooLargeError(settings.max_file_size_mb)

    filename = file.filename or "secret"
    secret_id, ttl = await service.create_file_secret(filename, bytes(chunks), ttl_seconds)
    return SecretCreatedResponse(id=secret_id, ttl_seconds=ttl)


@router.get(
    "/{secret_id}",
    response_model=None,
    responses={
        200: {
            "description": (
                "Текстовый секрет возвращается как JSON (SecretContentResponse); "
                "файл — как бинарное содержимое с заголовком Content-Disposition."
            ),
            "content": {
                "application/json": {"schema": SecretContentResponse.model_json_schema()},
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}},
            },
        },
    },
)
async def read_secret(
    secret_id: str,
    service: SecretService = Depends(get_secret_service),
) -> SecretContentResponse | Response:
    envelope = await service.read_secret(secret_id)

    if envelope["kind"] == SecretKind.FILE.value:
        raw_content = base64.b64decode(envelope["content_b64"])
        encoded_filename = quote(envelope["filename"])
        return Response(
            content=raw_content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
        )

    return SecretContentResponse(kind=SecretKind.TEXT, content=envelope["content"])
