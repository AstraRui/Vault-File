import fakeredis

from app.repositories.secret_repository import SecretRepository


def _make_repository() -> SecretRepository:
    client = fakeredis.FakeAsyncRedis(decode_responses=False)
    return SecretRepository(client)


async def test_save_then_get_and_delete_returns_value():
    repository = _make_repository()
    await repository.save("secret-id", b"encrypted-payload", ttl_seconds=60)

    assert await repository.get_and_delete("secret-id") == b"encrypted-payload"


async def test_get_and_delete_is_one_time():
    repository = _make_repository()
    await repository.save("secret-id", b"encrypted-payload", ttl_seconds=60)

    first = await repository.get_and_delete("secret-id")
    second = await repository.get_and_delete("secret-id")

    assert first == b"encrypted-payload"
    assert second is None


async def test_get_and_delete_missing_key_returns_none():
    repository = _make_repository()

    assert await repository.get_and_delete("does-not-exist") is None


async def test_save_sets_ttl():
    client = fakeredis.FakeAsyncRedis(decode_responses=False)
    repository = SecretRepository(client)
    await repository.save("secret-id", b"data", ttl_seconds=60)

    ttl = await client.ttl("secret-id")

    assert 0 < ttl <= 60


async def test_close_does_not_raise():
    repository = _make_repository()

    await repository.close()
