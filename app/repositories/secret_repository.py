from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings


class SecretRepository:
    """Redis — единственное хранилище секретов: TTL и одноразовость обеспечивает сам Redis.

    TTL задаётся через SET ... EX при записи, а чтение выполняется через GETDEL —
    атомарную команду Redis, которая возвращает значение и сразу удаляет ключ.
    Поэтому повторное чтение той же ссылки физически невозможно, дополнительная блокировка не нужна.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def save(self, secret_id: str, encrypted_data: bytes, ttl_seconds: int) -> None:
        await self._client.set(secret_id, encrypted_data, ex=ttl_seconds)

    async def get_and_delete(self, secret_id: str) -> bytes | None:
        return await self._client.getdel(secret_id)

    async def close(self) -> None:
        await self._client.aclose()


@lru_cache
def get_secret_repository() -> SecretRepository:
    settings = get_settings()
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        decode_responses=False,
    )
    return SecretRepository(client)
