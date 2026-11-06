"""AES-GCM BYO key round-trip."""

from __future__ import annotations

from app.config import settings
from app.services.openrouter_key import decrypt_api_key, encrypt_api_key


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "byo_encryption_key", "dev-local-byo-encryption-key-32b!!")
    blob = encrypt_api_key("sk-or-test-secret")
    assert isinstance(blob, (bytes, bytearray))
    assert decrypt_api_key(bytes(blob)) == "sk-or-test-secret"
