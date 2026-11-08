import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.core.crypto import CryptoService


def _make_service() -> CryptoService:
    settings = Settings(encryption_key=Fernet.generate_key().decode())
    return CryptoService(settings)


def test_encrypt_then_decrypt_roundtrip():
    service = _make_service()
    plaintext = b"super secret value"

    token = service.encrypt(plaintext)

    assert service.decrypt(token) == plaintext


def test_encrypt_output_differs_from_plaintext():
    service = _make_service()

    token = service.encrypt(b"hello")

    assert token != b"hello"


def test_encrypt_is_non_deterministic():
    service = _make_service()
    plaintext = b"same input"

    assert service.encrypt(plaintext) != service.encrypt(plaintext)


def test_decrypt_with_wrong_key_raises_invalid_token():
    service_a = _make_service()
    service_b = _make_service()
    token = service_a.encrypt(b"secret")

    with pytest.raises(InvalidToken):
        service_b.decrypt(token)


def test_decrypt_tampered_token_raises_invalid_token():
    service = _make_service()
    token = bytearray(service.encrypt(b"secret"))
    token[-1] ^= 0xFF

    with pytest.raises(InvalidToken):
        service.decrypt(bytes(token))
