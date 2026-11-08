import base64
import json
import logging
import uuid

from cryptography.fernet import InvalidToken

from app.core.config import Settings, get_settings
from app.core.crypto import CryptoService, get_crypto_service
from app.core.exceptions import (
    InvalidTTLError,
    PayloadTooLargeError,
    SecretCorruptedError,
    SecretNotFoundError,
)
from app.repositories.secret_repository import SecretRepository, get_secret_repository
from app.schemas.secret import SecretKind

logger = logging.getLogger(__name__)


class SecretService:
    """Бизнес-логика: валидация, шифрование при создании, расшифровка при одноразовом чтении.

    Текст и файл хранятся одинаково — как JSON-конверт с полем kind, зашифрованный
    целиком одним и тем же Fernet-ключом. CryptoService и SecretRepository не знают
    о разнице между типами секретов, вся разница — на уровне этого сервиса.
    """

    def __init__(
        self,
        repository: SecretRepository,
        crypto: CryptoService,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._crypto = crypto
        self._settings = settings

    def _resolve_ttl(self, ttl_seconds: int | None) -> int:
        ttl = ttl_seconds if ttl_seconds is not None else self._settings.default_ttl_seconds
        if ttl <= 0 or ttl > self._settings.max_ttl_seconds:
            raise InvalidTTLError(self._settings.max_ttl_seconds)
        return ttl

    async def _store(self, envelope: dict, ttl_seconds: int) -> str:
        secret_id = str(uuid.uuid4())
        encrypted = self._crypto.encrypt(json.dumps(envelope).encode("utf-8"))
        await self._repository.save(secret_id, encrypted, ttl_seconds)
        return secret_id

    async def create_text_secret(self, content: str, ttl_seconds: int | None) -> tuple[str, int]:
        ttl = self._resolve_ttl(ttl_seconds)
        secret_id = await self._store({"kind": SecretKind.TEXT.value, "content": content}, ttl)
        logger.info("Secret %s created (kind=text, ttl=%ss)", secret_id, ttl)
        return secret_id, ttl

    async def create_file_secret(
        self, filename: str, content: bytes, ttl_seconds: int | None
    ) -> tuple[str, int]:
        ttl = self._resolve_ttl(ttl_seconds)
        max_bytes = self._settings.max_file_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise PayloadTooLargeError(self._settings.max_file_size_mb)

        envelope = {
            "kind": SecretKind.FILE.value,
            "filename": filename,
            "content_b64": base64.b64encode(content).decode("ascii"),
        }
        secret_id = await self._store(envelope, ttl)
        logger.info("Secret %s created (kind=file, filename=%s, ttl=%ss)", secret_id, filename, ttl)
        return secret_id, ttl

    async def read_secret(self, secret_id: str) -> dict:
        encrypted = await self._repository.get_and_delete(secret_id)
        if encrypted is None:
            logger.info("Secret %s not found or already consumed", secret_id)
            raise SecretNotFoundError()

        try:
            decrypted = self._crypto.decrypt(encrypted)
        except InvalidToken:
            logger.critical("Secret %s could not be decrypted: data corrupted", secret_id)
            raise SecretCorruptedError() from None

        envelope = json.loads(decrypted.decode("utf-8"))
        logger.info("Secret %s read and destroyed (kind=%s)", secret_id, envelope["kind"])
        return envelope


def get_secret_service() -> SecretService:
    return SecretService(
        repository=get_secret_repository(),
        crypto=get_crypto_service(),
        settings=get_settings(),
    )
