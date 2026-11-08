from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import Settings, get_settings


class CryptoService:
    """Единая схема шифрования для всех секретов — и текста, и файлов.

    Оба типа контента на уровне сервиса приводятся к bytes, поэтому
    один и тот же ключ Fernet шифрует/расшифровывает содержимое независимо
    от его исходного вида. Ключ берётся из переменных окружения (ENCRYPTION_KEY)
    и нигде не хранится в коде.
    """

    def __init__(self, settings: Settings) -> None:
        self._fernet = Fernet(settings.encryption_key.encode())

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        """Бросает cryptography.fernet.InvalidToken, если ключ не подходит или токен повреждён."""
        return self._fernet.decrypt(token)


@lru_cache
def get_crypto_service() -> CryptoService:
    return CryptoService(get_settings())
