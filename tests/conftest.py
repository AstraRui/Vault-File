import os

from cryptography.fernet import Fernet

os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("MAX_FILE_SIZE_MB", "1")

import fakeredis
import httpx
import pytest

from app.core.config import get_settings
from app.core.crypto import CryptoService
from app.main import app
from app.repositories.secret_repository import SecretRepository
from app.services.secret_service import SecretService, get_secret_service


@pytest.fixture
async def client():
    """HTTP-клиент поверх ASGI-приложения с fakeredis вместо реального Redis.

    ASGITransport не запускает lifespan, поэтому настоящий Redis/логирование
    не требуются — сервис подменяется через dependency_overrides.
    """
    settings = get_settings()
    repository = SecretRepository(fakeredis.FakeAsyncRedis(decode_responses=False))
    crypto = CryptoService(settings)

    def override_get_secret_service() -> SecretService:
        return SecretService(repository=repository, crypto=crypto, settings=settings)

    app.dependency_overrides[get_secret_service] = override_get_secret_service

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()
