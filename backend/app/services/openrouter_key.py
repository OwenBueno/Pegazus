"""Resolve OpenRouter API key: BYO encrypted user key, else server settings."""

from __future__ import annotations

import base64
import os
from uuid import UUID

import httpx
import psycopg
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _aes_key() -> bytes | None:
    raw = settings.byo_encryption_key.strip()
    if not raw:
        return None
    # Accept urlsafe base64 or raw 32-byte latin1
    try:
        key = base64.urlsafe_b64decode(raw + "==")
        if len(key) >= 32:
            return key[:32]
    except Exception:
        pass
    b = raw.encode("utf-8")
    if len(b) >= 32:
        return b[:32]
    # Derive padded key for local/dev (ponytail: not KMS)
    return (b + b"0" * 32)[:32]


def encrypt_api_key(plaintext: str) -> bytes:
    key = _aes_key()
    if key is None:
        raise ValueError("BYO_ENCRYPTION_KEY not configured")
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ct


def decrypt_api_key(blob: bytes) -> str:
    key = _aes_key()
    if key is None:
        raise ValueError("BYO_ENCRYPTION_KEY not configured")
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")


def resolve_openrouter_key(conn: psycopg.Connection, user_id: UUID) -> str:
    row = conn.execute(
        "SELECT custom_openrouter_api_key_encrypted FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()
    if row and row.get("custom_openrouter_api_key_encrypted"):
        try:
            return decrypt_api_key(bytes(row["custom_openrouter_api_key_encrypted"]))
        except Exception:
            pass
    return settings.openrouter_api_key


def validate_openrouter_key(api_key: str) -> bool:
    try:
        r = httpx.get(
            OPENROUTER_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=8.0,
        )
        return r.status_code < 500
    except httpx.HTTPError:
        return False


def user_has_byo_key(conn: psycopg.Connection, user_id: UUID) -> bool:
    row = conn.execute(
        "SELECT custom_openrouter_api_key_encrypted IS NOT NULL AS has_key FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()
    return bool(row and row["has_key"])
