async def test_create_and_read_text_secret(client):
    create_response = await client.post("/api/v1/secrets", json={"content": "top secret"})
    assert create_response.status_code == 201
    secret_id = create_response.json()["id"]

    read_response = await client.get(f"/api/v1/secrets/{secret_id}")
    assert read_response.status_code == 200
    assert read_response.json() == {"kind": "text", "content": "top secret"}


async def test_text_secret_is_one_time(client):
    create_response = await client.post("/api/v1/secrets", json={"content": "burn after reading"})
    secret_id = create_response.json()["id"]

    first_read = await client.get(f"/api/v1/secrets/{secret_id}")
    second_read = await client.get(f"/api/v1/secrets/{secret_id}")

    assert first_read.status_code == 200
    assert second_read.status_code == 404
    assert "не найден" in second_read.json()["detail"]


async def test_read_nonexistent_secret_returns_404(client):
    response = await client.get("/api/v1/secrets/does-not-exist")

    assert response.status_code == 404


async def test_create_with_ttl_above_max_returns_400(client):
    response = await client.post(
        "/api/v1/secrets", json={"content": "x", "ttl_seconds": 99_999_999}
    )

    assert response.status_code == 400


async def test_create_with_empty_content_returns_422(client):
    response = await client.post("/api/v1/secrets", json={"content": ""})

    assert response.status_code == 422


async def test_create_and_download_file_secret(client):
    files = {"file": ("report.txt", b"file secret content", "text/plain")}

    create_response = await client.post("/api/v1/secrets/file", files=files)
    assert create_response.status_code == 201
    secret_id = create_response.json()["id"]

    download_response = await client.get(f"/api/v1/secrets/{secret_id}")
    assert download_response.status_code == 200
    assert download_response.content == b"file secret content"
    assert "report.txt" in download_response.headers["content-disposition"]


async def test_file_above_size_limit_returns_413(client):
    oversized_content = b"x" * (2 * 1024 * 1024)  # лимит в тестовом окружении — 1 МБ
    files = {"file": ("big.bin", oversized_content, "application/octet-stream")}

    response = await client.post("/api/v1/secrets/file", files=files)

    assert response.status_code == 413
