import logging
import uuid

from cryptography.fernet import InvalidToken

from app.core.config import Settings, get_settings
from app.core.crypto import CryptoService, get_crypto_service
from app.core.exceptions import InvalidTTLError, SecretCorruptedError, SecretNotFoundError
from app.repositories.secret_repository import SecretRepository, get_secret_repository

logger = logging.getLogger(__name__)


class SecretService:
    """Бизнес-логика: валидация TTL, шифрование при создании, расшифровка при одноразовом чтении."""

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

    async def create_text_secret(self, content: str, ttl_seconds: int | None) -> tuple[str, int]:
        ttl = self._resolve_ttl(ttl_seconds)
        secret_id = str(uuid.uuid4())
        encrypted = self._crypto.encrypt(content.encode("utf-8"))
        await self._repository.save(secret_id, encrypted, ttl)
        logger.info("Secret %s created (kind=text, ttl=%ss)", secret_id, ttl)
        return secret_id, ttl

    async def read_text_secret(self, secret_id: str) -> str:
        encrypted = await self._repository.get_and_delete(secret_id)
        if encrypted is None:
            logger.info("Secret %s not found or already consumed", secret_id)
            raise SecretNotFoundError()

        try:
            decrypted = self._crypto.decrypt(encrypted)
        except InvalidToken:
            logger.critical("Secret %s could not be decrypted: data corrupted", secret_id)
            raise SecretCorruptedError() from None

        logger.info("Secret %s read and destroyed", secret_id)
        return decrypted.decode("utf-8")


def get_secret_service() -> SecretService:
    return SecretService(
        repository=get_secret_repository(),
        crypto=get_crypto_service(),
        settings=get_settings(),
    )
